"""Generated registry of X12 transaction-set models. Do not edit by hand."""

from __future__ import annotations

from typing import NamedTuple


class TransactionSetEntry(NamedTuple):
    """Where to import the model for one release and implementation convention."""

    release: str
    transaction_set_id: str
    implementation_version: str | None
    module: str
    class_name: str


TRANSACTION_SETS: tuple[TransactionSetEntry, ...] = (
    TransactionSetEntry(
        "004010", "270", "004010X092A1", "yedipy.x12.transactions.v4010.ts270", "TS270"
    ),
    TransactionSetEntry(
        "004010", "271", "004010X092A1", "yedipy.x12.transactions.v4010.ts271", "TS271"
    ),
    TransactionSetEntry(
        "004010", "276", "004010X093A1", "yedipy.x12.transactions.v4010.ts276", "TS276"
    ),
    TransactionSetEntry(
        "004010", "277", "004010X093A1", "yedipy.x12.transactions.v4010.ts277", "TS277"
    ),
    TransactionSetEntry(
        "004010", "278", "004010X094A1", "yedipy.x12.transactions.v4010.ts278", "TS278"
    ),
    TransactionSetEntry(
        "004010", "820", "004010X061A1", "yedipy.x12.transactions.v4010.ts820", "TS820"
    ),
    TransactionSetEntry(
        "004010", "834", "004010X095A1", "yedipy.x12.transactions.v4010.ts834", "TS834"
    ),
    TransactionSetEntry(
        "004010", "835", "004010X091A1", "yedipy.x12.transactions.v4010.ts835", "TS835"
    ),
    TransactionSetEntry(
        "004010", "837", "004010X097A1", "yedipy.x12.transactions.v4010.ts837d", "TS837D"
    ),
    TransactionSetEntry(
        "004010", "837", "004010X096A1", "yedipy.x12.transactions.v4010.ts837i", "TS837I"
    ),
    TransactionSetEntry(
        "004010", "837", "004010X098A1", "yedipy.x12.transactions.v4010.ts837p", "TS837P"
    ),
    TransactionSetEntry(
        "005010", "270", "005010X279A1", "yedipy.x12.transactions.v5010.ts270", "TS270"
    ),
    TransactionSetEntry(
        "005010", "271", "005010X279A1", "yedipy.x12.transactions.v5010.ts271", "TS271"
    ),
    TransactionSetEntry(
        "005010", "276", "005010X212", "yedipy.x12.transactions.v5010.ts276", "TS276"
    ),
    TransactionSetEntry(
        "005010", "277", "005010X212", "yedipy.x12.transactions.v5010.ts277", "TS277"
    ),
    TransactionSetEntry(
        "005010", "277", "005010X214", "yedipy.x12.transactions.v5010.ts277a", "TS277A"
    ),
    TransactionSetEntry(
        "005010", "278", "005010X217", "yedipy.x12.transactions.v5010.ts278", "TS278"
    ),
    TransactionSetEntry(
        "005010", "820", "005010X218", "yedipy.x12.transactions.v5010.ts820", "TS820"
    ),
    TransactionSetEntry(
        "005010", "820", "005010X306", "yedipy.x12.transactions.v5010.ts820hix", "TS820HIX"
    ),
    TransactionSetEntry(
        "005010", "834", "005010X220A1", "yedipy.x12.transactions.v5010.ts834", "TS834"
    ),
    TransactionSetEntry(
        "005010", "835", "005010X221A1", "yedipy.x12.transactions.v5010.ts835", "TS835"
    ),
    TransactionSetEntry(
        "005010", "837", "005010X224A2", "yedipy.x12.transactions.v5010.ts837d", "TS837D"
    ),
    TransactionSetEntry(
        "005010", "837", "005010X223A2", "yedipy.x12.transactions.v5010.ts837i", "TS837I"
    ),
    TransactionSetEntry(
        "005010", "837", "005010X222A1", "yedipy.x12.transactions.v5010.ts837p", "TS837P"
    ),
    TransactionSetEntry("005010", "999", None, "yedipy.x12.transactions.v5010.ts999", "TS999"),
    TransactionSetEntry(
        "005010-pre-errata",
        "270",
        "005010X279",
        "yedipy.x12.transactions.v5010_pre_errata.ts270",
        "TS270",
    ),
    TransactionSetEntry(
        "005010-pre-errata",
        "271",
        "005010X279",
        "yedipy.x12.transactions.v5010_pre_errata.ts271",
        "TS271",
    ),
    TransactionSetEntry(
        "005010-pre-errata",
        "834",
        "005010X220",
        "yedipy.x12.transactions.v5010_pre_errata.ts834",
        "TS834",
    ),
    TransactionSetEntry(
        "005010-pre-errata",
        "835",
        "005010X221",
        "yedipy.x12.transactions.v5010_pre_errata.ts835",
        "TS835",
    ),
    TransactionSetEntry(
        "005010-pre-errata",
        "837",
        "005010X224A1",
        "yedipy.x12.transactions.v5010_pre_errata.ts837d",
        "TS837D",
    ),
    TransactionSetEntry(
        "005010-pre-errata",
        "837",
        "005010X223A1",
        "yedipy.x12.transactions.v5010_pre_errata.ts837i",
        "TS837I",
    ),
    TransactionSetEntry(
        "005010-pre-errata",
        "837",
        "005010X222",
        "yedipy.x12.transactions.v5010_pre_errata.ts837p",
        "TS837P",
    ),
)
