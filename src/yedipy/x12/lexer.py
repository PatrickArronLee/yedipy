"""Delimiter-aware, lossless X12 lexer."""

from __future__ import annotations

from .model import (
    Diagnostic,
    RawElement,
    RawSegment,
    X12Delimiters,
    X12Interchange,
    X12ParseResult,
)
from .slicing import slice_transactions
from .validation import validate_envelopes

_ISA_LENGTH = 106
_ISA_ELEMENT_LENGTHS = (2, 10, 2, 10, 2, 15, 2, 15, 6, 4, 1, 5, 9, 1, 1, 1)


def parse_x12(payload: bytes | str) -> X12ParseResult:
    """Lex an X12 payload without changing source order or content."""

    source, coercion_diagnostic = _coerce_source(payload)
    if coercion_diagnostic is not None:
        return X12ParseResult(interchange=None, diagnostics=(coercion_diagnostic,))

    delimiters, isa_diagnostics = _read_isa_delimiters(source)
    if delimiters is None:
        return X12ParseResult(interchange=None, diagnostics=isa_diagnostics)

    segments, segment_diagnostics = _read_segments(source, delimiters)
    envelope_diagnostics = validate_envelopes(segments)
    diagnostics = isa_diagnostics + segment_diagnostics + envelope_diagnostics
    interchange = X12Interchange(
        source=source,
        delimiters=delimiters,
        segments=segments,
        transactions=slice_transactions(segments),
    )
    return X12ParseResult(interchange=interchange, diagnostics=diagnostics)


def _coerce_source(payload: bytes | str) -> tuple[bytes, Diagnostic | None]:
    if isinstance(payload, bytes):
        return payload, None
    try:
        return payload.encode("ascii"), None
    except UnicodeEncodeError:
        return b"", Diagnostic(
            code="x12.source.non_ascii",
            message="X12 source must use ASCII characters.",
            offset=0,
        )


def _read_isa_delimiters(source: bytes) -> tuple[X12Delimiters | None, tuple[Diagnostic, ...]]:
    if len(source) < _ISA_LENGTH:
        return None, (
            Diagnostic(
                code="x12.isa.truncated",
                message="X12 ISA header is shorter than 106 bytes.",
                offset=0,
            ),
        )
    if source[:3] != b"ISA":
        return None, (
            Diagnostic(
                code="x12.isa.missing",
                message="X12 input must begin with an ISA header.",
                offset=0,
            ),
        )

    element_separator = source[3:4]
    header = source[:_ISA_LENGTH]
    fields = header[:-1].split(element_separator)
    field_lengths = tuple(len(field) for field in fields[1:])
    if len(fields) != 17 or fields[0] != b"ISA" or field_lengths != _ISA_ELEMENT_LENGTHS:
        return None, (
            Diagnostic(
                code="x12.isa.invalid",
                message="X12 ISA header does not match the fixed-width layout.",
                offset=0,
            ),
        )

    return (
        X12Delimiters(
            element=element_separator.decode("ascii"),
            repetition=fields[11].decode("ascii"),
            component=fields[16].decode("ascii"),
            segment=header[-1:].decode("ascii"),
        ),
        (),
    )


def _read_segments(
    source: bytes, delimiters: X12Delimiters
) -> tuple[tuple[RawSegment, ...], tuple[Diagnostic, ...]]:
    terminator = delimiters.segment.encode("ascii")
    separator = delimiters.element.encode("ascii")
    segments: list[RawSegment] = []
    diagnostics: list[Diagnostic] = []
    offset = 0

    while offset < len(source):
        while offset < len(source) and source[offset : offset + 1] in (b"\r", b"\n"):
            offset += 1
        if offset == len(source):
            break

        terminator_offset = source.find(terminator, offset)
        if terminator_offset == -1:
            diagnostics.append(
                Diagnostic(
                    code="x12.segment.unterminated",
                    message="X12 segment is missing its terminator.",
                    offset=offset,
                    segment_index=len(segments),
                )
            )
            break

        body = source[offset:terminator_offset]
        segment = _make_segment(body, offset, separator, len(segments))
        if isinstance(segment, Diagnostic):
            diagnostics.append(segment)
        else:
            segments.append(segment)
        offset = terminator_offset + 1

    return tuple(segments), tuple(diagnostics)


def _make_segment(
    body: bytes, start: int, separator: bytes, segment_index: int
) -> RawSegment | Diagnostic:
    fields = body.split(separator)
    identifier = fields[0]
    if not identifier:
        return Diagnostic(
            code="x12.segment.empty",
            message="X12 input contains an empty segment.",
            offset=start,
            segment_index=segment_index,
        )
    try:
        decoded_identifier = identifier.decode("ascii")
        elements = _make_elements(fields[1:], start + len(identifier), separator)
    except UnicodeDecodeError:
        return Diagnostic(
            code="x12.segment.non_ascii",
            message="X12 segment contains non-ASCII data.",
            offset=start,
            segment_index=segment_index,
        )
    return RawSegment(
        identifier=decoded_identifier,
        elements=elements,
        start=start,
        end=start + len(body) + 1,
    )


def _make_elements(fields: list[bytes], start: int, separator: bytes) -> tuple[RawElement, ...]:
    elements: list[RawElement] = []
    offset = start
    for position, field in enumerate(fields, start=1):
        offset += len(separator)
        elements.append(
            RawElement(
                position=position,
                value=field.decode("ascii"),
                start=offset,
                end=offset + len(field),
            )
        )
        offset += len(field)
    return tuple(elements)