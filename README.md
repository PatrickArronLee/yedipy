# YediPy

**X12 EDI, as typed Python objects.**

YediPy is a free, MIT-licensed Python library for reading, inspecting, and structurally validating X12 EDI. Preserve the original bytes while working with named fields, typed values, and structured diagnostics.

It includes 32 healthcare transaction models across X12 `004010`, `005010`, and `005010` pre-errata, covering eligibility, claim status, authorizations, enrollment, payments, claims, and acknowledgments.

**Supported transaction families:** 270, 271, 276, 277, 277A, 278, 820, 820 HIX, 834, 835, 837D, 837I, 837P, and 999. Availability varies by release; see the [transaction coverage table](https://patrickarronlee.github.io/yedipy/transactions/).

## What It Does

- Detects separators from a fixed-width ISA header.
- Preserves the original source bytes, segment order, elements, and byte offsets.
- Validates ISA/IEA, GS/GE, and ST/SE nesting, control numbers, and counts.
- Slices one interchange into ordered ST/SE transactions.
- Provides a shared parsing API for all supported transaction models.
- Builds typed Pydantic objects with snake_case attributes and JSON serialization.
- Checks required fields, numeric values, and field lengths in typed transaction models.
- Emits diagnostics without including source values.

## Install

Requires Python 3.11 or newer.

```shell
python -m pip install yedipy
```

For development:

```shell
python -m pip install -e ".[dev]"
```

## CLI

```text
yedipy x12 inspect input.edi
yedipy x12 validate input.edi --transaction 270
```

`inspect` reports envelope structure for X12 files without printing source values. The `validate` command currently supports 270 eligibility requests; use the Python API below to parse any supported transaction model.

Both commands return JSON and exit with `0` when their checks pass, `2` for parsing or validation failures, and `3` when the input cannot be read.

## Python API

```python
from pathlib import Path

from yedipy.x12 import parse_x12
from yedipy.x12.transactions import parse_transaction

result = parse_x12(Path("claims.edi").read_bytes())
result.raise_for_errors()

interchange = result.interchange
assert interchange is not None

raw = interchange.transactions[0]
typed = parse_transaction(raw, interchange.delimiters)
if typed.errors:
    raise ValueError([diagnostic.code for diagnostic in typed.errors])

transaction = typed.transaction  # A typed model for the selected transaction.
assert transaction is not None
```

For `004010`, supply the implementation version from `GS08` using the `implementation_version` argument. See the [parsing guide](https://patrickarronlee.github.io/yedipy/transactions/) for examples.

## Documentation

- [Getting started](https://patrickarronlee.github.io/yedipy/getting-started/)
- [Transaction sets](https://patrickarronlee.github.io/yedipy/transactions/)
- [X12 270 support](https://patrickarronlee.github.io/yedipy/x12-270/)
- [API reference](https://patrickarronlee.github.io/yedipy/api/)
- [EDI to Python object model](https://patrickarronlee.github.io/yedipy/edi-to-python.html)
- [Publishing](https://patrickarronlee.github.io/yedipy/publishing/)

## Validation Scope

YediPy 0.1 provides structural validation, not complete implementation-guide compliance. Situational rules, external code lists, and cross-segment requirements are not comprehensively enforced. Additional HL parent/child checks are available for `005010X279A1` 270 requests.

HL7 v2 and FHIR interoperability are on the roadmap; they are not implemented in this release.

## License

YediPy is released under the [MIT License](https://github.com/PatrickArronLee/yedipy/blob/main/LICENSE).