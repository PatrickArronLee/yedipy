from yedipy.x12 import parse_x12
from yedipy.x12.transactions.v5010 import parse_270


def _isa() -> bytes:
    elements = (
        "00",
        "          ",
        "00",
        "          ",
        "ZZ",
        "SENDERID".ljust(15),
        "ZZ",
        "RECEIVERID".ljust(15),
        "240101",
        "1200",
        "^",
        "00501",
        "000000001",
        "0",
        "P",
        ":",
    )
    return f"ISA*{'*'.join(elements)}~".encode("ascii")


def _source() -> bytes:
    return b"".join(
        (
            _isa(),
            b"GS*HS*SENDER*RECEIVER*20240101*1200*1*X*005010X279A1~",
            b"ST*270*0001*005010X279A1~",
            b"BHT*0022*13*TRACE001*20240101*1200~",
            b"HL*1**20*1~",
            b"NM1*PR*2*PAYER*****PI*12345~",
            b"HL*2*1*21*1~",
            b"NM1*1P*2*CLINIC*****XX*1234567893~",
            b"HL*3*2*22*0~",
            b"NM1*IL*1*DOE*JANE****MI*MEMBER01~",
            b"EQ*30^88~",
            b"SE*10*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )


def test_parses_subscriber_270_into_typed_hierarchy() -> None:
    parsed = parse_x12(_source())

    assert parsed.errors == ()
    assert parsed.interchange is not None
    result = parse_270(parsed.interchange.transactions[0], parsed.interchange.delimiters)

    assert result.errors == ()
    assert result.transaction is not None
    subscriber = result.transaction.information_sources[0].receivers[0].subscribers[0]
    assert subscriber.name.name == "DOE"
    assert subscriber.name.first_name == "JANE"
    assert subscriber.inquiries[0].service_type_codes == ("30", "88")


def test_rejects_invalid_hl_parent_without_exposing_values() -> None:
    source = _source().replace(b"HL*3*2*22*0", b"HL*3*1*22*0")
    parsed = parse_x12(source)

    assert parsed.errors == ()
    assert parsed.interchange is not None
    result = parse_270(parsed.interchange.transactions[0], parsed.interchange.delimiters)

    assert result.transaction is None
    assert [diagnostic.code for diagnostic in result.errors] == ["x12.270.hl.parent_level_invalid"]
    assert all("MEMBER01" not in diagnostic.message for diagnostic in result.errors)