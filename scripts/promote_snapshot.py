"""Promote locally rebuilt docs/data JSON to reviewed, versioned snapshots.

Run only after a full source-workbook rebuild and manual review of warnings:
    python scripts/promote_snapshot.py --from-dir docs/data
Raw workbooks are intentionally not copied into the public repository.
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path
from validate_outputs import validate_files

ROOT = Path(__file__).resolve().parents[1]
FILES = ("app_data.json", "insurers.json", "claim_journey.json", "validation_report.json")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--from-dir", type=Path, default=ROOT / "docs" / "data")
    p.add_argument("--to-dir", type=Path, default=ROOT / "data" / "published")
    args = p.parse_args()
    source = args.from_dir if args.from_dir.is_absolute() else ROOT / args.from_dir
    destination = args.to_dir if args.to_dir.is_absolute() else ROOT / args.to_dir
    absent = [name for name in FILES if not (source / name).is_file()]
    if absent:
        print("Snapshot promotion stopped; missing files: " + ", ".join(absent), file=sys.stderr)
        return 2
    validation = validate_files(source / FILES[0], source / FILES[1], source / FILES[2])
    report = json.loads((source / "validation_report.json").read_text(encoding="utf-8"))
    if report.get("status") != "PASSED":
        print("Snapshot promotion stopped; source validation report is not PASSED. Review the report first.", file=sys.stderr)
        return 2
    destination.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copy2(source / name, destination / name)
    source_manifest_path = source / "build-manifest.json"
    if source_manifest_path.is_file():
        shutil.copy2(source_manifest_path, destination / "build-manifest.json")
    else:
        app = json.loads((destination / "app_data.json").read_text(encoding="utf-8"))
        (destination / "build-manifest.json").write_text(json.dumps({
            "project": "BimaBrief", "latest_reporting_year": app["meta"].get("latest_year"),
            "built_on": app["meta"].get("built_on"), "source": "IRDAI Handbook on Indian Insurance Statistics",
            "schema_validation": validation.get("status", "UNKNOWN"),
            "state_data_checks": report.get("status", "UNKNOWN"),
            "files": list(FILES)
        }, indent=2), encoding="utf-8")
    print(f"[PROMOTED] Reviewed snapshots copied to {destination}.")
    print("Next: inspect the diff, confirm source warnings, then commit only the reviewed snapshots and code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
