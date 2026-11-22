"""The desk as a service: readiness checks, the questionnaire agent and delivery staffing over HTTP.

Customer files are untrusted input: sizes are capped, XML is parsed with defusedxml, and nothing a customer sends
changes what the desk decides. Settings come from config/product.json.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from golive.delivery import Intake, Tdm, allocate, complexity
from golive.dms import IntegrationPlan, audit
from golive.findings import Finding, Severity
from golive.questionnaire import QuestionnaireAgent, load_evidence
from golive.residency import Requirement, TenantPlan
from golive.residency import check as check_residency
from golive.sso import SsoExpectations, check_oidc_discovery, check_saml_metadata

MAX_XML = 512_000
MAX_QUESTIONS = 500
MAX_QUESTION_CHARS = 2_000
MAX_DMS_OBJECTS = 200_000


@lru_cache(maxsize=1)
def product() -> dict[str, Any]:
    out: dict[str, Any] = json.loads(Path(os.environ.get("GOLIVE_PRODUCT", "config/product.json")).read_text())
    return out


def verdict(findings: list[Finding]) -> dict[str, Any]:
    blockers = sum(1 for f in findings if f.severity is Severity.BLOCKER)
    return {"ready": blockers == 0, "blockers": blockers, "findings": [f.as_dict() for f in findings]}


class SamlCheck(BaseModel):
    metadata_xml: str = Field(max_length=MAX_XML)
    sp_entity_id: str
    acs_url: str
    go_live: dt.date
    configured_reply_urls: list[str] | None = None
    needs_groups: bool = True


class OidcCheck(BaseModel):
    discovery: dict[str, Any]
    expected_issuer: str | None = None


class DmsCheck(BaseModel):
    export: dict[str, Any]
    mode: Literal["per_user", "service_account"] = "per_user"
    group_depth: int = Field(8, ge=0, le=64)
    walls_mapped: bool = True
    anyone_links_public: bool = False
    acl_sync_minutes: int = Field(15, ge=0)


class ResidencyCheck(BaseModel):
    residency: Literal["DE", "EU", "UK", "EU_UK", "ANY"] = "EU"
    zero_retention_models: bool = True
    max_retention_days: int = 365
    no_training_on_content: bool = True
    tenant: dict[str, Any]


class Questionnaire(BaseModel):
    questions: list[str] = Field(max_length=MAX_QUESTIONS)
    today: dt.date | None = None


class Manager(BaseModel):
    name: str
    skills: list[str]
    languages: list[str]
    hours: float = 22.0
    load: float = 0.0


class Staffing(BaseModel):
    intake: dict[str, Any]
    team: list[Manager] = Field(min_length=1, max_length=50)


app = FastAPI(title="legal-golive-desk", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/checks/sso/saml")
def saml(body: SamlCheck) -> dict[str, Any]:
    exp = SsoExpectations(body.sp_entity_id, body.acs_url, body.go_live, product()["sso"]["certMarginDays"], body.needs_groups)
    try:
        return verdict(check_saml_metadata(body.metadata_xml, exp, body.configured_reply_urls))
    except Exception as e:
        raise HTTPException(422, f"metadata could not be read: {type(e).__name__}") from None


@app.post("/checks/sso/oidc")
def oidc(body: OidcCheck) -> dict[str, Any]:
    return verdict(check_oidc_discovery(body.discovery, body.expected_issuer))


@app.post("/checks/dms")
def dms(body: DmsCheck) -> dict[str, Any]:
    e = body.export
    size = sum(len(e.get(k, [])) for k in ("users", "documents", "containers", "walls")) + len(e.get("groups", {}))
    if size > MAX_DMS_OBJECTS:
        raise HTTPException(413, f"export has {size} objects; the limit is {MAX_DMS_OBJECTS}")
    plan = IntegrationPlan(body.mode, body.group_depth, body.walls_mapped, body.anyone_links_public, body.acl_sync_minutes)
    try:
        a = audit(e, plan, product()["dms"]["maxSyncMinutes"])
    except (KeyError, TypeError) as err:
        raise HTTPException(422, f"export is missing or has a wrong field: {err}") from None
    return {**verdict(a.findings), "audit": a.as_dict()}


@app.post("/checks/residency")
def residency(body: ResidencyCheck) -> dict[str, Any]:
    req = Requirement(body.residency, body.zero_retention_models, body.max_retention_days, body.no_training_on_content)
    try:
        plan = TenantPlan.from_dict(body.tenant)
    except (KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, f"tenant plan is missing or has a wrong field: {err}") from None
    return verdict(check_residency(req, plan))


@app.post("/questionnaires/answer")
def answer(body: Questionnaire) -> dict[str, Any]:
    if any(len(q) > MAX_QUESTION_CHARS for q in body.questions):
        raise HTTPException(413, f"a question is longer than {MAX_QUESTION_CHARS} characters")
    q = product()["questionnaire"]
    agent = QuestionnaireAgent(load_evidence(), body.today or dt.date.today(), q["minScore"], q["minMargin"], q["minCoverage"])
    answers = [agent.answer(x) for x in body.questions]
    drafted = sum(1 for a in answers if a.status == "drafted")
    return {"drafted": drafted, "to_security": len(answers) - drafted, "answers": [a.as_dict() for a in answers]}


@app.post("/delivery/assign")
def assign(body: Staffing) -> dict[str, Any]:
    try:
        i = Intake(**body.intake)
    except TypeError as err:
        raise HTTPException(422, f"intake is missing or has a wrong field: {err}") from None
    team = [Tdm(m.name, frozenset(m.skills), frozenset(m.languages), m.hours, m.load) for m in body.team]
    t = allocate(i, team, match=True, max_load_weeks=product()["allocation"]["maxLoadWeeks"])
    return {"manager": t.name, "expected_hours": round(complexity(i), 1)}
