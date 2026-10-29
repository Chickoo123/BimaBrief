"""Safety-focused tests for the optional, backend-only policy document checker."""
import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile as StarletteUploadFile

from policy_api import main as policy_api


@pytest.fixture
def client():
    return TestClient(policy_api.app)


def clear_provider_keys(monkeypatch):
    for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def minimal_family_profile():
    return {
        "household": "family_with_children",
        "target_cover": "10 lakh",
        "annual_budget": "not sure",
        "state": "Maharashtra",
        "priorities": ["low_copay", "room_rent_limits"],
        "notes": "",
    }


def test_health_endpoint_reports_provider_availability_only(client, monkeypatch):
    clear_provider_keys(monkeypatch)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["providers"] == {"gemini": False, "claude": False, "openai": False}
    assert "api_key" not in json.dumps(body).lower()
    assert body["uploads_persisted_by_bimabrief"] is False


def test_policy_compare_fails_closed_when_consent_missing(client, monkeypatch):
    clear_provider_keys(monkeypatch)
    response = client.post(
        "/api/policy-compare",
        data={
            "provider": "gemini",
            "family_profile": json.dumps(minimal_family_profile()),
            "consent_to_provider": "false",
        },
        files={
            "quote_a": ("a.pdf", b"%PDF-fake", "application/pdf"),
            "quote_b": ("b.pdf", b"%PDF-fake", "application/pdf"),
        },
    )
    assert response.status_code == 400
    assert "Consent is required" in response.json()["detail"]


def test_policy_compare_fails_closed_when_provider_not_configured(client, monkeypatch):
    clear_provider_keys(monkeypatch)
    response = client.post(
        "/api/policy-compare",
        data={
            "provider": "gemini",
            "family_profile": json.dumps(minimal_family_profile()),
            "consent_to_provider": "true",
        },
        files={
            "quote_a": ("a.pdf", b"%PDF-fake", "application/pdf"),
            "quote_b": ("b.pdf", b"%PDF-fake", "application/pdf"),
        },
    )
    assert response.status_code == 503
    assert "No files were sent" in response.json()["detail"]


def test_family_profile_rejects_common_personal_identifiers():
    profile = minimal_family_profile()
    profile["notes"] = "Please call 9876543210"
    with pytest.raises(Exception):
        policy_api.FamilyProfile.model_validate(profile)


def test_oversized_pdf_is_rejected_after_bounded_read(monkeypatch):
    upload = StarletteUploadFile(
        filename="oversized.pdf",
        file=BytesIO(b"%PDF-" + b"x" * policy_api.MAX_FILE_BYTES),
        headers=Headers({"content-type": "application/pdf"}),
    )
    import asyncio
    with pytest.raises(policy_api.HTTPException) as exc:
        asyncio.run(policy_api._read_upload(upload, "quote_a", "Offer A quote", True, 0))
    assert exc.value.status_code == 413
    assert "size limit" in exc.value.detail


def test_provider_model_defaults_are_configurable_and_known():
    assert policy_api.PROVIDER_ENV["gemini"][2] == "gemini-3.8-flash"
    assert policy_api.PROVIDER_ENV["claude"][2] == "claude-sonnet-5"
    assert policy_api.PROVIDER_ENV["openai"][2] == "gpt-6-luna"
    assert all(len(config) == 3 for config in policy_api.PROVIDER_ENV.values())
