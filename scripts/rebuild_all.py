"""Cross-platform, transactional build orchestrator for BimaBrief.

Build all outputs in a temporary directory, validate every data schema, render the
page, then publish the whole directory by atomic directory swap. A failed step leaves
the previous output folder untouched. By default the local preview is published to docs/;
CI should pass --output-dir build/site and deploy that artifact via GitHub Pages Actions.
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def step(label: str, args: list[str], env: dict[str, str] | None = None) -> None:
    print(f"\n{'=' * 72}\n{label}\n$ {' '.join(args)}\n{'=' * 72}", flush=True)
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def copy_tree_preserving(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.copytree(destination, source, dirs_exist_ok=True)
    source.mkdir(parents=True, exist_ok=True)


def publish_directory(candidate: Path, destination: Path) -> None:
    """Swap a fully-validated build directory into place with rollback on error."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".previous-build")
    if backup.exists():
        shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
    had_old = destination.exists()
    try:
        if had_old:
            os.replace(destination, backup)
        os.replace(candidate, destination)
    except Exception:
        if destination.exists() and destination != candidate:
            shutil.rmtree(destination) if destination.is_dir() else destination.unlink()
        if had_old and backup.exists():
            os.replace(backup, destination)
        raise
    if backup.exists():
        shutil.rmtree(backup) if backup.is_dir() else backup.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs", help="Publish built index.html + data/ to this directory")
    parser.add_argument("--repo-url", default=os.environ.get("REPO_URL", ""), help="Optional repository URL embedded in the page")
    parser.add_argument("--policy-api-base", default=os.environ.get("BIMABRIEF_POLICY_API_BASE", ""), help="Optional secure Policy Fit API base URL; keep blank until a backend is deployed")
    parser.add_argument("--keep-work", action="store_true", help="Keep the temporary build folder for debugging")
    args = parser.parse_args()

    handbook = ROOT / "data/raw/handbook"
    part2, part3 = handbook / "Part II.xlsx", handbook / "Part III.xlsx"
    missing = [str(p.relative_to(ROOT)) for p in (part2, part3) if not p.is_file()]
    if missing:
        print("Build stopped; official IRDAI workbook(s) missing: " + ", ".join(missing), file=sys.stderr)
        return 2

    work_root = ROOT / "build/tmp"
    work_root.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix="bimabrief-", dir=work_root))
    try:
        stage_data = temp / "data"
        stage_data.mkdir()
        stage_processed = temp / "processed"
        table67_csv = temp / "table67.csv"
        site_index = temp / "index.html"
        step("1/7 Extract Table 67 to a temporary CSV", [sys.executable, "scripts/extract_table67.py", str(part3), str(table67_csv)])
        step("2/7 Validate and transform state-level data", [sys.executable, "scripts/process_state_health.py", str(table67_csv), str(stage_processed)])
        state_json = stage_processed / "state_health.json"
        if not state_json.is_file():
            raise RuntimeError("State-health processing passed without producing state_health.json")
        step("3/7 Build state and cashless dataset", [sys.executable, "scripts/build_app_data.py", str(handbook), str(state_json), str(stage_data / "app_data.json")])
        step("4/7 Build insurer evidence profiles", [sys.executable, "scripts/build_insurers.py", str(handbook), str(stage_data / "insurers.json")])
        step("5/7 Build industry claim-journey dataset", [sys.executable, "scripts/build_claim_journey.py", str(part3), str(stage_data / "claim_journey.json")])
        step("6/7 Validate data models and cross-artifact invariants", [sys.executable, "scripts/validate_outputs.py", str(stage_data / "app_data.json"), str(stage_data / "insurers.json"), str(stage_data / "claim_journey.json")])
        step("7/7 Render a self-contained website", [sys.executable, "scripts/build_site.py", "--data-dir", str(stage_data), "--output", str(site_index), "--repo-url", args.repo_url, "--policy-api-base", args.policy_api_base])

        # Final structural check before any existing publish directory is touched.
        html = site_index.read_text(encoding="utf-8")
        required = ["BimaBrief", 'id="decoder"', 'id="share-snapshot"', 'id="claim-data"', 'id="app-data"', 'id="insurer-data"', 'id="policy-fit"', 'id="policy-fit-form"', 'id="irdai-updates"']
        absent = [s for s in required if s not in html]
        if absent:
            raise RuntimeError(f"Generated page failed required content check: {absent}")
        for placeholder in ("/*__CSS__*/", "/*__JS__*/", "/*__DATA__*/"):
            if placeholder in html:
                raise RuntimeError(f"Unexpanded build placeholder remains: {placeholder}")

        destination = args.output_dir if args.output_dir.is_absolute() else (ROOT / args.output_dir)
        destination = destination.resolve()
        if destination == ROOT or destination == ROOT / "data" or destination == handbook:
            raise RuntimeError(f"Refusing unsafe output directory: {destination}")
        candidate = temp / "publish"
        copy_tree_preserving(candidate, destination)
        shutil.copy2(site_index, candidate / "index.html")
        pub_data = candidate / "data"
        pub_data.mkdir(exist_ok=True)
        for name in ("app_data.json", "insurers.json", "claim_journey.json"):
            shutil.copy2(stage_data / name, pub_data / name)
        report = __import__("json").loads((stage_processed / "validation_report.json").read_text(encoding="utf-8"))
        shutil.copy2(stage_processed / "validation_report.json", pub_data / "validation_report.json")
        # A small machine-readable manifest exposes exact refresh context and artifact names.
        import json
        manifest = {
            "project": "BimaBrief",
            "latest_reporting_year": __import__("json").loads((stage_data / "app_data.json").read_text(encoding="utf-8"))["meta"]["latest_year"],
            "built_on": __import__("json").loads((stage_data / "app_data.json").read_text(encoding="utf-8"))["meta"].get("built_on"),
            "source": "IRDAI Handbook on Indian Insurance Statistics",
            "schema_validation": "PASSED",
            "state_data_checks": report.get("status", "UNKNOWN"),
            "files": ["app_data.json", "insurers.json", "claim_journey.json", "validation_report.json"]
        }
        (pub_data / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # candidate starts as a copy of prior output (if any), then is swapped atomically.
        publish_directory(candidate, destination)
        print(f"\n[PUBLISHED] {destination}\n[PASS] Transactional data validation and page generation completed.")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"\n[BUILD FAILED] Step exited with code {exc.returncode}. Existing published output was not replaced.", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:
        print(f"\n[BUILD FAILED] {type(exc).__name__}: {exc}. Existing published output was not replaced.", file=sys.stderr)
        return 1
    finally:
        if args.keep_work:
            print(f"[DEBUG] Temporary files retained at: {temp}")
        else:
            shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
