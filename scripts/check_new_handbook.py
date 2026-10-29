"""Monthly check for a newer IRDAI Handbook. Detection only; no silent auto-ingestion."""
import argparse
import json
import re
import urllib.request
from pathlib import Path

URL = "https://irdai.gov.in/handbook-of-indian-insurance"
YEAR_PATTERN = re.compile(r"Insurance Statistics\s*(?:F\.?Y\.?\s*)?(20\d\d)[\-\u2010-\u2015](\d\d)", re.I)


def extract_edition_years(html: str) -> list[str]:
    """Return normalized edition years from titles that use hyphen/en dash variants."""
    return sorted({f"{start}-{end}" for start, end in YEAR_PATTERN.findall(html)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="docs/data/app_data.json", help="Generated app_data.json path")
    args = parser.parse_args()
    try:
        current = json.loads(Path(args.data).read_text(encoding="utf-8"))["meta"]["latest_year"]
    except Exception as exc:
        print(f"CHECK_FAILED=CurrentDataUnavailable ({type(exc).__name__})")
        raise SystemExit(0)
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (BimaBrief public-data project)"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception as exc:
        print(f"CHECK_FAILED={type(exc).__name__}")
        raise SystemExit(0)
    years = extract_edition_years(html)
    latest = years[-1] if years else None
    if not latest:
        print("CHECK_FAILED=NoEditionYearFound")
        raise SystemExit(0)
    print(f"current={current} irdai_latest={latest}")
    if latest > current:
        print(f"NEW={latest}")


if __name__ == "__main__":
    main()
