# Security reporting

Please do not publish API keys, secrets, policy documents, claim records, or personal/medical data in an issue. If you discover an exposed credential or a security weakness in the optional Policy Fit backend, use GitHub's private vulnerability reporting feature for this repository if available, or contact the maintainer privately before publishing technical details.

API keys must be stored only in the backend host's secret manager. They must never be committed to this repository, included in the static site, or exposed through browser configuration.
