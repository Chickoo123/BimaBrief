"""Pydantic v2 schemas for data artifacts published by BimaBrief.

Schemas intentionally distinguish blank/missing values (None) from reported zeroes.
All numeric fields reject NaN and infinity. Unknown keys are rejected in core
metric records so source/schema drift fails the build instead of silently reaching UI.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CoreModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class StateMetric(CoreModel):
    policies: float | None = None
    persons_covered_thousand: float | None = None
    gross_premium_lakh: float | None = None
    claims_paid_count: float | None = None
    claims_paid_lakh: float | None = None
    has_negative_component: bool = False


class CashlessMetric(CoreModel):
    cashless: float | None = None
    reimbursement: float | None = None
    both: float | None = None
    benefit: float | None = None
    total: float | None = None
    parts_total: float | None = None
    total_mismatch: bool = False
    cashless_share_pct: float | None = None


class SimpleClaimStatus(CoreModel):
    name: str
    os_start: float | None = None
    intimated: float | None = None
    paid: float | None = None
    repudiated: float | None = None
    closed: float | None = None
    os_end: float | None = None
    repudiated_pct: float | None = None
    pending_end_pct: float | None = None
    complaints_new: float | None = None
    policies: float | None = None
    complaints_per_10k: float | None = None
    new_company: bool = False
    claims_handled: float | None = None


class AppData(CoreModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    meta: dict[str, Any]
    states: dict[str, dict[str, dict[str, StateMetric]]]
    cashless: dict[str, dict[str, dict[str, CashlessMetric]]]
    insurers: list[SimpleClaimStatus]


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    label: str
    table: str
    scope: str
    formula: str
    note: str | None = None


class HealthSegment(CoreModel):
    nep_lakh: float | None = None
    claims_incurred_lakh: float | None = None
    icr: float | None = None


class BusinessSegment(CoreModel):
    policies: float | None = None
    persons: float | None = None
    gross_premium_lakh: float | None = None
    market_share_pct: float | None = None


class SolvencyPoint(CoreModel):
    q: str
    v: float | None = None


class ComplaintYear(CoreModel):
    new: float | None = None
    definition: str | None = None
    per_10k_health_policies: float | None = None


class ClaimsStatusYear(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    os_start: float | None = None
    intimated: float | None = None
    paid: float | None = None
    repudiated: float | None = None
    closed: float | None = None
    os_end: float | None = None
    repudiated_pct: float | None = None
    pending_pct: float | None = None
    decided: float | None = None


class NetworkCounts(CoreModel):
    direct: float = 0
    tpa: float = 0


class Signal(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    level: str
    text: str
    rule: str


class InsurerProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str
    name: str
    type: str
    event: str | None = None
    health: dict[str, dict[str, HealthSegment]]
    business: dict[str, dict[str, BusinessSegment]]
    solvency: list[SolvencyPoint]
    complaints: dict[str, ComplaintYear]
    claims_status: dict[str, ClaimsStatusYear]
    claims_status_scope: str
    network: dict[str, NetworkCounts]
    network_reported: bool
    network_total: NetworkCounts
    flags: list[Signal]


class InsurerData(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    metrics: dict[str, MetricDefinition]
    insurers: list[InsurerProfile]


class ClaimPair(CoreModel):
    count: float | None = None
    amount_lakh: float | None = None


class AgingBucket(CoreModel):
    label: str
    count: float | None = None
    amount_lakh: float | None = None


class ClaimCategory(CoreModel):
    flows: dict[str, ClaimPair]
    aging: dict[str, list[AgingBucket]]


class ClaimRoute(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    categories: dict[str, ClaimCategory]
    flows: dict[str, ClaimPair]
    aging: dict[str, list[AgingBucket]]


class ClaimYear(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    year: str
    routes: dict[str, ClaimRoute]
    reconciliation: dict[str, dict[str, float | None]]


class ClaimMeta(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    source: str
    source_table: str
    title: str
    latest_year: str
    years: list[str]
    amount_unit: str
    count_unit: str
    aging_notes: dict[str, str]
    limitations: list[str]


class ClaimJourneyData(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    meta: ClaimMeta
    years: dict[str, ClaimYear]
