# Contributing to BimaBrief

Thanks for helping improve the accuracy and clarity of BimaBrief.

## Report a data issue

Use the **Data correction request** issue template. Include the metric, reporting year, official source URL/table, and a reproducible explanation. Please do not include policy documents, claim numbers, names, contact details, medical information, or confidential customer data.

## Standards for changes

- Prefer official source tables and document the table, year, unit, denominator, and formula.
- Preserve source-reported values, including zeroes and negative adjustments. Flag discrepancies rather than silently changing values to make totals reconcile.
- Keep missing values distinct from reported zeroes.
- Do not compare incompatible business scopes as if they were equivalent.
- Distinguish source-reported figures, derived metrics, illustrative examples, and unavailable values.
- Use neutral, factual language. Do not describe a company as fraudulent, dishonest, best, or worst unless there is a precisely cited, directly relevant official finding—and even then describe the finding, not an unsupported generalisation.
- Do not submit allegations about individual employees or policyholders.
- Do not add secrets, API keys, raw private policy documents, claim records or personal/medical data to issues, tests, examples or commits.

## Validation

Run the build and tests listed in `README.md` and `TESTING.md`. A successful test run confirms the defined checks only; it is not proof that every value is free of errors. Include any remaining discrepancy or limitation in your pull request description.
