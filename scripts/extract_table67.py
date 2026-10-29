"""
Extract IRDAI Handbook Table 67 (State-wise Health Insurance Business, excl. PA & Travel)
from the official Excel file into a tidy CSV that process_state_health.py understands.

Usage:
    python scripts/extract_table67.py "<path to Part III.xlsx>" data/raw/table67.csv

Checks done here (on the raw Excel, before anything else):
  - categories in each year add up to that year's "Grand Total"
  - states add up to the "Total" (All India) row
"""
import sys

import openpyxl
import pandas as pd

SHEET = "67"

CATEGORY_MAP = {
    "group business (other than rsby & govt sponsored schemes)": "Group Business (Employer & Other)",
    "group business (other than rsby & govt sponsored schemes) (a)": "Group Business (Employer & Other)",
    "individual family floater and other than family floater insurance": "Individual Business",
    "individual family floater and other than family floater insurance (c)": "Individual Business",
    "individual business including floater/non-floater policies": "Individual Business",
    "group business (only of rsby & other govt sponsored schemes)": "Government Schemes - Combined",
    "group business (only of rsby & other govt sponsored schemes) (b)": "Government Schemes - Combined",
    "group business (only of rsby)": "Government Scheme - RSBY",
    "rsby business": "Government Scheme - RSBY",
    "ayushman bharat - pradhan mantri jan arogya yojana (ab-pmjay) only": "Government Scheme - AB-PMJAY",
    "group business (other govt sponsored schemes)": "Government Scheme - Other",
    "other govt. sponsored schemes": "Government Scheme - Other",
    "grand total": "Grand Total",
}

METRIC_MAP = {
    "no.of policies issued": ("Total Policies Issued", "value in absolute number"),
    "no. of persons covered ('000s)": ("Total Persons Covered", "value in thousand"),
    "gross premium (₹lakh)": ("Gross Premium", "value in rupees lakh"),
    "no. of claims paid": ("Total Number of Claims Paid", "value in absolute number"),
    "claims paid (₹lakh)": ("Total Amount of Claims Paid", "value in rupees lakh"),
}

STATE_FIX = {
    "orissa": "Odisha",
    "uttrakhand": "Uttarakhand",
    "jammu kashmir": "Jammu & Kashmir",
    "total": "All India",
}


def clean(x):
    return " ".join(str(x).replace("\n", " ").split()).strip()


def extract(xlsx_path):
    rows = list(openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)[SHEET].iter_rows(values_only=True))
    # Find the header row that holds the years (the one starting with "S.No.")
    hdr = next(i for i, r in enumerate(rows) if r[0] and clean(r[0]).lower().startswith("s.no"))
    yrs, cats, mets = rows[hdr], rows[hdr + 1], rows[hdr + 2]

    cols, unknown = [], set()
    y = c = None
    for j in range(2, len(yrs)):
        if yrs[j] is not None:
            y, c = clean(yrs[j]), None
        if cats[j] is not None:
            c = clean(cats[j])
        if mets[j] is None or y is None or c is None:
            continue
        cat = CATEGORY_MAP.get(c.lower())
        met = METRIC_MAP.get(clean(mets[j]).lower())
        if cat is None:
            unknown.add(f"category: {c}")
        if met is None:
            unknown.add(f"metric: {clean(mets[j])}")
        if cat and met:
            cols.append((j, y, cat, met[0], met[1]))
    if unknown:
        raise ValueError(f"Unrecognised headers in Table 67, mapping must be updated: {sorted(unknown)}")

    out = []
    for r in rows[hdr + 3:]:
        if r[1] is None:
            continue
        state = clean(r[1])
        state = STATE_FIX.get(state.lower(), state)
        for j, y, cat, sub, unit in cols:
            out.append([y, state, cat, sub, r[j], unit])
    return pd.DataFrame(out, columns=["fiscal_year", "state_name", "category", "sub_category", "value", "unit"])


def reconcile(df):
    d = df.copy()
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    k = ["fiscal_year", "state_name", "sub_category"]
    parts = d[d.category != "Grand Total"].groupby(k)["value"].sum(min_count=1)
    total = d[d.category == "Grand Total"].groupby(k)["value"].sum(min_count=1)
    a = pd.concat([parts.rename("parts"), total.rename("total")], axis=1).dropna()
    tol = (a.total.abs() * 0.005).clip(lower=0.05)
    bad_cat = a[(a.parts - a.total).abs() > tol]

    k2 = ["fiscal_year", "category", "sub_category"]
    st = d[d.state_name != "All India"].groupby(k2)["value"].sum(min_count=1)
    nat = d[d.state_name == "All India"].groupby(k2)["value"].sum(min_count=1)
    b = pd.concat([st.rename("states"), nat.rename("national")], axis=1).dropna()
    tol2 = (b.national.abs() * 0.005).clip(lower=0.05)
    bad_state = b[(b.states - b.national).abs() > tol2]
    return a, bad_cat, b, bad_state


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    df = extract(src)
    df.to_csv(dst, index=False)
    a, bad_cat, b, bad_state = reconcile(df)
    print(f"Rows written: {len(df)}  |  years: {df.fiscal_year.nunique()}  |  states/UTs: {df[df.state_name!='All India'].state_name.nunique()}")
    print(f"Categories add up to Grand Total: {len(a)-len(bad_cat)}/{len(a)} match (0.5% tolerance)")
    if len(bad_cat):
        print(bad_cat.head(10))
    print(f"States add up to All India total: {len(b)-len(bad_state)}/{len(b)} match (0.5% tolerance)")
    if len(bad_state):
        print(bad_state.head(10))
