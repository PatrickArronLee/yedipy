# YediPy

YediPy is a Python library for lossless X12 EDI parsing and safe structural validation. It includes typed models for the healthcare transaction sets in X12 releases `004010`, `005010`, and `005010` pre-errata (270, 271, 276, 277, 277A, 278, 820, 820 HIX, 834, 835, 837D, 837I, 837P, and 999), plus a hand-written `005010X279A1` 270 parser with hierarchy validation.

## What It Does

- Detects separators from a fixed-width ISA header.
- Preserves the original source bytes, segment order, elements, and byte offsets.
- Validates ISA/IEA, GS/GE, and ST/SE nesting, control numbers, and counts.
- Slices one interchange into ordered ST/SE transactions.
- Parses 32 transaction sets across three releases into generated Pydantic models with snake_case attributes and OpenFoo aliases.
- Parses the 270 hierarchy with `HL` parent validation.
- Emits diagnostics without including source values.

## Install

After the first PyPI release:

```shell
python -m pip install yedipy
```

From a checkout:

```shell
python -m pip install -e ".[dev]"
```

## CLI

```text
yedipy x12 inspect input.edi
yedipy x12 validate input.edi --transaction 270
```

`inspect` returns structural JSON only. `validate` returns JSON diagnostics and exits with `0` for valid input, `2` for validation failures, and `3` when the input cannot be read.

## Python API

```python
from pathlib import Path

from yedipy.x12 import parse_x12
from yedipy.x12.transactions.v5010 import parse_270

result = parse_x12(Path("request.edi").read_bytes())
result.raise_for_errors()

interchange = result.interchange
assert interchange is not None

typed = parse_270(interchange.transactions[0], interchange.delimiters)
assert typed.transaction is not None
```

Any supported transaction set:

```python
from yedipy.x12.transactions import parse_transaction

claims = parse_transaction(interchange.transactions[0], interchange.delimiters)
claims.errors
claims.transaction  # e.g. yedipy.x12.transactions.v5010.ts837p.TS837P
```

## Documentation

- [Getting started](https://patrickarronlee.github.io/yedipy/getting-started/)
- [Transaction sets](https://patrickarronlee.github.io/yedipy/transactions/)
- [X12 270 support](https://patrickarronlee.github.io/yedipy/x12-270/)
- [API reference](https://patrickarronlee.github.io/yedipy/api/)
- [EDI to Python object model](https://patrickarronlee.github.io/yedipy/edi-to-python.html)
- [Publishing](https://patrickarronlee.github.io/yedipy/publishing/)

## Status

YediPy is pre-release software. It is not a payer-ready eligibility workflow, a FHIR mapper, or a complete X12 implementation.

## License

YediPy is released under the [MIT License](https://github.com/PatrickArronLee/yedipy/blob/main/LICENSE).