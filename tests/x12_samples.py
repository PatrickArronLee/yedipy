"""Build minimal X12 interchanges from generated model metadata."""

from __future__ import annotations

from yedipy.x12.transactions._runtime import (
    ElementSpec,
    X12Composite,
    X12Group,
    X12Loop,
    X12Segment,
    X12TransactionSet,
)


def _min_length(model: type[X12Segment | X12Composite], name: str) -> int:
    for item in model.model_fields[name].metadata:
        value = getattr(item, "min_length", None)
        if isinstance(value, int):
            return value
    return 1


def _max_length(model: type[X12Segment | X12Composite], name: str) -> int | None:
    for item in model.model_fields[name].metadata:
        value = getattr(item, "max_length", None)
        if isinstance(value, int):
            return value
    return None


def _value(model: type[X12Segment | X12Composite], spec: ElementSpec) -> str:
    if spec.composite is not None:
        return _join(spec.composite, ":")
    if spec.codes:
        return spec.codes[0]
    if spec.data_type in {"R", "N"}:
        return "1"
    if spec.data_type == "DT":
        return "20240101" if (_max_length(model, spec.name) or 8) >= 8 else "240101"
    if spec.data_type == "TM":
        return "1200"
    return "A" * _min_length(model, spec.name)


def _join(model: type[X12Segment | X12Composite], separator: str) -> str:
    values: dict[int, str] = {}
    for spec in model.x12_elements:
        if model.model_fields[spec.name].is_required():
            values[spec.position] = _value(model, spec)
    width = max(values, default=0)
    return separator.join(values.get(position, "") for position in range(1, width + 1))


def segment_text(model: type[X12Segment], overrides: dict[int, str] | None = None) -> str:
    values: dict[int, str] = {}
    for spec in model.x12_elements:
        if model.model_fields[spec.name].is_required():
            values[spec.position] = _value(model, spec)
    values.update(overrides or {})
    width = max(values, default=0)
    elements = [values.get(position, "") for position in range(1, width + 1)]
    return "*".join([model.x12_id, *elements])


def _walk(model: type[X12Loop], output: list[str], transaction: type[X12TransactionSet]) -> None:
    for child in model.x12_children:
        is_header = issubclass(child.model, X12Segment) and child.model.x12_id == "ST"
        if not model.model_fields[child.name].is_required() and not is_header:
            continue
        target = child.model
        if issubclass(target, X12Segment):
            if target.x12_id == "ST":
                version = transaction.x12_implementation_version
                overrides = {1: transaction.x12_transaction_set_id, 2: "0001"}
                if version and transaction.x12_release != "004010":
                    overrides[3] = version
                output.append(segment_text(target, overrides))
            elif target.x12_id == "SE":
                output.append("SE")
            else:
                output.append(segment_text(target))
        elif issubclass(target, X12Group) or issubclass(target, X12Loop):
            _walk(target, output, transaction)


def minimal_interchange(transaction: type[X12TransactionSet]) -> bytes:
    body: list[str] = []
    _walk(transaction, body, transaction)
    body = [segment for segment in body if segment != "SE"]
    body.append(f"SE*{len(body) + 1}*0001")
    is_4010 = transaction.x12_release == "004010"
    version = transaction.x12_implementation_version or "005010X231A1"
    isa = "*".join(
        (
            "ISA",
            "00",
            " " * 10,
            "00",
            " " * 10,
            "ZZ",
            "SENDER".ljust(15),
            "ZZ",
            "RECEIVER".ljust(15),
            "240101",
            "1200",
            "U" if is_4010 else "^",
            "00401" if is_4010 else "00501",
            "000000001",
            "0",
            "P",
            ":",
        )
    )
    segments = [
        isa,
        f"GS*HC*SENDER*RECEIVER*20240101*1200*1*X*{version}",
        *body,
        "GE*1*1",
        "IEA*1*000000001",
    ]
    return ("~".join(segments) + "~").encode("ascii")
