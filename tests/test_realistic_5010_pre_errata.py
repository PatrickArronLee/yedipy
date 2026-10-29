from pathlib import Path

import pytest

from yedipy.x12 import parse_x12
from yedipy.x12.transactions import parse_transaction

FIXTURES = Path(__file__).parent / "fixtures" / "5010_pre_errata"
CASES = {
    "270": ("270.edi", "TS270"), "271": ("271.edi", "TS271"), "834": ("834.edi", "TS834"),
    "835": ("835.edi", "TS835"), "837d": ("837d.edi", "TS837D"),
    "837i": ("837i.edi", "TS837I"), "837p": ("837p.edi", "TS837P"),
}

def _parse(name: str):
    parsed = parse_x12((FIXTURES / CASES[name][0]).read_bytes())
    assert parsed.errors == ()
    assert parsed.interchange is not None
    raw = parsed.interchange.transactions[0]
    result = parse_transaction(raw, parsed.interchange.delimiters, release="005010-pre-errata")
    assert result.errors == ()
    assert result.unmatched_segments == ()
    assert result.transaction is not None
    return result.transaction

@pytest.mark.parametrize("name", CASES, ids=CASES.keys())
def test_realistic_pre_errata_transaction(name: str) -> None:
    transaction = _parse(name)
    assert type(transaction).__name__ == CASES[name][1]

def test_270_typed_request_values() -> None:
    t = _parse("270")
    assert t.bht_beginning_of_hierarchical_transaction.submitter_transaction_identifier == "REQ27001"
    assert t.loop_2000a[0].hl_information_source_level.hierarchical_id_number == "1"

def test_271_has_multiple_typed_benefits() -> None:
    t = _parse("271")
    benefits = t.loop_2000a[0].loop_2000b[0].loop_2000c[0].loop_2100c.loop_2110c
    assert len(benefits) == 3
    assert benefits[0].eb_subscriber_eligibility_or_benefit_information.eligibility_or_benefit_information == "1"

def test_834_member_values() -> None:
    t = _parse("834")
    assert t.bgn_beginning_segment.transaction_set_reference_number == "ENR83401"
    assert t.loop_2000[0].ins_member_level_detail.insured_indicator == "Y"

def test_835_payment_and_two_services() -> None:
    t = _parse("835")
    assert t.bpr_financial_information.total_premium_payment_amount == 1250.0
    assert len(t.loop_2000[0].loop_2100) == 1
    assert len(t.loop_2000[0].loop_2100[0].loop_2110) == 2

def test_837d_claim_and_dental_lines() -> None:
    t = _parse("837d")
    claim = t.loop_2000a[0].loop_2000b[0].loop_2300[0]
    assert claim.clm_claim_information.patient_control_number == "DCLAIM01"
    assert len(claim.loop_2400) == 2
    assert claim.loop_2400[0].too_tooth_information[0].tooth_code == "8"

def test_837i_institutional_claim_and_lines() -> None:
    t = _parse("837i")
    claim = t.loop_2000a[0].loop_2000b[0].loop_2300[0]
    assert claim.clm_claim_information.patient_control_number == "ICLAIM01"
    assert claim.cl1_institutional_claim_code is not None
    assert len(claim.loop_2400) == 2

def test_837p_professional_claim_and_lines() -> None:
    t = _parse("837p")
    claim = t.loop_2000a[0].loop_2000b[0].loop_2300[0]
    assert claim.clm_claim_information.patient_control_number == "PCLAIM01"
    assert len(claim.loop_2400) == 2
    assert claim.loop_2400[0].sv1_professional_service.line_item_charge_amount == 150.0

def test_parse_transaction_selects_pre_errata_from_st03() -> None:
    parsed = parse_x12((FIXTURES / "837p.edi").read_bytes())
    assert parsed.interchange is not None
    raw = parsed.interchange.transactions[0]
    result = parse_transaction(raw, parsed.interchange.delimiters)
    assert result.errors == ()
    assert result.transaction is not None
    assert type(result.transaction).__name__ == "TS837P"
    assert result.transaction.x12_release == "005010-pre-errata"
