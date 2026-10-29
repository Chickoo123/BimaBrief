# BimaBrief: GitHub Pages deployment and optional AI setup

## Publish the public-data website

1. Create a GitHub repository named `BimaBrief` (or your preferred name) under your account.
2. Upload the contents of this folder to the repository root. Keep `data/published/`, the scripts, tests and site template. Do not upload raw workbook copies, `.env` files, API keys, user policy documents, caches or temporary build directories.
3. In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
4. Push to `main`. The workflow validates the reviewed JSON snapshot, builds a new site artifact, runs tests, checks the official Handbook listing and deploys the artifact.
5. Verify the GitHub Actions run before sharing the live link. A failed workflow must be investigated, not bypassed.

The public workflow deploys from reviewed `data/published/` snapshots; full Excel workbooks are not included because their redistribution terms have not been verified. To refresh source data, a maintainer downloads the new workbooks locally from the official IRDAI page, runs the full rebuild, inspects warnings and tests, then promotes reviewed JSON snapshots. Do not commit the raw workbooks.

## Handbook check

A monthly source check looks at the official [IRDAI Handbook listing](https://irdai.gov.in/handbook-of-indian-insurance). If a newer edition appears or the page cannot be checked, it opens a review issue. This is detection only, not automatic data ingestion and not a live IRDAI circular feed.

## Optional AI Policy Fit Checker

The website ships with the AI checker disabled by default. To enable it, deploy `policy_api/Dockerfile` to a trusted HTTPS host and configure the selected provider API key **only** in the backend host's secret manager (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`). Never put a key in HTML, JavaScript, the repository, GitHub Pages variables or a public issue.

Set `BIMABRIEF_ALLOWED_ORIGINS` on the backend to the exact GitHub Pages origin (no wildcard). Configure the GitHub Actions repository variable `BIMABRIEF_POLICY_API_BASE` to the backend's HTTPS base URL, without a trailing slash, then run the workflow. Test with non-sensitive sample PDFs first, confirm CORS and rate limits, and set provider spending limits. API use is billed separately from consumer chat subscriptions.

Uploaded PDFs are forwarded to the selected AI provider and are not persisted by BimaBrief's API backend. The provider's own data handling and retention terms still apply. Users should remove identifiers and sensitive details wherever possible and should upload only documents they are authorised to share. AI output is a document-based comparison, not a claim-approval prediction, legal advice, financial advice or a universal best-policy score.

## Before launch

- Review `TESTING.md` and run the workflow.
- Keep public content factual, source-linked and neutral.
- Do not claim that BimaBrief is affiliated with IRDAI or an insurer.
- Check the original circular and policy wording before relying on a rule.
- Do not publish personal data, claim records, confidential policy documents or allegations as facts.
