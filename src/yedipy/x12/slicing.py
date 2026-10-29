"""Transaction slicing for lossless X12 segment streams."""

from __future__ import annotations

from .model import RawSegment, RawTransaction


def slice_transactions(segments: tuple[RawSegment, ...]) -> tuple[RawTransaction, ...]:
    """Return every ST/SE slice while preserving source order and recovery state."""

    transactions: list[RawTransaction] = []
    start_index: int | None = None

    for index, segment in enumerate(segments):
        if segment.identifier == "ST":
            if start_index is not None:
                transactions.append(_make_transaction(segments, start_index, index - 1, False))
            start_index = index
        elif segment.identifier == "SE" and start_index is not None:
            transactions.append(_make_transaction(segments, start_index, index, True))
            start_index = None

    if start_index is not None:
        transactions.append(_make_transaction(segments, start_index, len(segments) - 1, False))
    return tuple(transactions)


def _make_transaction(
    segments: tuple[RawSegment, ...], start_index: int, end_index: int, complete: bool
) -> RawTransaction:
    start_segment = segments[start_index]
    return RawTransaction(
        identifier=_element(start_segment, 1),
        control_number=_element(start_segment, 2),
        implementation_version=_element(start_segment, 3),
        segments=segments[start_index : end_index + 1],
        start_index=start_index,
        end_index=end_index,
        complete=complete,
    )


def _element(segment: RawSegment, position: int) -> str | None:
    if position <= len(segment.elements):
        return segment.elements[position - 1].value
    return None