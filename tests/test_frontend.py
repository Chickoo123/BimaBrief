"""Frontend syntax and smoke tests for the self-contained GitHub Pages site."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = Path(os.environ.get("BIMABRIEF_SITE_DIR", str(ROOT / "docs"))).resolve()
DATA_DIR = SITE_DIR / "data"
SITE_INDEX = SITE_DIR / "index.html"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("js", sorted((ROOT / "site/js").glob("*.js")), ids=lambda p: p.name)
def test_js_syntax(js):
    r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_insurer_network_not_double_counted():
    d = json.loads((DATA_DIR / "insurers.json").read_text())
    p = {x["id"]: x for x in d["insurers"]}
    assert "Total" not in p["star"]["network"]
    assert p["star"]["network"]["Gujarat"]["direct"] == 1107
    assert p["star"]["network_total"]["direct"] == 22374
    assert p["icici-lombard"]["network_total"] == {"direct": 26936, "tpa": 54461}
    assert p["star"]["network_reported"] is True


def test_comparability_rules_in_data():
    d = json.loads((DATA_DIR / "insurers.json").read_text())
    p = {x["id"]: x for x in d["insurers"]}
    assert p["icici-lombard"]["claims_status_scope"] == "all_lines"
    assert p["star"]["claims_status_scope"] == "health_only"
    assert all(c.get("per_10k_health_policies") is None for c in p["icici-lombard"]["complaints"].values())
    assert "pending_pct" in d["metrics"]
    assert "year-end" in d["metrics"]["pending_pct"]["label"].lower()


def test_claim_journey_data_covers_all_reported_years():
    d = json.loads((DATA_DIR / "claim_journey.json").read_text())
    assert d["meta"]["source_table"] == "Table 66"
    assert d["meta"]["years"][0] == "2015-16"
    assert d["meta"]["latest_year"] == "2024-25"
    assert len(d["years"]) == 10
    latest = d["years"]["2024-25"]
    for route in ("all", "tpa", "direct"):
        assert route in latest["routes"]
        for key in ("opening", "new_registered", "paid", "repudiated", "closing"):
            assert key in latest["routes"][route]["flows"]
    assert "paid" in latest["routes"]["all"]["aging"]
    assert "repudiated" in latest["routes"]["all"]["aging"]
    assert "outstanding" in latest["routes"]["all"]["aging"]
    assert "first intimation" in d["meta"]["aging_notes"]["paid"].lower()


def test_site_has_new_feature_and_audit_labels():
    html = SITE_INDEX.read_text()
    assert "fonts.googleapis.com" not in html, "Site should remain self-contained and must not block on remote fonts"
    assert "fonts.gstatic.com" not in html, "Site should not depend on remote font resources"
    for token in ('id="journey"', 'id="claim-data"', 'id="claim-category"',
                  'id="ratio-axis"', 'id="h-place"', 'id="compare"',
                  'id="decoder"', 'id="share-snapshot"', 'BimaBrief'):
        assert token in html
    assert "Year-end outstanding share of claims workload" in html
    assert "Network providers listed by IRDAI" in html
    assert "All-product complaints per 10,000 health policies" in html
    assert "A number can be true" in html
    assert "Copy shareable view" in html
    assert 'id="irdai-updates"' in html
    assert "Health Insurance Master Circular" in html or "29 MAY 2024" in html
    assert "not auto-synced" in html.lower()
    assert "bimabharosa.irdai.gov.in" in html
    assert "Provider API usage is billed separately" in html
    assert "Why I built BimaBrief" in html
    assert "Harshil Desai" in html
    assert "og:site_name" in html
    assert "application/ld+json" in html
    assert "correction-link" in html


playwright = pytest.importorskip("playwright.sync_api")


def test_site_smoke():
    with playwright.sync_playwright() as pw:
        # Use system Chromium when available and disable sandbox for container/CI execution.
        # set_content avoids this environment's policy blocking local file and loopback navigation.
        chromium_path = "/usr/bin/chromium" if Path("/usr/bin/chromium").exists() else None
        launch = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if chromium_path:
            launch["executable_path"] = chromium_path
        try:
            b = pw.chromium.launch(**launch)
        except Exception as exc:
            if os.environ.get("CI") == "true" or os.environ.get("BIMABRIEF_SITE_DIR"):
                raise
            pytest.skip(f"Playwright is installed but its browser binary is unavailable locally: {exc}")
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        # Bound locator waits so a broken UI fails quickly instead of hanging CI for minutes.
        pg.set_default_timeout(7000)
        pg.set_default_navigation_timeout(30000)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        try:
            pg.set_content(SITE_INDEX.read_text(), wait_until="domcontentloaded", timeout=30000)
            pg.wait_for_timeout(250)
            assert errors == []
            assert pg.locator("h1").inner_text().strip()
            assert pg.title().startswith("BimaBrief")
            assert pg.locator("#decoder .decoder-card").count() == 4
            assert pg.locator("#irdai-updates .rule-card").count() == 5
            assert pg.locator("#irdai-updates a[href^=\"https://irdai.gov.in\"]").count() >= 6
            pg.locator("#decoder .decoder-card summary").first.click()
            assert pg.locator("#decoder .decoder-card").first.get_attribute("open") is not None
            pg.select_option("#place", "Gujarat")
            assert "Gujarat" in pg.inner_text("#h-place")
            assert "₹90.9" in pg.inner_text("#big")
            pg.select_option("#ins-a", "icici-lombard")
            pg.select_option("#ins-b", "star")
            verdicts = pg.locator("#ins-rows .verdict").all_inner_texts()
            assert sum(v.startswith("NOT COMPARABLE") for v in verdicts) >= 3
            pg.select_option("#ins-a", "star")
            pg.select_option("#ins-b", "care")
            assert all(not v.startswith("NOT COMPARABLE") for v in pg.locator("#ins-rows .verdict").all_inner_texts())
            assert pg.locator("#claim-flow .flow-card").count() >= 5
            assert pg.locator("#claim-aging .aging-row").count() == 6
            pg.select_option("#claim-route", "tpa")
            pg.select_option("#claim-category", "cashless")
            assert pg.locator("#claim-flow .flow-card").count() >= 5
            pg.select_option("#claim-unit", "amount_lakh")
            assert "cr" in pg.locator("#claim-flow .flow-value").first.inner_text().lower()
            pg.locator('[data-aging="outstanding"]').click()
            assert "last requirement" in pg.inner_text("#claim-aging-note").lower()

            # Responsive smoke: phone layout should not require sideways scrolling.
            pg.set_viewport_size({"width": 390, "height": 844})
            pg.wait_for_timeout(100)
            widths = pg.evaluate("({viewport: window.innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth})")
            assert widths["document"] <= widths["viewport"] + 1, f"Horizontal overflow on mobile: {widths}"
            assert pg.locator(".main-nav a").count() == 6
            card_box = pg.locator(".hero-data-card").bounding_box()
            for selector in ("#place", "#year"):
                box = pg.locator(selector).bounding_box()
                assert box["x"] + box["width"] <= card_box["x"] + card_box["width"] + 1, f"{selector} extends beyond card: {box}, {card_box}"
            assert pg.locator("#ins-heads .ins-head").count() == 2
            assert pg.locator("#claim-flow .flow-card").count() >= 5
            assert errors == []
        finally:
            b.close()
