from decimal import Decimal
from pathlib import Path

import pytest

from yedipy.x12 import parse_x12
from yedipy.x12.transactions import parse_transaction

FIXTURES = Path(__file__).parent / "fixtures" / "5010"
CASES = [
    ("837p.edi", "TS837P"),
    ("835.edi", "TS835"),
    ("834.edi", "TS834"),
    ("271.edi", "TS271"),
    ("276.edi", "TS276"),
    ("277.edi", "TS277"),
    ("999.edi", "TS999"),
]


def _contains(value: object, expected: object) -> bool:
    if value == expected:
        return True
    if isinstance(value, dict):
        return any(_contains(item, expected) for item in value.values())
    if isinstance(value, (tuple, list)):
        return any(_contains(item, expected) for item in value)
    return False


@pytest.mark.parametrize(("filename", "expected_model"), CASES)
def test_realistic_5010_transaction(filename: str, expected_model: str) -> None:
    """Parse a hand-crafted, synthetic interchange through both parser layers."""
    parsed = parse_x12((FIXTURES / filename).read_bytes())
    assert parsed.errors == ()
    assert parsed.interchange is not None
    assert len(parsed.interchange.transactions) == 1

    raw = parsed.interchange.transactions[0]
    result = parse_transaction(raw, parsed.interchange.delimiters)
    assert result.errors == (), result.diagnostics
    assert result.unmatched_segments == ()
    assert result.transaction is not None
    assert type(result.transaction).__name__ == expected_model

    values = result.transaction.model_dump(exclude_none=True)
    expected_value = {
        "837p.edi": Decimal(250),
        "835.edi": Decimal(200),
        "834.edi": "SUB12345",
        "271.edi": "1",
        "276.edi": Decimal(150),
        "277.edi": "F0",
        "999.edi": "837",
    }[filename]
    assert _contains(values, expected_value)


def test_realistic_999_typed_values() -> None:
    parsed = parse_x12((FIXTURES / "999.edi").read_bytes())
    assert parsed.errors == ()
    assert parsed.interchange is not None
    result = parse_transaction(parsed.interchange.transactions[0], parsed.interchange.delimiters)
    assert result.errors == ()
    assert result.unmatched_segments == ()
    assert result.transaction is not None
    assert result.transaction.ak9.number_of_accepted_transaction_sets == 1
    assert result.transaction.ak2_loop_1[0].ak2.transaction_set_identifier_code == "837"
