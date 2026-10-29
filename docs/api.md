# API Reference

## `parse_x12(payload)`

Parses `bytes` or an ASCII `str` into an `X12ParseResult`.

| Result member | Description |
| --- | --- |
| `interchange` | An `X12Interchange` when the ISA header is valid. |
| `diagnostics` | Ordered structural diagnostics. |
| `errors` | Diagnostics whose severity is `error`. |
| `raise_for_errors()` | Raises `X12ParseError` using diagnostic codes only. |

## `X12Interchange`

| Member | Description |
| --- | --- |
| `source` | Original input bytes. |
| `delimiters` | Element, repetition, component, and segment separators. |
| `segments` | Ordered `RawSegment` values with byte offsets. |
| `transactions` | Ordered `RawTransaction` ST/SE slices. |
| `to_source()` | Returns `source` unchanged. |

## `parse_270(transaction, delimiters)`

Parses one `RawTransaction` into a `Parse270Result`.

| Result member | Description |
| --- | --- |
| `transaction` | A `Transaction270` when structural validation succeeds. |
| `diagnostics` | 270-specific structural diagnostics. |
| `errors` | Error diagnostics. |

The resulting `Transaction270` exposes `control_number`, `implementation_version`, `beginning`, and `information_sources`.

## `parse_transaction(transaction, delimiters, *, implementation_version=None, release=None)`

Parses one `RawTransaction` with the generated model selected from `ST01` and `ST03` (or `implementation_version`). Returns a `ParseTransactionResult`. Raises `LookupError` when no single model matches.

| Result member | Description |
| --- | --- |
| `transaction` | The generated transaction model, or `None` when errors are present. |
| `diagnostics` | Placement and validation diagnostics. |
| `errors` | Error diagnostics. |
| `unmatched_segments` | Segments that did not fit the transaction layout. |

## `load_transaction_model(transaction_set_id, *, implementation_version=None, release=None)`

Imports and returns a generated `X12TransactionSet` subclass. `find_transaction_set` returns its `TransactionSetEntry` without importing it, and `TRANSACTION_SETS` lists every entry.

## `X12TransactionSet.parse(transaction, delimiters)`

Parses with a specific generated model, for example `TS835.parse(raw, delimiters)`. See [Transaction Sets](transactions.md).
