from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import pytest

from yedipy.x12 import parse_x12
from yedipy.x12.transactions import parse_transaction

FIXTURES = Path(__file__).parent / "fixtures" / "4010"
CASES = (("837p", "004010X098A1"), ("837i", "004010X096A1"), ("835", "004010X091A1"), ("834", "004010X095A1"), ("270", "004010X092A1"), ("271", "004010X092A1"))

def _values(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, (dict, list, tuple)):
                yield from _values(child)
            else:
                yield key, child
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _values(child)

@pytest.mark.parametrize("stem,implementation_version", CASES, ids=[x[0] for x in CASES])
def test_realistic_4010_transaction_parses(stem: str, implementation_version: str) -> None:
    parsed = parse_x12((FIXTURES / f"{stem}.edi").read_bytes())
    assert parsed.errors == ()
    assert parsed.interchange is not None
    raw = parsed.interchange.transactions[0]
    result = parse_transaction(raw, parsed.interchange.delimiters, implementation_version=implementation_version)
    assert result.errors == ()
    assert result.unmatched_segments == ()
    assert result.transaction is not None
    data = result.transaction.model_dump()

    if stem in {"837p", "837i"}:
        assert data["bht_beginning_of_hierarchical_transaction"]["submitter_transaction_identifier"] in {"PC12345", "IN12345"}
        claim = data["loop_2000a"][0]["loop_2000b"][0]["loop_2300"][0]
        assert len(claim["loop_2400"]) == 2
        assert any(value in {"K219", "J189"} for _, value in _values(claim))
        assert any(value in {Decimal(250), Decimal(1200)} for _, value in _values(claim))
    elif stem == "835":
        assert data["loop_2000"][0]["loop_2100"][0]["loop_2110"]
        assert any(value == Decimal(250) for _, value in _values(data))
        assert len(data["loop_2000"][0]["loop_2100"][0]["loop_2110"]) == 2
    elif stem == "834":
        assert len(data["loop_2000"]) == 2
        assert any(value == "MEM12345" for _, value in _values(data))
    elif stem == "270":
        assert any(value == "30" for _, value in _values(data))
        assert any(value == "MEM12345" for _, value in _values(data))
    else:
        assert any(value == "PLAN-A" for _, value in _values(data))
        assert any(value == "MEM12345" for _, value in _values(data))
