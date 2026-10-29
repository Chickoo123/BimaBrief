"""End-to-end test on the real IRDAI Excel files (skipped if they are not in the repo)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HB = ROOT / "data/raw/handbook"
pytestmark = pytest.mark.skipif(not (HB / "Part III.xlsx").exists(), reason="IRDAI Excel files not present")


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)


def test_full_pipeline_on_real_data(tmp_path):
    csv = tmp_path / "t67.csv"
    assert run("scripts/extract_table67.py", str(HB / "Part III.xlsx"), str(csv)).returncode == 0
    r = run("scripts/process_state_health.py", str(csv))
    assert r.returncode == 0, r.stdout
    out = tmp_path / "app.json"
    r = run("scripts/build_app_data.py", str(HB), "data/processed/state_health.json", str(out))
    assert r.returncode == 0, r.stdout
    d = json.loads(out.read_text())
    ai = d["states"]["All India"]["2024-25"]["individual"]
    # Values checked by hand against the official Excel (see TESTING.md)
    assert ai["policies"] == 25184542
    assert round(ai["gross_premium_lakh"]) == 4661139
    assert round(ai["claims_paid_lakh"]) == 3238032
    assert d["states"]["Maharashtra"]["2024-25"]["individual"]["policies"] == 5651274
    # Cross-table: Table 72 All India individual claims == Table 67
    assert d["cashless"]["All India"]["2024-25"]["individual"]["parts_total"] == ai["claims_paid_count"]
    # Insurer table: Star Health 2024-25 values from Table 53 / 56
    star = [v for v in d["insurers"] if v["name"].startswith("Star Health")][0]
    assert star["repudiated"] == 317661 and star["complaints_new"] == 20527 - 331
