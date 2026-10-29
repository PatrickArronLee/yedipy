"""Structural validation for X12 envelopes."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Diagnostic, RawSegment


@dataclass(slots=True)
class _InterchangeContext:
    segment: RawSegment
    segment_index: int
    group_count: int = 0


@dataclass(slots=True)
class _GroupContext:
    segment: RawSegment
    segment_index: int
    transaction_count: int = 0


@dataclass(slots=True)
class _TransactionContext:
    segment: RawSegment
    segment_index: int


def validate_envelopes(segments: tuple[RawSegment, ...]) -> tuple[Diagnostic, ...]:
    """Validate X12 envelope nesting, control numbers, and declared counts."""

    diagnostics: list[Diagnostic] = []
    interchange: _InterchangeContext | None = None
    group: _GroupContext | None = None
    transaction: _TransactionContext | None = None

    for segment_index, segment in enumerate(segments):
        if segment.identifier == "ISA":
            if interchange is not None:
                diagnostics.append(_diagnostic("x12.isa.unclosed", segment, segment_index))
            interchange = _InterchangeContext(segment, segment_index)
            group = None
            transaction = None
        elif segment.identifier == "GS":
            if interchange is None:
                diagnostics.append(_diagnostic("x12.gs.outside_interchange", segment, segment_index))
            if group is not None:
                diagnostics.append(_diagnostic("x12.gs.unclosed", segment, segment_index))
            group = _GroupContext(segment, segment_index)
            transaction = None
        elif segment.identifier == "ST":
            if group is None:
                diagnostics.append(_diagnostic("x12.st.outside_group", segment, segment_index))
            if transaction is not None:
                diagnostics.append(_diagnostic("x12.st.unclosed", segment, segment_index))
            transaction = _TransactionContext(segment, segment_index)
        elif segment.identifier == "SE":
            if transaction is None:
                diagnostics.append(_diagnostic("x12.se.unmatched", segment, segment_index))
                continue
            _validate_transaction_close(diagnostics, transaction, segment, segment_index)
            if group is not None:
                group.transaction_count += 1
            transaction = None
        elif segment.identifier == "GE":
            if group is None:
                diagnostics.append(_diagnostic("x12.ge.unmatched", segment, segment_index))
                continue
            if transaction is not None:
                diagnostics.append(_diagnostic("x12.se.missing", transaction.segment, transaction.segment_index))
                transaction = None
            _validate_group_close(diagnostics, group, segment, segment_index)
            if interchange is not None:
                interchange.group_count += 1
            group = None
        elif segment.identifier == "IEA":
            if interchange is None:
                diagnostics.append(_diagnostic("x12.iea.unmatched", segment, segment_index))
                continue
            if group is not None:
                diagnostics.append(_diagnostic("x12.ge.missing", group.segment, group.segment_index))
                group = None
            _validate_interchange_close(diagnostics, interchange, segment, segment_index)
            interchange = None

    if transaction is not None:
        diagnostics.append(_diagnostic("x12.se.missing", transaction.segment, transaction.segment_index))
    if group is not None:
        diagnostics.append(_diagnostic("x12.ge.missing", group.segment, group.segment_index))
    if interchange is not None:
        diagnostics.append(_diagnostic("x12.iea.missing", interchange.segment, interchange.segment_index))
    return tuple(diagnostics)


def _validate_transaction_close(
    diagnostics: list[Diagnostic],
    opening: _TransactionContext,
    closing: RawSegment,
    closing_index: int,
) -> None:
    _validate_count(
        diagnostics,
        code_prefix="x12.se",
        closing=closing,
        closing_index=closing_index,
        element_index=1,
        actual=closing_index - opening.segment_index + 1,
    )
    _validate_control_number(
        diagnostics,
        code_prefix="x12.se",
        opening=opening.segment,
        closing=closing,
        closing_index=closing_index,
        opening_element=2,
        closing_element=2,
    )


def _validate_group_close(
    diagnostics: list[Diagnostic],
    opening: _GroupContext,
    closing: RawSegment,
    closing_index: int,
) -> None:
    _validate_count(
        diagnostics,
        code_prefix="x12.ge",
        closing=closing,
        closing_index=closing_index,
        element_index=1,
        actual=opening.transaction_count,
    )
    _validate_control_number(
        diagnostics,
        code_prefix="x12.ge",
        opening=opening.segment,
        closing=closing,
        closing_index=closing_index,
        opening_element=6,
        closing_element=2,
    )


def _validate_interchange_close(
    diagnostics: list[Diagnostic],
    opening: _InterchangeContext,
    closing: RawSegment,
    closing_index: int,
) -> None:
    _validate_count(
        diagnostics,
        code_prefix="x12.iea",
        closing=closing,
        closing_index=closing_index,
        element_index=1,
        actual=opening.group_count,
    )
    _validate_control_number(
        diagnostics,
        code_prefix="x12.iea",
        opening=opening.segment,
        closing=closing,
        closing_index=closing_index,
        opening_element=13,
        closing_element=2,
    )


def _validate_count(
    diagnostics: list[Diagnostic],
    *,
    code_prefix: str,
    closing: RawSegment,
    closing_index: int,
    element_index: int,
    actual: int,
) -> None:
    declared = _element(closing, element_index)
    if declared is None or not declared.isdecimal():
        diagnostics.append(
            _diagnostic(f"{code_prefix}.count_invalid", closing, closing_index, element_index)
        )
    elif int(declared) != actual:
        diagnostics.append(
            _diagnostic(f"{code_prefix}.count_mismatch", closing, closing_index, element_index)
        )


def _validate_control_number(
    diagnostics: list[Diagnostic],
    *,
    code_prefix: str,
    opening: RawSegment,
    closing: RawSegment,
    closing_index: int,
    opening_element: int,
    closing_element: int,
) -> None:
    opening_value = _element(opening, opening_element)
    closing_value = _element(closing, closing_element)
    if opening_value is None or closing_value is None:
        diagnostics.append(
            _diagnostic(f"{code_prefix}.control_number_missing", closing, closing_index, closing_element)
        )
    elif opening_value != closing_value:
        diagnostics.append(
            _diagnostic(f"{code_prefix}.control_number_mismatch", closing, closing_index, closing_element)
        )


def _element(segment: RawSegment, position: int) -> str | None:
    if position <= len(segment.elements):
        return segment.elements[position - 1].value
    return None


def _diagnostic(
    code: str,
    segment: RawSegment,
    segment_index: int,
    element_index: int | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=code.replace(".", " ").replace("_", " "),
        offset=segment.start,
        segment_id=segment.identifier,
        segment_index=segment_index,
        element_index=element_index,
    )