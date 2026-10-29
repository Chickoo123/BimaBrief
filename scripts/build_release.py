"""Build a deployable site from reviewed, versioned JSON snapshots.

Public CI does not redistribute or require copies of the official IRDAI Excel
workbooks. A maintainer imports a new edition locally, validates it, reviews
all discrepancies, then promotes the generated JSON snapshots under
 data/published/ for the next release.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "data" / "published"
FILES = ("app_data.json", "insurers.json", "claim_journey.json", "validation_report.json")


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _replace_directory(candidate: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".previous-build")
    if backup.exists():
        shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
    existed = destination.exists()
    try:
        if existed:
            os.replace(destination, backup)
        os.replace(candidate, destination)
    except Exception:
        if destination.exists():
            shutil.rmtree(destination) if destination.is_dir() else destination.unlink()
        if existed and backup.exists():
            os.replace(backup, destination)
        raise
    if backup.exists():
        shutil.rmtree(backup) if backup.is_dir() else backup.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "site")
    parser.add_argument("--repo-url", default=os.environ.get("REPO_URL", ""))
    parser.add_argument("--policy-api-base", default=os.environ.get("BIMABRIEF_POLICY_API_BASE", ""))
    args = parser.parse_args()

    missing = [name for name in FILES if not (PUBLISHED / name).is_file()]
    if missing:
        print("Build stopped; reviewed snapshots missing: " + ", ".join(missing), file=sys.stderr)
        return 2

    from validate_outputs import validate_files
    report = validate_files(PUBLISHED / FILES[0], PUBLISHED / FILES[1], PUBLISHED / FILES[2])
    validation_report = _load_json(PUBLISHED / "validation_report.json")
    if validation_report.get("status") != "PASSED":
        print("Build stopped; published state-data validation report is not PASSED.", file=sys.stderr)
        return 2

    app = _load_json(PUBLISHED / "app_data.json")
    meta = app.get("meta", {})
    if not meta.get("latest_year") or not meta.get("source_url"):
        print("Build stopped; snapshot is missing reporting-year or source URL metadata.", file=sys.stderr)
        return 2

    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output = output.resolve()
    if output in (ROOT, ROOT / "data", ROOT / "data" / "published", ROOT / "data" / "raw"):
        print(f"Refusing unsafe output directory: {output}", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="bimabrief-release-", dir=output.parent))
    try:
        candidate = work / "site"
        candidate.mkdir()
        data_dir = candidate / "data"
        data_dir.mkdir()
        for name in FILES:
            shutil.copy2(PUBLISHED / name, data_dir / name)
        if (PUBLISHED / "build-manifest.json").is_file():
            source_manifest = _load_json(PUBLISHED / "build-manifest.json")
        else:
            source_manifest = {}
        manifest = {
            "project": "BimaBrief",
            "latest_reporting_year": meta["latest_year"],
            "snapshot_built_on": meta.get("built_on"),
            "deployed_on_utc": datetime.now(timezone.utc).date().isoformat(),
            "source": "IRDAI Handbook on Indian Insurance Statistics",
            "source_url": meta["source_url"],
            "schema_validation": "PASSED",
            "state_data_checks": validation_report.get("status", "UNKNOWN"),
            "snapshot_mode": True,
            "raw_source_workbooks_in_repository": False,
            "published_validation_report": "validation_report.json",
            "source_snapshot_manifest": source_manifest,
            "files": list(FILES),
        }
        (data_dir / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        index_out = candidate / "index.html"
        cmd = [sys.executable, "scripts/build_site.py", "--data-dir", str(PUBLISHED),
               "--output", str(index_out), "--repo-url", args.repo_url,
               "--policy-api-base", args.policy_api_base]
        print("$ " + " ".join(cmd), flush=True)
        subprocess.run(cmd, cwd=ROOT, check=True)
        html = index_out.read_text(encoding="utf-8")
        required = ("BimaBrief", 'id="app-data"', 'id="insurer-data"', 'id="claim-data"',
                    'id="decoder"', 'id="policy-fit"', 'id="irdai-updates"',
                    "not affiliated with, endorsed by, or acting on behalf of IRDAI")
        absent = [item for item in required if item not in html]
        if absent:
            raise RuntimeError(f"Generated page failed required content checks: {absent}")
        destination = output
        _replace_directory(candidate, destination)
        print(f"[PUBLISHED] {destination}; snapshot source year={meta['latest_year']}; schema checks passed; source warnings remain preserved.")
        return 0
    except (subprocess.CalledProcessError, Exception) as exc:
        print(f"[BUILD FAILED] {type(exc).__name__}: {exc}. Previous output was not replaced.", file=sys.stderr)
        return getattr(exc, "returncode", 1) or 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
