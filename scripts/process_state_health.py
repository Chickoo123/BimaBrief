"""
BimaBrief - Step 1
Process IRDAI state-wise health insurance data (via Dataful CSV) into clean JSON for the app.

Usage:
    python scripts/process_state_health.py data/raw/<file>.csv

Outputs:
    data/processed/state_health.json      clean data used by the app
    data/processed/validation_report.json every check and its result

Safety lock: if any HARD check fails, the script exits with code 1 and writes
no app data, so a bad data update can never go live.
"""
import json
import sys
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["fiscal_year", "state_name", "category", "sub_category", "value", "unit"]

# sub_category in source -> (metric key, expected unit)
METRICS = {
    "total policies issued": ("policies", "value in absolute number"),
    "number of policies issued": ("policies", "value in absolute number"),
    "total persons covered": ("persons_covered_thousand", "value in thousand"),
    "number of persons covered": ("persons_covered_thousand", "value in thousand"),
    "gross premium": ("gross_premium_lakh", "value in rupees lakh"),
    "total number of claims paid": ("claims_paid_count", "value in absolute number"),
    "number of claims paid": ("claims_paid_count", "value in absolute number"),
    "total amount of claims paid": ("claims_paid_lakh", "value in rupees lakh"),
    "claims paid": ("claims_paid_lakh", "value in rupees lakh"),
}

GOVT_KEYWORDS = ["rsby", "pmjay", "government", "govt"]
# Note: Table 67 labels like "Group Business (other than RSBY & Govt ...)" are renamed by
# extract_table67.py to "Group Business (Employer & Other)" so they are not mistaken for government.


def classify(category: str) -> str:
    c = category.lower()
    if "total" in c:
        return "total_row"  # kept separate so it is never double-counted
    if any(k in c for k in GOVT_KEYWORDS):
        return "government_scheme"
    if "group" in c:
        return "group"
    if "individual" in c:
        return "individual"
    return "other"


def run(csv_path: str, out_dir: str = "data/processed") -> dict:
    checks = []

    def check(name, passed, detail="", hard=True):
        checks.append({"check": name, "passed": bool(passed), "hard": hard, "detail": detail})
        return passed

    df = pd.read_csv(csv_path)

    # 1. Structure
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if not check("required_columns_present", not missing, f"missing: {missing}"):
        return _finish(checks, None, out_dir)

    for col in ["fiscal_year", "state_name", "category", "sub_category", "unit"]:
        df[col] = df[col].astype(str).str.strip()
    raw = df["value"]
    blank = raw.isna() | (raw.astype(str).str.strip() == "")
    df["value"] = pd.to_numeric(raw, errors="coerce")

    check("no_empty_file", len(df) > 0, f"rows: {len(df)}")
    # Blank = missing in source: kept as missing (never turned into 0), only a warning.
    check("missing_values_kept_missing", True, f"blank values kept as missing: {int(blank.sum())}", hard=False)
    # Text that is not a number (e.g. "abc") means the file is broken: hard stop.
    bad_values = int((df["value"].isna() & ~blank).sum())
    check("all_values_numeric", bad_values == 0, f"non-numeric text values: {bad_values}")
    # Negative values exist in the official IRDAI data (mostly government-scheme premium
    # refunds/adjustments). They are kept exactly as published, flagged for review,
    # and never used to calculate a ratio.
    neg = df[df["value"] < 0]
    check("negative_values_flagged", True,
          f"{len(neg)} negative values kept as published (adjustments); categories: "
          f"{sorted(neg['category'].unique().tolist())}", hard=False)

    # 2. Known metrics only (unknown ones are reported, never silently dropped)
    df["metric_key"] = df["sub_category"].str.lower().map(lambda s: METRICS.get(s, (None, None))[0])
    df["expected_unit"] = df["sub_category"].str.lower().map(lambda s: METRICS.get(s, (None, None))[1])
    unknown = sorted(df.loc[df["metric_key"].isna(), "sub_category"].unique().tolist())
    check("all_metrics_recognised", not unknown, f"unknown sub_categories: {unknown}", hard=False)
    df = df[df["metric_key"].notna()].copy()

    wrong_unit = df[df["unit"] != df["expected_unit"]]
    check("units_consistent", wrong_unit.empty,
          f"rows with unexpected unit: {len(wrong_unit)}; e.g. {wrong_unit[['sub_category','unit']].drop_duplicates().head(3).to_dict('records')}")

    # 3. Duplicates
    key = ["fiscal_year", "state_name", "category", "metric_key"]
    dups = int(df.duplicated(subset=key).sum())
    check("no_duplicate_rows", dups == 0, f"duplicate keys: {dups}")

    # 4. Categories
    df["group"] = df["category"].map(classify)
    cats = df[["category", "group"]].drop_duplicates().sort_values("group").to_dict("records")
    check("category_mapping", True, f"{cats}", hard=False)

    # 5. Coverage info
    years = sorted(df["fiscal_year"].unique().tolist())
    states = sorted(df["state_name"].unique().tolist())
    check("coverage", True, f"{len(years)} years ({years[0]} to {years[-1]}), {len(states)} states/UTs", hard=False)

    # 6. Reconciliation: sum of states must match the source's own All India total
    is_national = df["state_name"].str.lower().isin(["all india", "india", "total"])
    if is_national.any():
        k = ["fiscal_year", "category", "metric_key"]
        nat = df[is_national].groupby(k)["value"].sum(min_count=1)
        st = df[~is_national].groupby(k)["value"].sum(min_count=1)
        both = pd.concat([nat.rename("national"), st.rename("states")], axis=1).dropna()
        tol = (both["national"].abs() * 0.01).clip(lower=0.05)  # 1% or rounding
        off = both[(both["national"] - both["states"]).abs() > tol]
        check("states_match_national_total", off.empty,
              f"{len(off)} of {len(both)} totals differ by >1%: {off.reset_index().head(3).to_dict('records')}",
              hard=False)
    else:
        check("states_match_national_total", True, "no All India rows in file, check skipped", hard=False)

    if any(c["hard"] and not c["passed"] for c in checks):
        return _finish(checks, None, out_dir)
    df = df[~is_national].copy()

    # 7. Build tidy table: one row per year/state/category with all metrics
    wide = (df.pivot_table(index=["fiscal_year", "state_name", "category", "group"],
                           columns="metric_key", values="value", aggfunc="first")
              .reset_index())
    for m in {v[0] for v in METRICS.values()}:
        if m not in wide.columns:
            wide[m] = None

    # Claims paid as % of premium. Only where premium > 0, otherwise "not available".
    def ratio(r):
        p, c = r["gross_premium_lakh"], r["claims_paid_lakh"]
        if pd.isna(p) or pd.isna(c) or p <= 0 or c < 0:
            return None  # no ratio from missing, zero or negative (adjustment) values
        return round(c / p * 100, 2)

    wide["claims_to_premium_pct"] = wide.apply(ratio, axis=1)

    # 8. Sanity: ratios far above 100% are possible (claims can exceed premium),
    #    but extreme values are flagged for human review, not hidden.
    extreme = wide[wide["claims_to_premium_pct"] > 300]
    check("extreme_ratios_flagged", True,
          f"{len(extreme)} rows above 300% need review: "
          f"{extreme[['fiscal_year','state_name','category','claims_to_premium_pct']].head(5).to_dict('records')}",
          hard=False)

    return _finish(checks, wide, out_dir)


def _finish(checks, wide, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    hard_fail = any(c["hard"] and not c["passed"] for c in checks)
    report = {"status": "FAILED" if hard_fail else "PASSED", "checks": checks}
    (out / "validation_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    if not hard_fail and wide is not None:
        records = json.loads(wide.to_json(orient="records"))
        (out / "state_health.json").write_text(json.dumps(records, ensure_ascii=False))
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python scripts/process_state_health.py <csv_path> [output_dir]")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "data/processed"
    rep = run(sys.argv[1], out_dir)
    for c in rep["checks"]:
        mark = "PASS" if c["passed"] else ("FAIL" if c["hard"] else "WARN")
        print(f"[{mark}] {c['check']}: {c['detail'][:200]}")
    print(f"\nOverall: {rep['status']}")
    sys.exit(0 if rep["status"] == "PASSED" else 1)
