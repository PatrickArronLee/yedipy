"""Command-line interface for YediPy."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .x12 import Diagnostic, X12ParseResult, parse_x12
from .x12.transactions.v5010 import parse_270


def main(argv: Sequence[str] | None = None) -> int:
    """Run the YediPy command-line interface."""

    parser = _build_parser()
    arguments = parser.parse_args(argv)
    try:
        source = arguments.input.read_bytes()
    except OSError:
        _write_output(
            {
                "valid": False,
                "diagnostics": [_diagnostic_dict(Diagnostic("x12.input.unreadable", "Input is unreadable.", 0))],
            }
        )
        return 3

    parsed = parse_x12(source)
    if arguments.command == "inspect":
        return _inspect(parsed)
    return _validate(parsed, arguments.transaction)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yedipy")
    protocol_parsers = parser.add_subparsers(dest="protocol", required=True)
    x12_parser = protocol_parsers.add_parser("x12")
    command_parsers = x12_parser.add_subparsers(dest="command", required=True)

    inspect_parser = command_parsers.add_parser("inspect")
    inspect_parser.add_argument("input", type=Path)

    validate_parser = command_parsers.add_parser("validate")
    validate_parser.add_argument("input", type=Path)
    validate_parser.add_argument("--transaction", choices=("270",), required=True)
    return parser


def _inspect(parsed: X12ParseResult) -> int:
    interchange = parsed.interchange
    output: dict[str, object] = {
        "valid": not parsed.errors,
        "diagnostics": [_diagnostic_dict(diagnostic) for diagnostic in parsed.diagnostics],
    }
    if interchange is not None:
        output["delimiters"] = {
            "element": interchange.delimiters.element,
            "repetition": interchange.delimiters.repetition,
            "component": interchange.delimiters.component,
            "segment": interchange.delimiters.segment,
        }
        output["segments"] = [
            {
                "index": index,
                "identifier": segment.identifier,
                "element_count": len(segment.elements),
                "start": segment.start,
                "end": segment.end,
            }
            for index, segment in enumerate(interchange.segments)
        ]
        output["transactions"] = [
            {
                "identifier": transaction.identifier,
                "complete": transaction.complete,
                "start_index": transaction.start_index,
                "end_index": transaction.end_index,
            }
            for transaction in interchange.transactions
        ]
    _write_output(output)
    return 0 if not parsed.errors else 2


def _validate(parsed: X12ParseResult, transaction_id: str) -> int:
    diagnostics = list(parsed.diagnostics)
    interchange = parsed.interchange
    if interchange is not None and transaction_id == "270":
        transactions = [transaction for transaction in interchange.transactions if transaction.identifier == "270"]
        if not transactions:
            diagnostics.append(Diagnostic("x12.270.transaction_missing", "No 270 transaction found.", 0))
        for transaction in transactions:
            diagnostics.extend(parse_270(transaction, interchange.delimiters).diagnostics)

    _write_output(
        {
            "valid": not any(diagnostic.severity == "error" for diagnostic in diagnostics),
            "diagnostics": [_diagnostic_dict(diagnostic) for diagnostic in diagnostics],
        }
    )
    return 0 if not any(diagnostic.severity == "error" for diagnostic in diagnostics) else 2


def _diagnostic_dict(diagnostic: Diagnostic) -> dict[str, object]:
    return {
        "code": diagnostic.code,
        "message": diagnostic.message,
        "severity": diagnostic.severity,
        "offset": diagnostic.offset,
        "segment_id": diagnostic.segment_id,
        "segment_index": diagnostic.segment_index,
        "element_index": diagnostic.element_index,
    }


def _write_output(output: dict[str, object]) -> None:
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())