"""Versioned X12 transaction-set models and parsers.

Generated models live in release packages:

- ``yedipy.x12.transactions.v4010``
- ``yedipy.x12.transactions.v5010``
- ``yedipy.x12.transactions.v5010_pre_errata``

Each module (for example ``v5010.ts837p``) is imported lazily through
``load_transaction_model`` so that importing this package stays fast.
"""

from __future__ import annotations

import importlib

from ..model import RawTransaction, X12Delimiters
from ._registry import TRANSACTION_SETS, TransactionSetEntry
from ._runtime import (
    ChildSpec,
    ElementSpec,
    ParseTransactionResult,
    X12Composite,
    X12Group,
    X12Loop,
    X12Model,
    X12Segment,
    X12TransactionSet,
    parse_transaction_set,
)

__all__ = [
    "TRANSACTION_SETS",
    "ChildSpec",
    "ElementSpec",
    "ParseTransactionResult",
    "TransactionSetEntry",
    "X12Composite",
    "X12Group",
    "X12Loop",
    "X12Model",
    "X12Segment",
    "X12TransactionSet",
    "find_transaction_set",
    "load_transaction_model",
    "parse_transaction",
]


def find_transaction_set(
    transaction_set_id: str,
    *,
    implementation_version: str | None = None,
    release: str | None = None,
) -> TransactionSetEntry:
    """Return the registry entry for a transaction set, or raise ``LookupError``.

    ``release`` is ``"004010"``, ``"005010"``, or ``"005010-pre-errata"``. When several
    implementation conventions share a transaction set identifier (837 P/I/D, 820/820 HIX,
    277/277A), pass ``implementation_version`` to choose one.
    """

    candidates = [
        entry for entry in TRANSACTION_SETS if entry.transaction_set_id == transaction_set_id
    ]
    if release is not None:
        candidates = [entry for entry in candidates if entry.release == release]
    if implementation_version is not None:
        exact = [
            entry for entry in candidates if entry.implementation_version == implementation_version
        ]
        candidates = exact or [
            entry for entry in candidates if entry.implementation_version is None
        ]
    if len(candidates) != 1:
        found = "no" if not candidates else "multiple"
        raise LookupError(
            f"Found {found} models for transaction set {transaction_set_id}; "
            "pass implementation_version and/or release."
        )
    return candidates[0]


def load_transaction_model(
    transaction_set_id: str,
    *,
    implementation_version: str | None = None,
    release: str | None = None,
) -> type[X12TransactionSet]:
    """Import and return the generated model class for a transaction set."""

    entry = find_transaction_set(
        transaction_set_id, implementation_version=implementation_version, release=release
    )
    model = getattr(importlib.import_module(entry.module), entry.class_name)
    if not isinstance(model, type) or not issubclass(model, X12TransactionSet):
        raise TypeError(f"{entry.module}.{entry.class_name} is not a transaction-set model")
    return model


def parse_transaction(
    transaction: RawTransaction,
    delimiters: X12Delimiters,
    *,
    implementation_version: str | None = None,
    release: str | None = None,
) -> ParseTransactionResult[X12TransactionSet]:
    """Parse a transaction slice with the model selected from ST01 and ST03.

    004010 transactions do not carry ST03; pass the GS08 value as
    ``implementation_version`` for them.
    """

    model = load_transaction_model(
        transaction.identifier or "",
        implementation_version=implementation_version or transaction.implementation_version,
        release=release,
    )
    return parse_transaction_set(model, transaction, delimiters)
