import json

from yedipy.cli import main


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
            b"EQ*30~",
            b"SE*10*0001~",
            b"GE*1*1~",
            b"IEA*1*000000001~",
        )
    )


def test_validate_270_returns_safe_json(tmp_path, capsys) -> None:
    input_path = tmp_path / "request.edi"
    input_path.write_bytes(_source())

    exit_code = main(("x12", "validate", str(input_path), "--transaction", "270"))

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output == {"diagnostics": [], "valid": True}


def test_inspect_does_not_emit_segment_values(tmp_path, capsys) -> None:
    input_path = tmp_path / "request.edi"
    input_path.write_bytes(_source())

    exit_code = main(("x12", "inspect", str(input_path)))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "MEMBER01" not in output
    assert json.loads(output)["transactions"][0]["identifier"] == "270"