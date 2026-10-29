# Testing & Data Integrity Log — BimaBrief

## Current release candidate

The public GitHub Actions workflow validates the versioned JSON snapshot in `data/published/`, renders a fresh `build/site/` artifact, and deploys that artifact without committing generated HTML/JSON build output. The optional full source-workbook integration test runs only when a maintainer has downloaded the IRDAI workbook locally; those workbook copies are not part of the public repository.

### Build and validation sequence

The public CI build command is `python scripts/build_release.py --output-dir build/site`. It validates reviewed snapshots, renders the site and publishes only after all checks pass. For a local source-data refresh, `python scripts/rebuild_all.py` requires official workbook files downloaded locally. After manual review and tests, `python scripts/promote_snapshot.py --from-dir docs/data` promotes the reviewed output to `data/published/`.

### Required tests

| Area | What must be checked |
|---|---|
| State business — Table 67 | Required columns and units, duplicate keys, missing-vs-zero, negative values preserved, state/national reconciliation flags |
| Cashless split — Table 72 | Category breakdown retained; source “Total” mismatches flagged and never silently corrected |
| Insurer evidence | Insurer identity mapping, health ICR, market-share reconciliation, complaints total check, Table 53 scope, Table 80 state totals |
| Claim Journey — Table 66 | All published years/routes/categories, count/amount schemas, source-defined aging clocks and reconciliation residuals |
| Pydantic output schemas | Required top-level fields, state/cashless metric shapes, insurer profiles, claim-flow/aging structures, no NaN or infinity |
| Frontend | State/year/cover controls, shareable view, Metric Decoder, insurer comparison verdicts, Claim Journey controls, no JS errors |
| Responsive browser | 390px viewport, no horizontal overflow, selectors remain inside card, company columns visible, reduced-motion preference respected |
| Publishing | GitHub Pages artifact contains index plus source JSON and validation report; generated files are not pushed back into Git |

### Known interpretation limits

- Missing values remain missing; they are never converted to zero.
- Negative source components are retained and flagged; affected derived ratios can be unavailable.
- Claims paid per ₹100 premium is a same-year amount comparison, not ICR, CSR, profit or approval probability.
- Insurer claims status can have different scopes: stand-alone health insurers are health-only in Table 53, while multi-line insurers include multiple products.
- Complaint numerators may cover all products while the denominator is health policies. This is a rough indicator, not an exact health-complaint rate.
- Table 80 is a network-provider snapshot, not a ten-year trend and not a guarantee of cashless service at a particular hospital.
- Table 66 is industry-level. Annual paid/repudiated outcomes are not a same-year registration cohort, and the source uses different starting dates for aging categories.
- Reconciliation warnings preserve source values; no flow is balanced by changing or hiding values.

### Local commands

```bash
python -m pip install -r requirements.txt -r requirements-policy-api.txt
python scripts/build_release.py --output-dir build/site --repo-url https://github.com/OWNER/REPO
BIMABRIEF_SITE_DIR=build/site python -m pytest -q
# Optional full source refresh, after downloading IRDAI workbooks locally:
python scripts/rebuild_all.py
BIMABRIEF_SITE_DIR=docs python -m pytest -q
python scripts/promote_snapshot.py --from-dir docs/data
```

For an actual release, the combined CI workflow must finish successfully, including the browser smoke test. A local test skip or timeout is not a pass.


## BimaBrief additions (Oct 2026)

- The IRDAI source hub is a set of official outbound links plus dated summaries; it is not described as a live rules feed.
- Static AI policy-comparison controls stay disabled until a secure backend URL is configured and a provider API key is detected by the backend health endpoint.
- API tests should confirm provider keys are not sent to or embedded in the static site, oversized PDFs are rejected without unbounded reads, provider-unconfigured requests fail closed, and unsupported AI citations remain visibly unverified.
- Annual claim count/amount and aging values from Table 66 remain source-reported, and reconciliation warnings are shown instead of silently balancing the chart.


## Verified build and public-release checks — 29 October 2026

- Full local-source validation, while the locally downloaded official IRDAI Excel workbooks were available: `python scripts/build_release.py --output-dir build/site --repo-url https://github.com/OWNER/BimaBrief` followed by `BIMABRIEF_SITE_DIR=build/site python -m pytest -q`: **35 passed**. This included the real-workbook integration test.
- Public-release package validation, after raw workbooks and temporary/generated directories were removed: `python scripts/build_release.py --output-dir build/site --repo-url https://github.com/OWNER/BimaBrief` followed by `BIMABRIEF_SITE_DIR=build/site python -m pytest -q`: **34 passed, 1 skipped**. The single skip is intentional: the real-workbook integration test requires a maintainer to download the official workbook locally, because those files are not redistributed in this repository.
- Browser smoke checks passed on the build artifact: no JavaScript page errors, six navigation links, five dated rule cards, and no horizontal overflow at a 390px viewport.
- Pydantic output-schema validation and cross-artifact checks passed.
- Real-source warnings remain intentionally visible: 42 negative published components were retained and flagged; ratios were unavailable for 38 affected groups; some Table 72 totals did not equal their component sums. Source figures were not silently corrected.
- Optional Policy Fit API safety tests passed for consent gating, unconfigured-provider behaviour, common personal-identifier pattern checks, and bounded upload reads. **No real paid-provider API call was made.** The public site has no AI backend URL configured, so policy uploads remain disabled until a secure backend and provider secrets are configured.
- The IRDAI Handbook page check could not reach the official page in this local environment (`URLError`) and emitted `CHECK_FAILED`. The GitHub workflow is configured to open a manual-review issue in that situation rather than silently claiming there is no newer edition.

The destination GitHub Actions run has not yet been executed; deployment is not considered live or verified until that repository workflow succeeds. A passing test run covers only the defined checks and is not a guarantee that every possible error has been eliminated.
