"""Build a self-contained BimaBrief HTML site from validated JSON artifacts.

Default local preview:
  python scripts/build_site.py
CI / Pages artifact build:
  python scripts/build_site.py --data-dir build/staging/data --output build/staging/index.html --repo-url https://github.com/OWNER/REPO
The page embeds data for a single-file no-backend experience. JSON files are also
copied alongside the page as a transparent, inspectable data artifact.
"""
from __future__ import annotations
import argparse
import json
import html as html_lib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def blob(obj):
    # Prevent a closing script tag in data from terminating the inline JSON script.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_url_positional", nargs="?", default="", help="Backwards-compatible repository URL")
    parser.add_argument("--repo-url", default="", help="Repository URL included in site metadata")
    parser.add_argument("--policy-api-base", default=os.environ.get("BIMABRIEF_POLICY_API_BASE", ""), help="Optional secure Policy Fit API base URL; leave blank to keep AI uploads disabled")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "docs/data", help="Directory containing three validated JSON files")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/index.html", help="Destination HTML file")
    args = parser.parse_args()
    repo_url = args.repo_url or args.repo_url_positional
    data_dir = args.data_dir.resolve()
    out_path = args.output.resolve()

    inputs = {
        "data": data_dir / "app_data.json",
        "insurers": data_dir / "insurers.json",
        "claims": data_dir / "claim_journey.json",
    }
    missing = [str(p) for p in inputs.values() if not p.is_file()]
    if missing:
        raise SystemExit("Build stopped; required validated data file(s) missing: " + ", ".join(missing))

    data = json.loads(inputs["data"].read_text(encoding="utf-8"))
    insurers = json.loads(inputs["insurers"].read_text(encoding="utf-8"))
    claims = json.loads(inputs["claims"].read_text(encoding="utf-8"))
    if repo_url:
        data.setdefault("meta", {})["repo_url"] = repo_url

    template_path = ROOT / "site/index.template.html"
    template = template_path.read_text(encoding="utf-8")
    placeholders = ("/*__CSS__*/", "/*__JS__*/", "/*__DATA__*/", "/*__INSURERS__*/", "/*__CLAIMS__*/", "/*__POLICY_API_BASE__*/")
    missing_placeholders = [ph for ph in placeholders if ph not in template]
    if missing_placeholders:
        raise SystemExit(f"Build stopped; template placeholder(s) missing: {missing_placeholders}")

    css = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "site/css").glob("*.css")))
    js = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "site/js").glob("*.js")))
    html = (template.replace("/*__CSS__*/", css)
            .replace("/*__JS__*/", js.replace("</script", "<\\/script"))
            .replace("/*__DATA__*/", blob(data))
            .replace("/*__INSURERS__*/", blob(insurers))
            .replace("/*__CLAIMS__*/", blob(claims))
            .replace("/*__POLICY_API_BASE__*/", html_lib.escape(args.policy_api_base.strip().rstrip("/"), quote=True)))

    required_markers = ("BimaBrief", 'id="app-data"', 'id="insurer-data"', 'id="claim-data"', 'id="decoder"', 'id="policy-fit"', 'id="policy-fit-form"', 'id="irdai-updates"')
    failed = [marker for marker in required_markers if marker not in html]
    if failed:
        raise SystemExit(f"Build stopped; generated page missing marker(s): {failed}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
