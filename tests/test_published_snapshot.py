"""Tests for the reviewed public snapshot shipped with the repository."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "published"

def test_published_snapshot_is_source_linked_and_currently_labelled():
    app = json.loads((DATA / "app_data.json").read_text(encoding="utf-8"))
    assert app["meta"]["source_url"] == "https://irdai.gov.in/handbook-of-indian-insurance"
    assert app["meta"]["latest_year"] == "2024-25"
    assert "All India" in app["states"]

def test_public_snapshot_preserves_manual_spot_checks():
    app = json.loads((DATA / "app_data.json").read_text(encoding="utf-8"))
    ai = app["states"]["All India"]["2024-25"]["individual"]
    assert ai["policies"] == 25184542
    assert round(ai["gross_premium_lakh"]) == 4661139
    assert round(ai["claims_paid_lakh"]) == 3238032
    assert app["states"]["Maharashtra"]["2024-25"]["individual"]["policies"] == 5651274

def test_public_snapshot_manifest_explains_source_year_and_validation():
    manifest = json.loads((DATA / "build-manifest.json").read_text(encoding="utf-8"))
    assert manifest["latest_reporting_year"] == "2024-25"
    assert manifest["schema_validation"] == "PASSED"
    report = json.loads((DATA / "validation_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASSED"
