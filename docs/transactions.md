# Transaction Sets

YediPy ships generated, typed Pydantic models for every transaction set in three X12 releases:

| Release | Package | Transaction sets |
| --- | --- | --- |
| `004010` | `yedipy.x12.transactions.v4010` | 270, 271, 276, 277, 278, 820, 834, 835, 837D, 837I, 837P |
| `005010` | `yedipy.x12.transactions.v5010` | 270, 271, 276, 277, 277A, 278, 820, 820 HIX, 834, 835, 837D, 837I, 837P, 999 |
| `005010-pre-errata` | `yedipy.x12.transactions.v5010_pre_errata` | 270, 271, 834, 835, 837D, 837I, 837P |

Each transaction set has its own module, for example `v5010.ts837p`, `v4010.ts835`, or `v5010_pre_errata.ts270`. The module exposes a transaction class named after the set (`TS837P`, `TS835`, `TS270`) plus classes for every loop, segment, and composite it uses.

## Parse Any Supported Transaction

```python
from pathlib import Path

from yedipy.x12 import parse_x12
from yedipy.x12.transactions import parse_transaction

parsed = parse_x12(Path("claims.edi").read_bytes())
parsed.raise_for_errors()
interchange = parsed.interchange
assert interchange is not None

result = parse_transaction(interchange.transactions[0], interchange.delimiters)
if result.errors:
    raise SystemExit([diagnostic.code for diagnostic in result.errors])
claim_set = result.transaction
```

`parse_transaction` selects the model from `ST01` and `ST03`. 004010 transactions have no `ST03`, so pass the `GS08` value:

```python
result = parse_transaction(raw, delimiters, implementation_version="004010X098A1")
```

To parse with a specific model, call its `parse` class method:

```python
from yedipy.x12.transactions.v5010.ts835 import TS835

result = TS835.parse(raw, delimiters)
payment = result.transaction
```

Use `load_transaction_model(transaction_set_id, implementation_version=..., release=...)` to look up a model class without parsing, and `TRANSACTION_SETS` to list every generated model.

## Naming

Attributes use Pythonic snake_case names. The original OpenFoo property names remain available as Pydantic aliases:

```python
from yedipy.x12.transactions.v5010.ts270 import NM1InformationSourceName

field = NM1InformationSourceName.model_fields["entity_identifier_code_01"]
field.alias  # "EntityIdentifierCode_01"
```

- Segment and loop attributes keep the segment identifier as a prefix: `nm1_subscriber_name`, `loop_2100c`, `ref_subscriber_additional_identification`.
- Element attributes drop the trailing position unless two elements in the same segment would share a name, as with `entity_identifier_code_01` and `entity_identifier_code_11`.
- `model_dump(by_alias=True)` produces OpenFoo-shaped JSON; `model_validate` accepts either naming style.

## Types

| X12 type | Python type |
| --- | --- |
| `AN`, `ID`, `DT`, `TM` | `str` (dates and times are kept as written) |
| `R` | `decimal.Decimal` |
| `N0` | `int` |
| `N2` and other implied-decimal types | `decimal.Decimal`, already scaled |
| Repeating elements and repeating segments or loops | `tuple[...]` |
| Composite elements | Generated composite models |

Each segment model keeps its source tokens in `raw_segment`, which is excluded from serialization.

## How Segments Are Placed

The parser walks the transaction in order. Each segment is assigned to the first slot that matches its identifier and every implementation-guide code it carries (for example `NM101`, `HL03`, `REF01`, or a `HI` composite qualifier). It searches the current loop and then the enclosing loops. A segment that matches only by identifier is still placed, with a `segment.code_unrecognized` warning. A segment that fits nowhere is returned in `unmatched_segments`, with a `segment.unexpected` warning.

After placement, every segment, loop, and transaction is validated by its model. Missing required segments or elements, invalid numbers, and length violations become error diagnostics whose messages never include source values. `result.transaction` is `None` whenever an error diagnostic is present.

## Regenerating Models

The models are generated from OpenFoo OpenAPI specifications, which are not distributed with YediPy:

```shell
python tools/generate_x12_models.py PATH/TO/open-api-specs
```

The specification directory must contain `004010`, `005010`, and `005010-pre-errata` folders of `en-<id>-OpenFoo.json` files. The generator rewrites the release packages and `yedipy/x12/transactions/_registry.py`, then formats them with Ruff.

## Current Limits

- Placement is structural. It does not enforce situational rules, cross-segment syntax notes, or `HL` parent consistency. The hand-written `v5010.parse_270` still validates `HL` parent consistency for 270.
- Code values are used for placement but are not otherwise validated.
- Models cannot yet be serialized back to X12.
