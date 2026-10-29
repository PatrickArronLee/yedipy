from yedipy.x12 import parse_x12


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


def test_lexes_270_and_preserves_source_bytes() -> None:
    source = b"".join(
        (
            _isa(),
            b"\r\nGS*HS*SENDER*RECEIVER*20240101*1200*1*X*005010X279A1~",
            b"ST*270*0001*005010X279A1~",
            b"BHT*0022*13*10001234*20240101*1200~",
            b"HL*1**20*1~",
            b"NM1*PR*2*PAYER*****PI*12345~",
            b"HL*2*1*21*1~",
            b"NM1*1P*2*CLINIC*****XX*1234567893~",
            b"HL*3*2*22*0~",
            b"NM1*IL*1*DOE*JANE****MI*MEMBER01~",
            b"EQ*30~",
            b"SE*10*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )

    result = parse_x12(source)

    assert result.errors == ()
    assert result.interchange is not None
    assert result.interchange.to_source() == source
    assert result.interchange.delimiters.element == "*"
    assert result.interchange.delimiters.repetition == "^"
    assert result.interchange.delimiters.component == ":"
    assert result.interchange.delimiters.segment == "~"
    assert len(result.interchange.transactions) == 1
    assert result.interchange.transactions[0].identifier == "270"
    assert result.interchange.transactions[0].control_number == "0001"
    assert result.interchange.transactions[0].complete is True
    assert [segment.identifier for segment in result.interchange.segments] == [
        "ISA",
        "GS",
        "ST",
        "BHT",
        "HL",
        "NM1",
        "HL",
        "NM1",
        "HL",
        "NM1",
        "EQ",
        "SE",
        "GE",
        "IEA",
    ]


def test_truncated_isa_is_redacted() -> None:
    source = b"ISA*00*member-secret"

    result = parse_x12(source)

    assert result.interchange is None
    assert [diagnostic.code for diagnostic in result.errors] == ["x12.isa.truncated"]
    assert "member-secret" not in result.errors[0].message


def test_reports_invalid_transaction_trailer_without_exposing_values() -> None:
    source = b"".join(
        (
            _isa(),
            b"GS*HS*SENDER*RECEIVER*20240101*1200*1*X*005010X279A1~",
            b"ST*270*0001*005010X279A1~",
            b"BHT*0022*13*10001234*20240101*1200~",
            b"SE*9*wrong-control~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )

    result = parse_x12(source)

    assert [diagnostic.code for diagnostic in result.errors] == [
        "x12.se.count_mismatch",
        "x12.se.control_number_mismatch",
    ]
    assert all("wrong-control" not in diagnostic.message for diagnostic in result.errors)


def test_slices_multiple_transactions_in_source_order() -> None:
    source = b"".join(
        (
            _isa(),
            b"GS*HS*SENDER*RECEIVER*20240101*1200*1*X*005010X279A1~",
            b"ST*270*0001*005010X279A1~",
            b"BHT*0022*13*FIRST*20240101*1200~",
            b"SE*3*0001~",
            b"ST*270*0002*005010X279A1~",
            b"BHT*0022*13*SECOND*20240101*1200~",
            b"SE*3*0002~",
            b"GE*2*1~",
            b"IEA*1*000000001~",
        )
    )

    result = parse_x12(source)

    assert result.errors == ()
    assert result.interchange is not None
    assert [transaction.control_number for transaction in result.interchange.transactions] == [
        "0001",
        "0002",
    ]
    assert all(transaction.complete for transaction in result.interchange.transactions)