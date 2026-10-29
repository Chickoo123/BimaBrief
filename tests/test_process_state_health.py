import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from process_state_health import run  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "raw" / "sample_state_health.csv"


def test_real_sample_passes(tmp_path):
    rep = run(str(SAMPLE), str(tmp_path))
    assert rep["status"] == "PASSED"
    data = json.loads((tmp_path / "state_health.json").read_text())
    pmjay = [r for r in data if "PMJAY" in r["category"]][0]
    # Values copied from the Dataful preview must survive unchanged
    assert pmjay["claims_paid_count"] == 14
    assert pmjay["claims_paid_lakh"] == 3.53
    assert pmjay["group"] == "government_scheme"
    # Premium is 0, so the ratio must be "not available", not 0 or infinity
    assert pmjay["claims_to_premium_pct"] is None


def test_ratio_is_correct(tmp_path):
    df = pd.DataFrame([
        ["2024-25", "Maharashtra", "Individual Business", "Gross Premium", 200, "value in rupees lakh"],
        ["2024-25", "Maharashtra", "Individual Business", "Total Amount of Claims Paid", 150, "value in rupees lakh"],
    ], columns=["fiscal_year", "state_name", "category", "sub_category", "value", "unit"])
    p = tmp_path / "t.csv"; df.to_csv(p, index=False)
    rep = run(str(p), str(tmp_path / "out"))
    data = json.loads((tmp_path / "out" / "state_health.json").read_text())
    assert rep["status"] == "PASSED"
    assert data[0]["claims_to_premium_pct"] == 75.0


def _bad(tmp_path, rows):
    df = pd.DataFrame(rows, columns=["fiscal_year", "state_name", "category", "sub_category", "value", "unit"])
    p = tmp_path / "bad.csv"; df.to_csv(p, index=False)
    out = tmp_path / "out"
    rep = run(str(p), str(out))
    return rep, out


def test_duplicates_block_publish(tmp_path):
    row = ["2024-25", "Goa", "Group Business", "Gross Premium", 10, "value in rupees lakh"]
    rep, out = _bad(tmp_path, [row, row])
    assert rep["status"] == "FAILED"
    assert not (out / "state_health.json").exists()  # safety lock: nothing published


def test_negative_values_kept_but_no_ratio(tmp_path):
    # Real IRDAI data has negative premium adjustments: keep them as published, never compute a ratio
    rows = [["2024-25", "Goa", "Government Scheme - RSBY", "Gross Premium", -5, "value in rupees lakh"],
            ["2024-25", "Goa", "Government Scheme - RSBY", "Total Amount of Claims Paid", 3, "value in rupees lakh"]]
    rep, out = _bad(tmp_path, rows)
    assert rep["status"] == "PASSED"
    data = json.loads((out / "state_health.json").read_text())
    assert data[0]["gross_premium_lakh"] == -5
    assert data[0]["claims_to_premium_pct"] is None
    chk = [c for c in rep["checks"] if c["check"] == "negative_values_flagged"][0]
    assert "1 negative" in chk["detail"]


def test_wrong_unit_blocks_publish(tmp_path):
    rep, out = _bad(tmp_path, [["2024-25", "Goa", "Group Business", "Gross Premium", 5, "value in rupees crore"]])
    assert rep["status"] == "FAILED"


def test_missing_column_blocks_publish(tmp_path):
    p = tmp_path / "m.csv"
    pd.DataFrame({"fiscal_year": ["2024-25"], "value": [1]}).to_csv(p, index=False)
    rep = run(str(p), str(tmp_path / "out"))
    assert rep["status"] == "FAILED"


def test_blank_stays_missing_not_zero(tmp_path):
    df = pd.DataFrame([
        ["2024-25", "Goa", "Group Business", "Gross Premium", None, "value in rupees lakh"],
        ["2024-25", "Goa", "Group Business", "Total Amount of Claims Paid", 4, "value in rupees lakh"],
    ], columns=["fiscal_year", "state_name", "category", "sub_category", "value", "unit"])
    p = tmp_path / "b.csv"; df.to_csv(p, index=False)
    rep = run(str(p), str(tmp_path / "out"))
    data = json.loads((tmp_path / "out" / "state_health.json").read_text())
    assert rep["status"] == "PASSED"
    assert data[0]["gross_premium_lakh"] is None       # missing, not 0
    assert data[0]["claims_to_premium_pct"] is None    # no ratio from missing data


def test_text_value_blocks_publish(tmp_path):
    rep, out = _bad(tmp_path, [["2024-25", "Goa", "Group Business", "Gross Premium", "abc", "value in rupees lakh"]])
    assert rep["status"] == "FAILED"


def test_national_total_mismatch_is_flagged(tmp_path):
    rows = [
        ["2024-25", "Goa", "Group Business", "Gross Premium", 10, "value in rupees lakh"],
        ["2024-25", "Kerala", "Group Business", "Gross Premium", 20, "value in rupees lakh"],
        ["2024-25", "All India", "Group Business", "Gross Premium", 50, "value in rupees lakh"],
    ]
    rep, out = _bad(tmp_path, rows)
    chk = [c for c in rep["checks"] if c["check"] == "states_match_national_total"][0]
    assert chk["passed"] is False
    data = json.loads((out / "state_health.json").read_text())
    assert all(r["state_name"] != "All India" for r in data)  # national row never shown as a state


def test_national_total_match_passes(tmp_path):
    rows = [
        ["2024-25", "Goa", "Group Business", "Gross Premium", 10, "value in rupees lakh"],
        ["2024-25", "Kerala", "Group Business", "Gross Premium", 20, "value in rupees lakh"],
        ["2024-25", "All India", "Group Business", "Gross Premium", 30, "value in rupees lakh"],
    ]
    rep, out = _bad(tmp_path, rows)
    chk = [c for c in rep["checks"] if c["check"] == "states_match_national_total"][0]
    assert chk["passed"] is True


def test_employer_group_not_classified_as_government():
    from process_state_health import classify
    assert classify("Group Business (Employer & Other)") == "group"
    assert classify("Government Scheme - AB-PMJAY") == "government_scheme"
    assert classify("Individual Business") == "individual"
    assert classify("Grand Total") == "total_row"
