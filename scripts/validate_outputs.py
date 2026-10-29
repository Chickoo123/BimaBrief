"""Validate generated JSON artifacts before they are copied to a publishable folder."""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path
from pydantic import ValidationError
from data_schema import AppData, InsurerData, ClaimJourneyData


def _walk_finite(value, path="$", errors=None):
    errors = errors if errors is not None else []
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(f"{path}: non-finite number {value}")
    elif isinstance(value, dict):
        for k, v in value.items():
            _walk_finite(v, f"{path}.{k}", errors)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _walk_finite(v, f"{path}[{i}]", errors)
    return errors


def validate_files(app_path: Path, insurers_path: Path, claims_path: Path) -> dict:
    paths = [("app data", app_path, AppData), ("insurer data", insurers_path, InsurerData),
             ("claim journey data", claims_path, ClaimJourneyData)]
    parsed = {}
    errors = []
    for label, path, model in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{label}: cannot parse JSON: {exc}")
            continue
        for e in _walk_finite(raw):
            errors.append(f"{label}: {e}")
        try:
            parsed[label] = model.model_validate(raw)
            print(f"[PASS] {label} schema: {path}")
        except ValidationError as exc:
            errors.append(f"{label}: schema validation failed: {exc}")

    # Cross-artifact invariants guard against valid schemas wired to the wrong files.
    app = parsed.get("app data")
    ins = parsed.get("insurer data")
    claims = parsed.get("claim journey data")
    if app:
        if "All India" not in app.states:
            errors.append("app data: missing 'All India' state row")
        if not app.meta.get("latest_year"):
            errors.append("app data: missing latest_year source metadata")
        if not app.states:
            errors.append("app data: states object is empty")
        if not app.cashless:
            errors.append("app data: cashless object is empty")
    if ins:
        ids = [x.id for x in ins.insurers]
        if len(ids) != len(set(ids)):
            errors.append("insurer data: duplicate insurer IDs")
        if not ins.metrics or not ins.insurers:
            errors.append("insurer data: metrics or insurer list is empty")
        if any(x.claims_status_scope not in {"health_only", "all_lines"} for x in ins.insurers):
            errors.append("insurer data: claims_status_scope must be health_only or all_lines")
    if claims:
        years = claims.meta.years
        if len(years) != len(set(years)) or set(years) != set(claims.years):
            errors.append("claim journey: metadata years do not match generated year keys")
        if claims.meta.latest_year not in claims.years:
            errors.append("claim journey: latest_year missing from years list")
        for year, ydata in claims.years.items():
            if ydata.year != year:
                errors.append(f"claim journey: year label mismatch for {year}")
            missing_routes = {"all", "tpa", "direct"} - set(ydata.routes)
            if missing_routes:
                errors.append(f"claim journey {year}: missing routes {sorted(missing_routes)}")
            for route_name, route in ydata.routes.items():
                for kind in ("paid", "repudiated", "outstanding"):
                    buckets = route.aging.get(kind)
                    if buckets is not None and not buckets:
                        errors.append(f"claim journey {year}/{route_name}: empty {kind} aging buckets")
    if errors:
        print("[FAIL] Output validation:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("[PASS] Cross-artifact invariants")
    return {"status": "PASSED", "artifacts": [str(p) for _, p, _ in paths]}


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python scripts/validate_outputs.py app_data.json insurers.json claim_journey.json")
    validate_files(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
