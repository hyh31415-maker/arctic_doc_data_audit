from __future__ import annotations

from arctic_doc_data_audit.normalize import convert_doc_to_mgC_L


def test_doc_unit_conversion_mg_l_as_c() -> None:
    value, reason = convert_doc_to_mgC_L(2.5, "mg/L as C")
    assert value == 2.5
    assert reason == ""


def test_doc_unit_conversion_ug_l() -> None:
    value, reason = convert_doc_to_mgC_L(2500, "ug/L")
    assert value == 2.5
    assert reason == ""


def test_invalid_unit_flagged() -> None:
    value, reason = convert_doc_to_mgC_L(2.5, "mmol/L")
    assert value is None
    assert "invalid_or_unsupported_unit" in reason

