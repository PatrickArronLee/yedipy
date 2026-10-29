"""Lossless, protocol-level X12 data types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class X12Delimiters:
    """The separators declared by an ISA header."""

    element: str
    repetition: str
    component: str
    segment: str


@dataclass(frozen=True, slots=True)
class RawElement:
    """An element with its one-based position and original byte range."""

    position: int
    value: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class RawSegment:
    """A source-ordered X12 segment without semantic interpretation."""

    identifier: str
    elements: tuple[RawElement, ...]
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class RawTransaction:
    """A source-ordered ST/SE transaction slice."""

    identifier: str | None
    control_number: str | None
    implementation_version: str | None
    segments: tuple[RawSegment, ...]
    start_index: int
    end_index: int
    complete: bool


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A safe structural diagnostic that never includes source values."""

    code: str
    message: str
    offset: int
    severity: Literal["error", "warning"] = "error"
    segment_id: str | None = None
    segment_index: int | None = None
    element_index: int | None = None


class X12ParseError(ValueError):
    """Raised when a caller requests a successful parse from invalid input."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]) -> None:
        codes = ", ".join(diagnostic.code for diagnostic in diagnostics)
        super().__init__(f"X12 parsing failed: {codes}")
        self.diagnostics = diagnostics


@dataclass(frozen=True, slots=True)
class X12Interchange:
    """A lossless X12 interchange and its protocol-level tokens."""

    source: bytes
    delimiters: X12Delimiters
    segments: tuple[RawSegment, ...]
    transactions: tuple[RawTransaction, ...]

    def to_source(self) -> bytes:
        """Return the unmodified input bytes."""

        return self.source


@dataclass(frozen=True, slots=True)
class X12ParseResult:
    """A recoverable parse result with ordered diagnostics."""

    interchange: X12Interchange | None
    diagnostics: tuple[Diagnostic, ...]

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "error")

    def raise_for_errors(self) -> None:
        """Raise a redacted error when any parse errors are present."""

        if self.errors:
            raise X12ParseError(self.errors)