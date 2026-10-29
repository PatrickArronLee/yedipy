"""Runtime support shared by generated X12 transaction-set models.

Generated models describe their X12 layout through class-level metadata. The parser in this
module walks a lossless ``RawTransaction`` and assigns each segment to the loop, group, or
segment slot that the metadata describes, then validates the result with Pydantic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar, Generic, Literal, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..model import Diagnostic, RawSegment, RawTransaction, X12Delimiters

DataType = Literal["AN", "ID", "R", "N", "DT", "TM"]


@dataclass(frozen=True, slots=True)
class ElementSpec:
    """Positional layout for one simple or composite element."""

    name: str
    position: int
    data_type: DataType = "AN"
    codes: tuple[str, ...] = ()
    composite: type[X12Composite] | None = None
    repeat: bool = False
    implied_decimals: int = 0


@dataclass(frozen=True, slots=True)
class ChildSpec:
    """A segment, loop, or unordered group slot within a loop."""

    name: str
    model: type[X12Segment | X12Loop]
    repeat: bool = False
    max_items: int | None = None


class X12Model(BaseModel):
    """Base class for generated X12 models.

    Attributes use Pythonic snake_case names. The original OpenFoo property names are
    available as aliases, so ``model_dump(by_alias=True)`` yields OpenFoo-shaped JSON and
    ``model_validate`` accepts either naming style.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        validate_by_name=True,
        validate_by_alias=True,
        protected_namespaces=(),
    )


class X12Composite(X12Model):
    """A composite data element."""

    x12_id: ClassVar[str] = ""
    x12_elements: ClassVar[tuple[ElementSpec, ...]] = ()


class X12Segment(X12Model):
    """A segment with typed elements and a reference to its source tokens."""

    x12_id: ClassVar[str] = ""
    x12_elements: ClassVar[tuple[ElementSpec, ...]] = ()

    raw_segment: RawSegment | None = Field(default=None, exclude=True, repr=False)


class X12Loop(X12Model):
    """An ordered loop whose first child identifies each loop instance."""

    x12_id: ClassVar[str | None] = None
    x12_children: ClassVar[tuple[ChildSpec, ...]] = ()


class X12Group(X12Loop):
    """An unordered group of segments or loops that may appear in any order."""


class X12TransactionSet(X12Loop):
    """A complete ST/SE transaction set."""

    x12_transaction_set_id: ClassVar[str] = ""
    x12_implementation_version: ClassVar[str | None] = None
    x12_release: ClassVar[str] = ""

    @classmethod
    def parse(
        cls, transaction: RawTransaction, delimiters: X12Delimiters
    ) -> ParseTransactionResult[Self]:
        """Parse a lossless transaction slice into this transaction-set model."""

        return parse_transaction_set(cls, transaction, delimiters)


TransactionT = TypeVar("TransactionT", bound=X12TransactionSet)


@dataclass(frozen=True, slots=True)
class ParseTransactionResult(Generic[TransactionT]):
    """The typed transaction, diagnostics, and any segments that did not fit the layout."""

    transaction: TransactionT | None
    diagnostics: tuple[Diagnostic, ...]
    unmatched_segments: tuple[RawSegment, ...] = ()

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(
            diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "error"
        )


def _empty_counts() -> dict[int, int]:
    return {}


def _empty_values() -> dict[str, list[Any]]:
    return {}


@dataclass(slots=True)
class _Frame:
    model: type[X12Loop]
    first: _Located | None
    index: int = 0
    counts: dict[int, int] = field(default_factory=_empty_counts)
    values: dict[str, list[Any]] = field(default_factory=_empty_values)


@dataclass(frozen=True, slots=True)
class _Located:
    segment: RawSegment
    index: int


def parse_transaction_set(
    model: type[TransactionT], transaction: RawTransaction, delimiters: X12Delimiters
) -> ParseTransactionResult[TransactionT]:
    """Parse ``transaction`` into ``model``; diagnostics never contain source values."""

    context = _Context(model.x12_transaction_set_id, delimiters, transaction.start_index)
    if not transaction.complete:
        context.error(
            "transaction.incomplete", "The transaction has no matching SE segment.", transaction
        )
    if transaction.identifier != model.x12_transaction_set_id:
        context.error(
            "transaction.identifier_invalid",
            f"ST01 does not identify transaction set {model.x12_transaction_set_id}.",
            transaction,
        )
    expected_version = model.x12_implementation_version
    if (
        expected_version is not None
        and transaction.implementation_version is not None
        and transaction.implementation_version != expected_version
    ):
        context.error(
            "transaction.implementation_version_invalid",
            f"ST03 does not identify implementation convention {expected_version}.",
            transaction,
        )

    first = (
        _Located(transaction.segments[0], transaction.start_index) if transaction.segments else None
    )
    root = _Frame(model, first)
    stack = [root]
    unmatched: list[RawSegment] = []
    for offset, segment in enumerate(transaction.segments):
        located = _Located(segment, transaction.start_index + offset)
        if not _place(stack, located, context):
            unmatched.append(segment)
            context.diagnostic(
                "segment.unexpected",
                f"Segment {segment.identifier} does not fit the {model.__name__} layout.",
                located,
                severity="warning",
            )

    built = _build_loop(root, context)
    transaction_model = built if isinstance(built, model) and not context.has_errors else None
    return ParseTransactionResult(
        transaction=transaction_model,
        diagnostics=tuple(context.diagnostics),
        unmatched_segments=tuple(unmatched),
    )


class _Context:
    def __init__(self, transaction_set_id: str, delimiters: X12Delimiters, base_index: int) -> None:
        self.prefix = f"x12.{transaction_set_id or 'transaction'}"
        self.delimiters = delimiters
        self.base_index = base_index
        self.diagnostics: list[Diagnostic] = []

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.severity == "error" for diagnostic in self.diagnostics)

    def error(self, code: str, message: str, transaction: RawTransaction) -> None:
        segment = transaction.segments[0] if transaction.segments else None
        self.diagnostics.append(
            Diagnostic(
                code=f"{self.prefix}.{code}",
                message=message,
                offset=segment.start if segment else 0,
                segment_id=segment.identifier if segment else None,
                segment_index=transaction.start_index,
            )
        )

    def diagnostic(
        self,
        code: str,
        message: str,
        located: _Located | None,
        *,
        severity: Literal["error", "warning"] = "error",
        element_index: int | None = None,
    ) -> None:
        self.diagnostics.append(
            Diagnostic(
                code=f"{self.prefix}.{code}",
                message=message,
                offset=located.segment.start if located else 0,
                severity=severity,
                segment_id=located.segment.identifier if located else None,
                segment_index=located.index if located else None,
                element_index=element_index,
            )
        )


def _place(stack: list[_Frame], located: _Located, context: _Context) -> bool:
    for strict in (True, False):
        for depth in range(len(stack) - 1, -1, -1):
            path = _search(stack[depth], located.segment, context.delimiters, strict)
            if path is None:
                continue
            del stack[depth + 1 :]
            if not strict:
                context.diagnostic(
                    "segment.code_unrecognized",
                    f"Segment {located.segment.identifier} contains a code outside the "
                    "implementation convention; it was placed by segment identifier.",
                    located,
                    severity="warning",
                )
            _apply(stack, path, located)
            return True
    return False


def _search(
    frame: _Frame, segment: RawSegment, delimiters: X12Delimiters, strict: bool
) -> list[int] | None:
    children = frame.model.x12_children
    unordered = issubclass(frame.model, X12Group)
    start = 0 if unordered else frame.index
    for child_index in range(start, len(children)):
        child = children[child_index]
        count = frame.counts.get(child_index, 0)
        if issubclass(child.model, X12Group) and count:
            continue
        if not child.repeat and count:
            continue
        if child.max_items is not None and count >= child.max_items:
            continue
        subpath = _accepts(child.model, segment, delimiters, strict)
        if subpath is not None:
            return [child_index, *subpath]
    return None


def _accepts(
    model: type[X12Segment | X12Loop],
    segment: RawSegment,
    delimiters: X12Delimiters,
    strict: bool,
) -> list[int] | None:
    if issubclass(model, X12Segment):
        if model.x12_id != segment.identifier:
            return None
        if strict and not _codes_match(model.x12_elements, segment, delimiters):
            return None
        return []
    children = model.x12_children
    if not children:
        return None
    candidates = range(len(children)) if issubclass(model, X12Group) else range(1)
    for child_index in candidates:
        subpath = _accepts(children[child_index].model, segment, delimiters, strict)
        if subpath is not None:
            return [child_index, *subpath]
    return None


def _codes_match(
    elements: tuple[ElementSpec, ...], segment: RawSegment, delimiters: X12Delimiters
) -> bool:
    for spec in elements:
        value = _element_value(segment, spec.position)
        if not value:
            continue
        values = _split_repetitions(value, delimiters) if spec.repeat else [value]
        for item in values:
            if not item:
                continue
            if spec.composite is not None:
                components = item.split(delimiters.component)
                for component_spec in spec.composite.x12_elements:
                    if not component_spec.codes:
                        continue
                    position = component_spec.position
                    if (
                        position <= len(components)
                        and components[position - 1]
                        and components[position - 1] not in component_spec.codes
                    ):
                        return False
            elif spec.codes and item not in spec.codes:
                return False
    return True


def _apply(stack: list[_Frame], path: list[int], located: _Located) -> None:
    frame = stack[-1]
    for child_index in path:
        child = frame.model.x12_children[child_index]
        if not issubclass(frame.model, X12Group):
            frame.index = child_index
        frame.counts[child_index] = frame.counts.get(child_index, 0) + 1
        slot = frame.values.setdefault(child.name, [])
        if issubclass(child.model, X12Segment):
            slot.append(located)
            return
        child_frame = _Frame(child.model, located)
        slot.append(child_frame)
        stack.append(child_frame)
        frame = child_frame


def _build_loop(frame: _Frame, context: _Context) -> X12Loop | None:
    data: dict[str, Any] = {}
    for child in frame.model.x12_children:
        items = frame.values.get(child.name)
        if not items:
            continue
        built: list[Any] = []
        for item in items:
            if isinstance(item, _Frame):
                value = _build_loop(item, context)
            elif isinstance(item, _Located) and issubclass(child.model, X12Segment):
                value = _build_segment(child.model, item, context)
            else:
                value = None
            if value is not None:
                built.append(value)
        if not built:
            continue
        data[child.name] = tuple(built) if child.repeat else built[0]
    return _validate(frame.model, data, context, frame.first)


def _build_segment(
    model: type[X12Segment], located: _Located, context: _Context
) -> X12Segment | None:
    segment = located.segment
    data: dict[str, Any] = {"raw_segment": segment}
    known_positions = {spec.position for spec in model.x12_elements}
    for element in segment.elements:
        if element.value and element.position not in known_positions:
            context.diagnostic(
                "element.unexpected",
                f"{segment.identifier}{element.position:02d} is not used by this segment layout.",
                located,
                severity="warning",
                element_index=element.position,
            )
    for spec in model.x12_elements:
        value = _element_value(segment, spec.position)
        if not value:
            continue
        if spec.repeat:
            items = [item for item in _split_repetitions(value, context.delimiters) if item]
            converted = [_convert(spec, item, context, located) for item in items]
            data[spec.name] = tuple(item for item in converted if item is not None)
        else:
            converted_value = _convert(spec, value, context, located)
            if converted_value is not None:
                data[spec.name] = converted_value
    built = _validate(model, data, context, located)
    return built if isinstance(built, X12Segment) else None


def _convert(spec: ElementSpec, value: str, context: _Context, located: _Located) -> Any:
    if spec.composite is not None:
        components = value.split(context.delimiters.component)
        data: dict[str, Any] = {}
        for component_spec in spec.composite.x12_elements:
            position = component_spec.position
            if position <= len(components) and components[position - 1]:
                data[component_spec.name] = _scalar(component_spec, components[position - 1])
        return _validate(spec.composite, data, context, located)
    return _scalar(spec, value)


def _scalar(spec: ElementSpec, value: str) -> Any:
    if spec.data_type == "N" and spec.implied_decimals:
        try:
            return Decimal(value).scaleb(-spec.implied_decimals)
        except InvalidOperation:
            return value
    return value


_ModelT = TypeVar("_ModelT", bound=X12Model)


def _validate(
    model: type[_ModelT],
    data: dict[str, Any],
    context: _Context,
    located: _Located | None,
) -> _ModelT | None:
    try:
        return model.model_validate(data)
    except ValidationError as error:
        for detail in error.errors(include_input=False, include_url=False):
            location = ".".join(str(part) for part in detail["loc"])
            context.diagnostics.append(
                Diagnostic(
                    code=f"{context.prefix}.model.{detail['type']}",
                    message=f"{model.__name__}.{location} failed {detail['type']} validation.",
                    offset=located.segment.start if located else 0,
                    segment_id=located.segment.identifier if located else None,
                    segment_index=located.index if located else None,
                )
            )
        return model.model_construct(**data)


def _element_value(segment: RawSegment, position: int) -> str:
    if position <= len(segment.elements):
        return segment.elements[position - 1].value
    return ""


def _split_repetitions(value: str, delimiters: X12Delimiters) -> list[str]:
    # Before 005010, ISA11 is a standards identifier (usually `U`), not a separator.
    if delimiters.repetition.isalnum():
        return [value]
    return value.split(delimiters.repetition)
