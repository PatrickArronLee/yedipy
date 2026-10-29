# Getting Started

## Requirements

- Python 3.11 or newer.
- An X12 file beginning with a valid fixed-width `ISA` header.

## Install

Install the released package:

```shell
python -m pip install yedipy
```

For local development:

```shell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

## Inspect a File

```shell
yedipy x12 inspect request.edi
```

The command emits structural JSON: delimiters, segment identifiers, offsets, transaction boundaries, and diagnostics. It does not emit source element values.

## Validate a 270

```shell
yedipy x12 validate request.edi --transaction 270
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | The input and requested 270 structures are valid. |
| `2` | Parsing or validation failed. |
| `3` | The input file could not be read. |

## Parse in Python

```python
from pathlib import Path

from yedipy.x12 import parse_x12
from yedipy.x12.transactions.v5010 import parse_270

parsed = parse_x12(Path("request.edi").read_bytes())
parsed.raise_for_errors()

interchange = parsed.interchange
assert interchange is not None
typed = parse_270(interchange.transactions[0], interchange.delimiters)
typed_errors = typed.errors
```

`parse_x12` returns a recoverable result. Check `errors` before accessing parsed structures, or use `raise_for_errors()` when failure should stop processing.