"""Typed parser for X12 270 005010X279A1 eligibility inquiries."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from ...model import Diagnostic, RawSegment, RawTransaction, X12Delimiters

_IMPLEMENTATION_VERSION = "005010X279A1"
_EXPECTED_PARENT_LEVEL = {"20": None, "21": "20", "22": "21", "23": "22"}
_TRANSACTION_BOUNDARY_SEGMENTS = {"ST", "BHT", "SE"}


class _Typed270Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)


class BeginningOfHierarchicalTransaction(_Typed270Model):
    hierarchical_structure_code: str
    transaction_set_purpose_code: str
    submitter_transaction_identifier: str
    creation_date: str | None = None
    creation_time: str | None = None
    raw_segment: RawSegment


class Nm1Party(_Typed270Model):
    entity_identifier_code: str
    entity_type_qualifier: str
    name: str
    first_name: str | None = None
    identification_code_qualifier: str | None = None
    identification_code: str | None = None
    raw_segment: RawSegment


class EligibilityInquiry(_Typed270Model):
    service_type_codes: tuple[str, ...]
    raw_segment: RawSegment


class DependentLevel(_Typed270Model):
    hierarchical_id: str
    name: Nm1Party
    inquiries: tuple[EligibilityInquiry, ...]
    raw_segments: tuple[RawSegment, ...]


class SubscriberLevel(_Typed270Model):
    hierarchical_id: str
    name: Nm1Party
    inquiries: tuple[EligibilityInquiry, ...]
    dependents: tuple[DependentLevel, ...]
    raw_segments: tuple[RawSegment, ...]


class InformationReceiverLevel(_Typed270Model):
    hierarchical_id: str
    name: Nm1Party
    subscribers: tuple[SubscriberLevel, ...]
    raw_segments: tuple[RawSegment, ...]


class InformationSourceLevel(_Typed270Model):
    hierarchical_id: str
    name: Nm1Party
    receivers: tuple[InformationReceiverLevel, ...]
    raw_segments: tuple[RawSegment, ...]


class Transaction270(_Typed270Model):
    control_number: str
    implementation_version: str
    beginning: BeginningOfHierarchicalTransaction
    information_sources: tuple[InformationSourceLevel, ...]
    raw_transaction: RawTransaction


@dataclass(frozen=True, slots=True)
class Parse270Result:
    transaction: Transaction270 | None
    diagnostics: tuple[Diagnostic, ...]

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "error")


def _empty_loop_segments() -> list[tuple[int, RawSegment]]:
    return []


def _empty_loop_children() -> list[_HlLoop]:
    return []


@dataclass(slots=True)
class _HlLoop:
    identifier: str
    parent_identifier: str | None
    level_code: str
    segment: RawSegment
    segment_index: int
    segments: list[tuple[int, RawSegment]] = field(default_factory=_empty_loop_segments)
    children: list[_HlLoop] = field(default_factory=_empty_loop_children)


def parse_270(transaction: RawTransaction, delimiters: X12Delimiters) -> Parse270Result:
    """Parse a lossless transaction slice into the supported 270 hierarchy."""

    diagnostics: list[Diagnostic] = []
    if not transaction.complete:
        diagnostics.append(_transaction_diagnostic("x12.270.transaction.incomplete", transaction))
    if transaction.identifier != "270":
        diagnostics.append(_transaction_diagnostic("x12.270.transaction_id_invalid", transaction))
    if transaction.implementation_version != _IMPLEMENTATION_VERSION:
        diagnostics.append(_transaction_diagnostic("x12.270.implementation_version_invalid", transaction))

    beginning = _read_bht(transaction, diagnostics)
    loops = _read_hl_loops(transaction, diagnostics)
    _link_hl_loops(loops, diagnostics)
    if diagnostics:
        return Parse270Result(transaction=None, diagnostics=tuple(diagnostics))
    information_sources = _build_sources(loops, delimiters, diagnostics)

    if diagnostics:
        return Parse270Result(transaction=None, diagnostics=tuple(diagnostics))
    if beginning is None:
        return Parse270Result(transaction=None, diagnostics=tuple(diagnostics))

    return Parse270Result(
        transaction=Transaction270(
            control_number=transaction.control_number or "",
            implementation_version=transaction.implementation_version or "",
            beginning=beginning,
            information_sources=information_sources,
            raw_transaction=transaction,
        ),
        diagnostics=(),
    )


def _read_bht(
    transaction: RawTransaction, diagnostics: list[Diagnostic]
) -> BeginningOfHierarchicalTransaction | None:
    bhts = [
        (transaction.start_index + index, segment)
        for index, segment in enumerate(transaction.segments)
        if segment.identifier == "BHT"
    ]
    if len(bhts) != 1:
        diagnostics.append(_transaction_diagnostic("x12.270.bht.missing_or_repeated", transaction))
        return None

    segment_index, segment = bhts[0]
    required = _required_elements(segment, segment_index, (1, 2, 3), "x12.270.bht.invalid", diagnostics)
    if required is None:
        return None
    return BeginningOfHierarchicalTransaction(
        hierarchical_structure_code=required[0],
        transaction_set_purpose_code=required[1],
        submitter_transaction_identifier=required[2],
        creation_date=_element(segment, 4),
        creation_time=_element(segment, 5),
        raw_segment=segment,
    )


def _read_hl_loops(transaction: RawTransaction, diagnostics: list[Diagnostic]) -> tuple[_HlLoop, ...]:
    by_identifier: dict[str, _HlLoop] = {}
    ordered: list[_HlLoop] = []
    current: _HlLoop | None = None

    for relative_index, segment in enumerate(transaction.segments):
        segment_index = transaction.start_index + relative_index
        if segment.identifier == "HL":
            current = _make_hl_loop(segment, segment_index, diagnostics)
            if current is None:
                continue
            if current.identifier in by_identifier:
                diagnostics.append(_diagnostic("x12.270.hl.duplicate_id", segment, segment_index, 1))
                current = None
                continue
            by_identifier[current.identifier] = current
            ordered.append(current)
        elif current is not None and segment.identifier not in _TRANSACTION_BOUNDARY_SEGMENTS:
            current.segments.append((segment_index, segment))

    if not ordered:
        diagnostics.append(_transaction_diagnostic("x12.270.hl.missing", transaction))
    return tuple(ordered)


def _make_hl_loop(
    segment: RawSegment, segment_index: int, diagnostics: list[Diagnostic]
) -> _HlLoop | None:
    identifier = _element(segment, 1)
    level_code = _element(segment, 3)
    if not identifier or not level_code:
        diagnostics.append(_diagnostic("x12.270.hl.invalid", segment, segment_index))
        return None
    parent_identifier = _element(segment, 2) or None
    return _HlLoop(
        identifier=identifier,
        parent_identifier=parent_identifier,
        level_code=level_code,
        segment=segment,
        segment_index=segment_index,
    )


def _link_hl_loops(loops: tuple[_HlLoop, ...], diagnostics: list[Diagnostic]) -> None:
    by_identifier = {loop.identifier: loop for loop in loops}
    for loop in loops:
        expected_parent_level = _EXPECTED_PARENT_LEVEL.get(loop.level_code)
        if loop.level_code not in _EXPECTED_PARENT_LEVEL:
            diagnostics.append(_diagnostic("x12.270.hl.level_invalid", loop.segment, loop.segment_index, 3))
            continue
        if expected_parent_level is None:
            if loop.parent_identifier is not None:
                diagnostics.append(_diagnostic("x12.270.hl.parent_invalid", loop.segment, loop.segment_index, 2))
            continue
        parent = by_identifier.get(loop.parent_identifier or "")
        if parent is None:
            diagnostics.append(_diagnostic("x12.270.hl.parent_missing", loop.segment, loop.segment_index, 2))
        elif parent.level_code != expected_parent_level:
            diagnostics.append(
                _diagnostic("x12.270.hl.parent_level_invalid", loop.segment, loop.segment_index, 2)
            )
        else:
            parent.children.append(loop)


def _build_sources(
    loops: tuple[_HlLoop, ...], delimiters: X12Delimiters, diagnostics: list[Diagnostic]
) -> tuple[InformationSourceLevel, ...]:
    source_loops = tuple(loop for loop in loops if loop.level_code == "20")
    if not source_loops:
        diagnostics.append(_loop_diagnostic("x12.270.source.missing", loops))
        return ()
    sources: list[InformationSourceLevel] = []
    for loop in source_loops:
        source = _build_source(loop, delimiters, diagnostics)
        if source is not None:
            sources.append(source)
    return tuple(sources)


def _build_source(
    loop: _HlLoop, delimiters: X12Delimiters, diagnostics: list[Diagnostic]
) -> InformationSourceLevel | None:
    name = _read_nm1(loop, diagnostics)
    receivers = tuple(
        receiver
        for child in loop.children
        if child.level_code == "21"
        for receiver in (_build_receiver(child, delimiters, diagnostics),)
        if receiver is not None
    )
    if not receivers:
        diagnostics.append(_diagnostic("x12.270.receiver.missing", loop.segment, loop.segment_index))
    if name is None or not receivers:
        return None
    return InformationSourceLevel(
        hierarchical_id=loop.identifier,
        name=name,
        receivers=receivers,
        raw_segments=_raw_segments(loop),
    )


def _build_receiver(
    loop: _HlLoop, delimiters: X12Delimiters, diagnostics: list[Diagnostic]
) -> InformationReceiverLevel | None:
    name = _read_nm1(loop, diagnostics)
    subscribers = tuple(
        subscriber
        for child in loop.children
        if child.level_code == "22"
        for subscriber in (_build_subscriber(child, delimiters, diagnostics),)
        if subscriber is not None
    )
    if not subscribers:
        diagnostics.append(_diagnostic("x12.270.subscriber.missing", loop.segment, loop.segment_index))
    if name is None or not subscribers:
        return None
    return InformationReceiverLevel(
        hierarchical_id=loop.identifier,
        name=name,
        subscribers=subscribers,
        raw_segments=_raw_segments(loop),
    )


def _build_subscriber(
    loop: _HlLoop, delimiters: X12Delimiters, diagnostics: list[Diagnostic]
) -> SubscriberLevel | None:
    name = _read_nm1(loop, diagnostics)
    dependents = tuple(
        dependent
        for child in loop.children
        if child.level_code == "23"
        for dependent in (_build_dependent(child, delimiters, diagnostics),)
        if dependent is not None
    )
    if name is None:
        return None
    return SubscriberLevel(
        hierarchical_id=loop.identifier,
        name=name,
        inquiries=_read_inquiries(loop, delimiters, diagnostics),
        dependents=dependents,
        raw_segments=_raw_segments(loop),
    )


def _build_dependent(
    loop: _HlLoop, delimiters: X12Delimiters, diagnostics: list[Diagnostic]
) -> DependentLevel | None:
    name = _read_nm1(loop, diagnostics)
    if name is None:
        return None
    return DependentLevel(
        hierarchical_id=loop.identifier,
        name=name,
        inquiries=_read_inquiries(loop, delimiters, diagnostics),
        raw_segments=_raw_segments(loop),
    )


def _read_nm1(loop: _HlLoop, diagnostics: list[Diagnostic]) -> Nm1Party | None:
    for segment_index, segment in loop.segments:
        if segment.identifier != "NM1":
            continue
        required = _required_elements(segment, segment_index, (1, 2, 3), "x12.270.nm1.invalid", diagnostics)
        if required is None:
            return None
        return Nm1Party(
            entity_identifier_code=required[0],
            entity_type_qualifier=required[1],
            name=required[2],
            first_name=_element(segment, 4),
            identification_code_qualifier=_element(segment, 8),
            identification_code=_element(segment, 9),
            raw_segment=segment,
        )
    diagnostics.append(_diagnostic("x12.270.nm1.missing", loop.segment, loop.segment_index))
    return None


def _read_inquiries(
    loop: _HlLoop, delimiters: X12Delimiters, diagnostics: list[Diagnostic]
) -> tuple[EligibilityInquiry, ...]:
    inquiries: list[EligibilityInquiry] = []
    for segment_index, segment in loop.segments:
        if segment.identifier != "EQ":
            continue
        service_type_codes = tuple(
            code for code in (_element(segment, 1) or "").split(delimiters.repetition) if code
        )
        if not service_type_codes:
            diagnostics.append(_diagnostic("x12.270.eq.service_type_missing", segment, segment_index, 1))
            continue
        inquiries.append(EligibilityInquiry(service_type_codes=service_type_codes, raw_segment=segment))
    return tuple(inquiries)


def _required_elements(
    segment: RawSegment,
    segment_index: int,
    positions: tuple[int, ...],
    code: str,
    diagnostics: list[Diagnostic],
) -> tuple[str, ...] | None:
    values = tuple(_element(segment, position) for position in positions)
    if any(not value for value in values):
        diagnostics.append(_diagnostic(code, segment, segment_index))
        return None
    return tuple(value for value in values if value is not None)


def _element(segment: RawSegment, position: int) -> str | None:
    if position <= len(segment.elements):
        return segment.elements[position - 1].value
    return None


def _raw_segments(loop: _HlLoop) -> tuple[RawSegment, ...]:
    return (loop.segment,) + tuple(segment for _, segment in loop.segments)


def _transaction_diagnostic(code: str, transaction: RawTransaction) -> Diagnostic:
    if transaction.segments:
        segment = transaction.segments[0]
        return _diagnostic(code, segment, transaction.start_index)
    return Diagnostic(code=code, message=_message(code), offset=0)


def _loop_diagnostic(code: str, loops: tuple[_HlLoop, ...]) -> Diagnostic:
    if loops:
        first = loops[0]
        return _diagnostic(code, first.segment, first.segment_index)
    return Diagnostic(code=code, message=_message(code), offset=0)


def _diagnostic(
    code: str,
    segment: RawSegment,
    segment_index: int,
    element_index: int | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=_message(code),
        offset=segment.start,
        segment_id=segment.identifier,
        segment_index=segment_index,
        element_index=element_index,
    )


def _message(code: str) -> str:
    return code.replace(".", " ").replace("_", " ")