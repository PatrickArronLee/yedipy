from __future__ import annotations

import importlib

import pytest
from x12_samples import minimal_interchange

from yedipy.x12 import parse_x12
from yedipy.x12.transactions import (
    TRANSACTION_SETS,
    TransactionSetEntry,
    load_transaction_model,
    parse_transaction,
)
from yedipy.x12.transactions._runtime import X12TransactionSet


def _model(entry: TransactionSetEntry) -> type[X12TransactionSet]:
    model = getattr(importlib.import_module(entry.module), entry.class_name)
    assert issubclass(model, X12TransactionSet)
    return model


def test_registry_covers_every_release() -> None:
    releases = {entry.release for entry in TRANSACTION_SETS}
    assert releases == {"004010", "005010", "005010-pre-errata"}
    assert len(TRANSACTION_SETS) == 32


@pytest.mark.parametrize(
    "entry", TRANSACTION_SETS, ids=lambda entry: f"{entry.release}-{entry.class_name}"
)
def test_minimal_transaction_round_trips(entry: TransactionSetEntry) -> None:
    model = _model(entry)
    parsed = parse_x12(minimal_interchange(model))
    assert parsed.errors == ()
    assert parsed.interchange is not None
    raw = parsed.interchange.transactions[0]

    result = model.parse(raw, parsed.interchange.delimiters)

    assert result.errors == ()
    assert result.unmatched_segments == ()
    assert result.transaction is not None
    by_alias = result.transaction.model_dump(by_alias=True, exclude_none=True)
    reloaded = type(result.transaction).model_validate(by_alias)
    assert reloaded.model_dump(by_alias=True, exclude_none=True) == by_alias


def test_load_transaction_model_resolves_by_version() -> None:
    model = load_transaction_model("837", implementation_version="005010X222A1")
    assert model.__name__ == "TS837P"
    assert model.x12_release == "005010"


def test_parse_transaction_detects_model_from_st03() -> None:
    model = load_transaction_model("835", implementation_version="005010X221A1")
    parsed = parse_x12(minimal_interchange(model))
    assert parsed.interchange is not None

    result = parse_transaction(parsed.interchange.transactions[0], parsed.interchange.delimiters)

    assert result.errors == ()
    assert type(result.transaction).__name__ == "TS835"


def test_4010_requires_explicit_version() -> None:
    model = load_transaction_model("270", release="004010")
    parsed = parse_x12(minimal_interchange(model))
    assert parsed.interchange is not None
    raw = parsed.interchange.transactions[0]

    with pytest.raises(LookupError):
        parse_transaction(raw, parsed.interchange.delimiters)
    result = parse_transaction(
        raw, parsed.interchange.delimiters, implementation_version="004010X092A1"
    )
    assert result.errors == ()


def test_pythonic_names_and_OpenFoo_aliases() -> None:
    from yedipy.x12.transactions.v5010.ts270 import NM1InformationSourceName

    fields = NM1InformationSourceName.model_fields
    assert fields["entity_identifier_code_01"].alias == "EntityIdentifierCode_01"
    assert fields["response_contact_last_or_organization_name"].alias == (
        "ResponseContactLastorOrganizationName_03"
    )
