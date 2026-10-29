"""Structural and invariant tests for generated JSON schemas."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = Path(os.environ.get("BIMABRIEF_SITE_DIR", str(ROOT / "docs"))).resolve()


def test_pydantic_output_validation_passes_for_built_artifacts():
    paths = [SITE_DIR / "data" / name for name in ("app_data.json", "insurers.json", "claim_journey.json")]
    if not all(p.is_file() for p in paths):
        pytest.skip("Build the site before testing generated output schemas")
    run = subprocess.run([sys.executable, "scripts/validate_outputs.py", *map(str, paths)], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "[PASS] Cross-artifact invariants" in run.stdout


def test_generated_html_has_no_build_placeholders():
    site = SITE_DIR / "index.html"
    if not site.exists():
        pytest.skip("Build the site before checking rendered HTML")
    html = site.read_text(encoding="utf-8")
    for token in ("/*__CSS__*/", "/*__JS__*/", "/*__DATA__*/", "/*__INSURERS__*/", "/*__CLAIMS__*/"):
        assert token not in html
    assert "BimaBrief" in html
    assert 'id="decoder"' in html


def test_insurer_ids_are_unique_and_scopes_are_explicit():
    p = SITE_DIR / "data" / "insurers.json"
    if not p.exists():
        pytest.skip("Build the site before checking insurer profiles")
    data = json.loads(p.read_text(encoding="utf-8"))
    ids = [x["id"] for x in data["insurers"]]
    assert len(ids) == len(set(ids))
    assert all(x["claims_status_scope"] in {"health_only", "all_lines"} for x in data["insurers"])
