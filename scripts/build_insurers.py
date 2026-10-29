"""
Insurer Evidence Profiles (Version 2, Feature 1).

Usage:
    python scripts/build_insurers.py data/raw/handbook docs/data/insurers.json

Sources (IRDAI Handbook on Indian Insurance Statistics 2024-25):
  Table 62  health insurance net earned premium, claims incurred, ICR by segment (health only, all insurers)
  Table 58  health insurance policies, persons covered, gross premium by segment (health only)
  Table 49  solvency ratio, quarterly (whole company)
  Table 56  grievances (whole company, all products)
  Table 53  claims status (health only for stand-alone health insurers; ALL lines for others)
  Table 80  network hospitals by insurer and state, direct agreement vs through TPAs (2024-25)

Every metric carries a "scope" so the website can refuse unfair comparisons (Comparability Engine),
and a "source" so every number can be traced (Audit Trail). Any failed check stops the build.
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

FAILS = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok:
        FAILS.append(name)


def clean(x):
    return " ".join(str(x).replace("\n", " ").split()).strip() if x is not None else ""


def num(x):
    if x is None or (isinstance(x, str) and x.strip() in ("", "-", "--", "NA", "N.A.")):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ---------------- insurer registry ----------------
# (id, display name, type, aliases checked in order; more specific aliases first)
REGISTRY = [
    ("hdfc-ergo-health", "HDFC ERGO Health (merged 2020)", "standalone_health", ["hdfc ergo health"]),
    ("reliance-health", "Reliance Health (stopped new policies 2019)", "standalone_health", ["reliance health"]),
    ("national", "National Insurance", "public", ["national insurance", "national"]),
    ("new-india", "New India Assurance", "public", ["new india"]),
    ("oriental", "Oriental Insurance", "public", ["oriental"]),
    ("united-india", "United India Insurance", "public", ["united india"]),
    ("acko", "Acko General", "private", ["acko"]),
    ("bajaj", "Bajaj Allianz General", "private", ["bajaj"]),
    ("bharti-axa", "Bharti AXA General (demerged into ICICI Lombard 2021)", "private", ["bharti axa"]),
    ("chola", "Cholamandalam MS General", "private", ["cholamandalam"]),
    ("future-generali", "Future Generali India", "private", ["future generali"]),
    ("go-digit", "Go Digit General", "private", ["go digit"]),
    ("hdfc-ergo", "HDFC ERGO General", "private", ["hdfc ergo"]),
    ("icici-lombard", "ICICI Lombard General", "private", ["icici lombard"]),
    ("iffco-tokio", "IFFCO Tokio General", "private", ["iffco"]),
    ("zurich-kotak", "Zurich Kotak General", "private", ["kotak"]),
    ("kshema", "Kshema General", "private", ["kshema"]),
    ("liberty", "Liberty General", "private", ["liberty"]),
    ("magma", "Magma General", "private", ["magma"]),
    ("navi", "Navi General", "private", ["navi"]),
    ("raheja-qbe", "Raheja QBE General", "private", ["raheja"]),
    ("reliance-general", "Reliance General", "private", ["reliance general"]),
    ("royal-sundaram", "Royal Sundaram General", "private", ["royal sundaram"]),
    ("sbi-general", "SBI General", "private", ["sbi general"]),
    ("shriram", "Shriram General", "private", ["shriram"]),
    ("tata-aig", "Tata AIG General", "private", ["tata aig"]),
    ("universal-sompo", "Universal Sompo General", "private", ["universal sompo"]),
    ("zuno", "Zuno General (formerly Edelweiss)", "private", ["zuno", "edelweiss"]),
    ("aic", "Agriculture Insurance Co.", "specialised", ["agriculture insurance"]),
    ("ecgc", "ECGC", "specialised", ["ecgc"]),
    ("aditya-birla", "Aditya Birla Health", "standalone_health", ["aditya birla"]),
    ("care", "Care Health", "standalone_health", ["care health"]),
    ("galaxy", "Galaxy Health", "standalone_health", ["galaxy"]),
    ("manipalcigna", "ManipalCigna Health", "standalone_health", ["manipalcigna", "manipal cigna"]),
    ("narayana", "Narayana Health", "standalone_health", ["narayana"]),
    ("niva-bupa", "Niva Bupa Health", "standalone_health", ["niva bupa"]),
    ("star", "Star Health", "standalone_health", ["star health"]),
]
EVENTS = {
    "icici-lombard": "Bharti AXA General's business was demerged into ICICI Lombard from 1 April 2021.",
    "hdfc-ergo": "L&T General was renamed HDFC ERGO General after a 2017 merger; HDFC ERGO Health merged into it from 1 March 2020.",
    "reliance-health": "IRDAI directed Reliance Health to stop selling new policies in November 2019; its portfolio was taken over by Reliance General.",
    "galaxy": "Started operations in 2024-25, so there is very little history.",
    "narayana": "Started operations in 2024-25, so there is very little history.",
    "zuno": "Formerly Edelweiss General Insurance.",
}
SKIP = re.compile(r"(total|public sector insurers$|private sector insurers$|private insurers$|stand-alone health insurers$|specialized insurers$|specialised insurers$|reinsurer|general insurance corporation|^insurers?$|^s\.no)", re.I)


def match(name):
    n = clean(name).lower()
    if not n or SKIP.search(n):
        return None
    if n.endswith("^") and not n.endswith("^^"):
        return "erstwhile"  # erstwhile HDFC ERGO General, merged in 2017; history only, not shown
    for iid, _, _, aliases in REGISTRY:
        if any(a in n for a in aliases):
            return iid
    return "unknown:" + clean(name)


def ff(row):
    out, last = [], None
    for x in row:
        if x is not None and clean(x):
            last = clean(x)
        out.append(last)
    return out


def header_index(rows, col0_prefix="s.no"):
    return next(i for i, r in enumerate(rows) if clean(r[0]).lower().startswith(col0_prefix))


SEG = {"government": "government", "group": "group", "family": "individual_floater",
       "individual family floater": "individual_floater", "individual other": "individual_other",
       "individual insurance excluding": "individual_other", "total": "total"}


def seg_key(c):
    c = c.lower()
    if c.startswith("government"):
        return "government"
    if c.startswith("group"):
        return "group"
    if c.startswith("individual family floater") or c.startswith("family"):
        return "individual_floater"
    if c.startswith("individual other") or c.startswith("individual insurance"):
        return "individual_other"
    if c.startswith("total"):
        return "total"
    return None


def year_table(rows, metric_map, name_col=1):
    """Parse a year / segment / metric header table into {insurer_id: {year: {segment: {metric: value}}}}."""
    h = header_index(rows)
    Y, C = ff(rows[h]), ff(rows[h + 1])
    M = [clean(x).lower() for x in rows[h + 2]]
    cols = []
    for j in range(2, len(Y)):
        if not Y[j] or not re.match(r"20\d\d-\d\d", Y[j] or ""):
            continue
        s = seg_key(C[j] or "")
        m = next((v for k, v in metric_map.items() if M[j].startswith(k)), None)
        if s and m:
            cols.append((j, Y[j], s, m))
    out, unknown, grand = {}, [], None
    for r in rows[h + 3:]:
        nm = clean(r[name_col])
        if nm.lower() == "grand total":
            grand = {}
            for j, y, s, m in cols:
                grand.setdefault(y, {}).setdefault(s, {})[m] = num(r[j])
            continue
        iid = match(nm)
        if iid is None or iid == "erstwhile":
            continue
        if iid.startswith("unknown:"):
            unknown.append(iid)
            continue
        for j, y, s, m in cols:
            v = num(r[j])
            d = out.setdefault(iid, {}).setdefault(y, {}).setdefault(s, {})
            d[m] = (d.get(m) or 0) + v if (v is not None and d.get(m) is not None) else (v if v is not None else d.get(m))
    return out, grand, unknown, cols


def build(folder):
    wb2 = openpyxl.load_workbook(folder / "Part II.xlsx", data_only=True, read_only=True)
    wb3 = openpyxl.load_workbook(folder / "Part III.xlsx", data_only=True, read_only=True)

    # ---- Table 62: health ICR ----
    r62 = list(wb3["62"].iter_rows(values_only=True))
    t62, g62, unk, cols62 = year_table(r62, {"net earned premium": "nep_lakh", "claims incurred": "claims_incurred_lakh", "incurred claims ratio": "icr"})
    check("t62_all_names_known", not unk, f"unknown: {unk}")
    years62 = sorted({c[1] for c in cols62})
    check("t62_years", len(years62) == 10, f"{years62[0]}..{years62[-1]}")
    # Recompute ICR from its parts and compare with IRDAI's published ratio
    bad = []
    for iid, ys in t62.items():
        for y, ss in ys.items():
            for s, d in ss.items():
                if d.get("nep_lakh") and d.get("claims_incurred_lakh") is not None and d.get("icr") is not None and d["nep_lakh"] > 0:
                    if abs(d["claims_incurred_lakh"] / d["nep_lakh"] - d["icr"]) > 0.01:
                        bad.append((iid, y, s))
    check("t62_icr_equals_claims_over_premium", len(bad) <= 5, f"{len(bad)} cells differ by >1 point: {bad[:4]}")
    # Insurers add up to Grand Total (latest year, Total segment, NEP)
    gy = years62[-1]
    s_ = sum((t62[i].get(gy, {}).get("total", {}).get("nep_lakh") or 0) for i in t62)
    G = (g62 or {}).get(gy, {}).get("total", {}).get("nep_lakh")
    check("t62_insurers_add_up_to_grand_total", G and abs(s_ - G) <= 0.002 * G, f"{s_:,.0f} vs {G:,.0f}" if G else "no grand total")

    # ---- Table 58: health policies & premium ----
    r58 = list(wb3["58"].iter_rows(values_only=True))
    t58, g58, unk, cols58 = year_table(r58, {"no. of policies": "policies", "no. of persons": "persons", "gross premium": "gross_premium_lakh"})
    check("t58_all_names_known", not unk, f"unknown: {unk}")
    years58 = sorted({c[1] for c in cols58})
    shares_ok = []
    for y in years58:
        G = (g58 or {}).get(y, {}).get("total", {}).get("gross_premium_lakh")
        if not G:
            continue
        tot = 0
        for iid in t58:
            p = t58[iid].get(y, {}).get("total", {}).get("gross_premium_lakh")
            if p is not None:
                t58[iid][y]["total"]["market_share_pct"] = round(p / G * 100, 2)
                tot += p
        shares_ok.append((y, round(tot / G * 100, 1)))
    check("t58_market_shares_add_to_100", all(abs(v - 100) <= 0.5 for _, v in shares_ok), f"{shares_ok[-3:]}")

    # ---- Table 49: solvency (quarterly) ----
    r49 = list(wb2["49"].iter_rows(values_only=True))
    h = header_index(r49)
    qs = [(j, clean(x)) for j, x in enumerate(r49[h]) if j >= 2 and x is not None]
    solv, unk = {}, []
    for r in r49[h + 1:]:
        iid = match(r[1])
        if iid is None or iid == "erstwhile":
            continue
        if iid.startswith("unknown:"):
            unk.append(iid)
            continue
        series = [{"q": q, "v": round(num(r[j]), 2)} for j, q in qs if num(r[j]) is not None]
        if series:
            solv[iid] = series
    check("t49_all_names_known", not unk, f"unknown: {unk}")
    check("t49_latest_quarter", qs and qs[-1][1] == "March 2025", f"latest {qs[-1][1] if qs else None}")

    # ---- Table 56: complaints (definitions change over time) ----
    r56 = list(wb2[[s for s in wb2.sheetnames if s.strip() == "56"][0]].iter_rows(values_only=True))
    h = header_index(r56)
    Y = ff(r56[h])
    sub = [clean(x).lower() for x in r56[h + 1]]
    comp = {}
    # Block 1: 2014-15 .. 2023-24, name in column 1
    yc = {}
    for j in range(2, len(Y)):
        y = Y[j]
        if y and re.match(r"20\d\d-\d\d$", y) and y != "2024-25":
            yc.setdefault(y, {})[sub[j]] = j
    for r in r56[h + 2:]:
        iid = match(r[1])
        if not iid or iid == "erstwhile" or iid.startswith("unknown:"):
            continue
        for y, cmap in yc.items():
            if "actual complaints" in cmap:
                v, d = num(r[cmap["actual complaints"]]), "actual"
            else:
                k = next((k for k in cmap if k.startswith("reported")), None)
                v, d = (num(r[cmap[k]]) if k else None), "reported"
            if v is not None:
                comp.setdefault(iid, {})[y] = {"new": v, "definition": d}
    # Block 2: 2024-25 (separate block with its own name column; "reported" includes opening balance)
    y0 = next(j for j, x in enumerate(r56[h]) if clean(x) == "2024-25")
    nc = next(j for j in range(y0, len(sub)) if sub[j] == "insurer")
    oc = next(j for j in range(nc, len(sub)) if sub[j].startswith("opening"))
    rc = next(j for j in range(nc, len(sub)) if sub[j].startswith("reported"))
    for r in r56[h + 2:]:
        iid = match(r[nc])
        if not iid or iid == "erstwhile" or iid.startswith("unknown:"):
            continue
        rep, opn = num(r[rc]), num(r[oc])
        if rep is not None:
            comp.setdefault(iid, {})["2024-25"] = {"new": rep - (opn or 0), "definition": "reported_minus_opening"}
    g = [r for r in r56 if clean(r[nc]).lower() == "grand total"]
    check("t56_grand_total_2024_25", g and num(g[0][rc]) == 137361, f"{num(g[0][rc]) if g else None} (Bima Bharosa reported 1,37,361)")

    # ---- Table 53: claims status ----
    r53 = list(wb2["53"].iter_rows(values_only=True))
    h = header_index(r53)
    Y = ff(r53[h])
    # labels sit on the first header row below the years that contains "claims paid"
    lr = next(i for i in range(h + 1, h + 5) if any(clean(x).lower().startswith("claims paid") for x in r53[i]))
    lab = [clean(x).lower() for x in r53[lr]]
    want = {"claims o/s at start": "os_start", "claims intimated": "intimated", "claims paid": "paid",
            "claims repudiated": "repudiated", "claims closed": "closed", "claims o/s at the end": "os_end"}
    cs = {}
    for r in r53[lr + 1:]:
        iid = match(r[1])
        if not iid or iid == "erstwhile" or iid.startswith("unknown:"):
            continue
        for j in range(2, len(Y)):
            k = next((v for kk, v in want.items() if lab[j].startswith(kk)), None)
            if k and Y[j]:
                cs.setdefault(iid, {}).setdefault(Y[j], {})[k] = num(r[j])
    for iid, ys in cs.items():
        for y, d in ys.items():
            dec = sum(d.get(k) or 0 for k in ("paid", "repudiated", "closed"))
            hand = (d.get("os_start") or 0) + (d.get("intimated") or 0)
            d["repudiated_pct"] = round(d["repudiated"] / dec * 100, 1) if dec and d.get("repudiated") is not None else None
            d["pending_pct"] = round(d["os_end"] / hand * 100, 1) if hand and d.get("os_end") is not None else None
            d["decided"] = dec

    star = cs.get("star", {}).get("2024-25", {})
    check("t53_star_2024_25_matches_v1", star.get("repudiated") == 317661 and star.get("repudiated_pct") == 13.6, f"{star.get('repudiated')} / {star.get('repudiated_pct')}%")
    check("t53_insurers_found", len(cs) >= 30, f"{len(cs)} insurers")

    # ---- Table 80: network hospitals by insurer x state ----
    r80 = list(wb3["78"].iter_rows(values_only=True))
    # IRDAI writes the insurer name somewhere inside its block (not always on the first row),
    # so blocks are delimited by each insurer's "Total" row instead.
    STATE80 = {"orissa": "Odisha", "uttrakhand": "Uttarakhand", "jammu kashmir": "Jammu & Kashmir",
               "jammu and kashmir": "Jammu & Kashmir", "maharasthra": "Maharashtra", "pondicherry": "Puducherry",
               "andaman & nicobar is": "Andaman & Nicobar", "andaman & nicobar is.": "Andaman & Nicobar",
               "andaman & nicobar islands": "Andaman & Nicobar", "dadra & nagra haveli": "Dadra & Nagar Haveli and Daman & Diu"}
    net, unk, block, mism = {}, [], [], []
    for r in r80[4:]:
        if r[0] and clean(r[0]).lower().startswith("note"):
            break
        if not r[1]:
            continue
        block.append(r)
        if clean(r[1]).lower() != "total":
            continue
        names = [clean(x[0]) for x in block if x[0]]
        cur = match(names[0]) if names else None
        if cur and cur.startswith("unknown:"):
            unk.append(cur)
        states, tot = {}, block[-1]
        for x in block[:-1]:
            st = clean(x[1]); st = STATE80.get(st.lower(), st)
            d, t = sum(num(v) or 0 for v in x[2:18]), sum(num(v) or 0 for v in x[18:34])
            if d or t:
                e = states.setdefault(st, {"direct": 0, "tpa": 0}); e["direct"] += int(d); e["tpa"] += int(t)
        sd, stp = sum(v["direct"] for v in states.values()), sum(v["tpa"] for v in states.values())
        td, tt = sum(num(v) or 0 for v in tot[2:18]), sum(num(v) or 0 for v in tot[18:34])
        if abs(sd - td) > 0 or abs(stp - tt) > 0:
            mism.append((cur, sd, td, stp, tt))
        if cur and not cur.startswith("unknown:"):
            net[cur] = states
        block = []
    check("t80_states_add_up_to_insurer_total", not mism, f"{len(net)-len(mism)}/{len(net)} insurers exact. Off: {mism[:4]}")
    check("t80_no_total_row_counted_as_state", all("Total" not in v for v in net.values()), "Total rows excluded")
    check("t80_all_names_known", not unk, f"unknown: {unk}")
    check("t80_insurers_found", len(net) >= 25, f"{len(net)} insurers with network data")

    # ---- assemble profiles ----
    prof = []
    for iid, name, typ, _ in REGISTRY:
        p = {"id": iid, "name": name, "type": typ, "event": EVENTS.get(iid)}
        p["health"] = t62.get(iid, {})
        p["business"] = t58.get(iid, {})
        p["solvency"] = solv.get(iid, [])
        p["complaints"] = comp.get(iid, {})
        p["claims_status"] = cs.get(iid, {})
        p["claims_status_scope"] = "health_only" if typ == "standalone_health" else "all_lines"
        p["network"] = net.get(iid, {})
        p["network_reported"] = iid in net
        n_dir = sum(v["direct"] for v in p["network"].values())  # "Total" rows are excluded above
        n_tpa = sum(v["tpa"] for v in p["network"].values())
        p["network_total"] = {"direct": n_dir, "tpa": n_tpa}
        # Complaints per 10k health policies: only fair where complaints are (almost) all health,
        # i.e. stand-alone health insurers. For others complaints cover motor, fire etc.
        for y, c in p["complaints"].items():
            pol = p["business"].get(y, {}).get("total", {}).get("policies")
            c["per_10k_health_policies"] = (round(c["new"] / pol * 10000, 1)
                                           if typ == "standalone_health" and pol and pol > 0 else None)
        p["flags"] = flags(p)
        if p["health"] or p["solvency"] or p["complaints"]:
            prof.append(p)
    tp = sum(p["business"].get("2024-25", {}).get("total", {}).get("policies") or 0 for p in prof)
    check("t58_policies_match_table67", tp == 26489690, f"{tp:,.0f} vs Table 67 grand total 26,489,690")
    check("profiles_built", len(prof) >= 30, f"{len(prof)} insurer profiles")
    ice = next(p for p in prof if p["id"] == "icici-lombard")
    check("icici_lombard_has_health_data", bool(ice["health"].get("2024-25")), "Table 62 row found")
    return prof


def flags(p):
    """Neutral, explainable context signals; never a composite insurer rating."""
    out = []
    solvency = p.get("solvency") or []
    if solvency:
        last = solvency[-1]
        value = last.get("v")
        quarter = str(last.get("q") or "date not stated")
        year_match = re.search(r"(20\d{2})", quarter)
        observation_year = int(year_match.group(1)) if year_match else None
        # This snapshot covers FY 2024-25. Do not present a historical ratio for
        # a merged/stopped insurer as a current signal.
        if observation_year not in {2024, 2025}:
            out.append({
                "level": "info",
                "text": f"Latest solvency observation available in this dataset is {value:.2f} for {quarter}. This is historical information and does not establish current status.",
                "rule": "latest available solvency observation predates the current reporting window; no current status inferred",
            })
        elif value < 1.5:
            out.append({
                "level": "info",
                "text": f"IRDAI Table 49 reports a solvency ratio of {value:.2f} for {quarter}, below the stated minimum of 1.50. Check current official disclosures; this source comparison is not an independent compliance finding.",
                "rule": "source-reported ratio compared with stated IRDAI minimum; factual indicator only",
            })
        elif value < 1.7:
            out.append({
                "level": "watch",
                "text": f"Reported solvency ratio is {value:.2f} for {quarter}, within our display band above the stated minimum of 1.50. This is our caution rule, not a separate IRDAI category.",
                "rule": "1.50 <= solvency < 1.70 (project display rule only)",
            })

    years = sorted(p.get("health", {}))[-3:]
    icrs = [p["health"][y].get("total", {}).get("icr") for y in years]
    if len(icrs) == 3 and all(v is not None and v > 1 for v in icrs):
        out.append({
            "level": "info",
            "text": f"The published health ICR was above 100% in each of {years[0]} to {years[-1]} ({', '.join(f'{v*100:.0f}%' for v in icrs)}). This is an incurred-claims-to-earned-premium measure, not a service-quality or claim-approval score.",
            "rule": "health ICR > 100% in each of the latest three reported years",
        })

    if p["type"] == "standalone_health":
        complaint_years = sorted(y for y, c in p.get("complaints", {}).items() if c.get("per_10k_health_policies") is not None)
        last3 = complaint_years[-3:]
        vals = [p["complaints"][y]["per_10k_health_policies"] for y in last3]
        defs = {p["complaints"][y]["definition"] for y in last3}
        if len(vals) == 3 and vals[0] < vals[1] < vals[2] and len(defs) == 1:
            out.append({
                "level": "info",
                "text": f"The reported complaints-per-policy indicator rose in each of {last3[0]} to {last3[-1]} ({', '.join(str(v) for v in vals)}). Complaint definitions match, but the numerator/denominator limitation still applies.",
                "rule": "indicator rises in three consecutive years under the same complaint definition; contextual signal only",
            })

    if p["id"] in ("galaxy", "narayana"):
        out.append({
            "level": "info",
            "text": "Limited history in this dataset; a long-term trend is not assessed.",
            "rule": "short observed history in the current dataset",
        })
    return out


METRICS = {
    "health_icr": {"label": "Health incurred claims ratio", "table": "Table 62", "scope": "health_only",
                   "formula": "Net claims incurred ÷ net earned premium (health, excl. PA & travel), as published by IRDAI",
                   "note": "Above 100% means health claims cost more than the premium earned that year. It does not measure customer service or approval chances."},
    "market_share": {"label": "Share of India's health premium", "table": "Table 58", "scope": "health_only",
                     "formula": "Insurer's gross health premium ÷ all insurers' gross health premium (excl. PA & travel)"},
    "solvency": {"label": "Solvency ratio", "table": "Table 49", "scope": "company_total",
                 "formula": "Available solvency margin ÷ required solvency margin, quarterly, as published. IRDAI minimum: 1.50"},
    "complaints_raw": {"label": "New complaints", "table": "Table 56", "scope": "company_total",
                       "formula": "2018-19 to 2023-24: 'actual complaints' (duplicates removed). 2014-15 to 2017-18: 'reported'. 2024-25: reported minus opening balance (IRDAI footnote: reported includes opening)"},
    "complaints_per_10k": {"label": "All-product complaints per 10,000 health policies — rough indicator", "table": "Tables 56 + 58", "scope": "health_only_approx",
                           "formula": "New reported complaints ÷ health policies × 10,000. The complaint numerator includes all reported products while the denominator is health policies; this is not an exact health-complaint rate."},
    "repudiated_pct": {"label": "Claims repudiated (% of claims decided)", "table": "Table 53", "scope": "by_insurer_type",
                       "formula": "Claims repudiated ÷ (paid + repudiated + closed) × 100. Health only for stand-alone health insurers; all products (motor, fire, health…) for multi-line insurers.",
                       "note": "These are outcomes recorded in the reporting year, not the rejection probability for claims newly registered in that year."},
    "pending_pct": {"label": "Year-end outstanding share of claims workload", "table": "Table 53", "scope": "by_insurer_type",
                     "formula": "Claims outstanding at year-end ÷ (claims outstanding at start + claims intimated during year) × 100.",
                     "note": "This is a year-end outstanding snapshot relative to the workload available during the year, not the share of newly filed claims still pending."},
    "network": {"label": "Network providers listed by IRDAI", "table": "Table 80", "scope": "snapshot_2024_25",
                "formula": "Count of providers listed under direct agreements and TPA arrangements in the relevant state or across the table, 2024–25. The same provider may appear for several insurers.",
                "note": "This is a 2024–25 snapshot, not a ten-year series, and does not guarantee cashless availability at a specific hospital."},
}

if __name__ == "__main__":
    folder, dst = Path(sys.argv[1]), Path(sys.argv[2])
    prof = build(folder)
    if FAILS:
        sys.exit(f"\nBUILD STOPPED. Failed checks: {FAILS}. Nothing was written.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps({"metrics": METRICS, "insurers": prof}, ensure_ascii=False, separators=(",", ":")))
    print(f"\nWrote {dst} ({dst.stat().st_size/1024:.0f} KB), {len(prof)} insurers")
