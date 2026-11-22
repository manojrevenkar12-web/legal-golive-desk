"""The simulated EMEA delivery region: law firms and legal teams going live on an AI workspace.

The world plants problems in each customer's real setup files, decides how long the customer's IT and security
reviewers take, and records what happens: go-live weeks, slips, and incidents after go-live. Designs see only what
delivery can see; the world keeps the truth.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from golive.delivery import Intake, Tdm, allocate, at_risk
from golive.dms import audit
from golive.findings import Finding, Severity
from golive.keyed import Keyed, poisson
from golive.questionnaire import QuestionnaireAgent, load_evidence
from golive.residency import Requirement
from golive.residency import check as check_residency
from golive.sso import SsoExpectations, check_oidc_discovery, check_saml_metadata
from golive.world import artifacts
from golive.world.questions import BANK, is_german

# which finding proves which planted problem was found
FOUND_BY = {
    "certExpiring": {"saml.cert.expiring", "saml.cert.expired"},
    "weakKey": {"saml.cert.weak_key"},
    "replyUrl": {"saml.reply_url"},
    "noGroups": {"saml.claims.groups", "oidc.groups"},
    "noPkce": {"oidc.pkce"},
    "wallsUnmapped": {"dms.walls"},
    "anyonePublic": {"dms.exposure"},
    "shallowGroups": {"dms.hidden"},
    "slowSync": {"dms.acl_sync"},
    "regionWrong": {"residency.tenant", "residency.backup"},
    "usTranscription": {"residency.subprocessor"},
    "retainingVendor": {"residency.retention.subprocessor"},
}
# findings that follow from a planted problem (an unmapped wall also shows as an exposure), so they are not false alarms
ALSO_EXPLAINS = {
    "wallsUnmapped": {"dms.exposure"},
    "anyonePublic": {"dms.anyone_links"},
    "regionWrong": {"residency.subprocessor"},
    "shallowGroups": {"dms.exposure"},  # a wall's excluded group nested deeper than the connector reads
}
AREA = {
    "certExpiring": "sso",
    "weakKey": "sso",
    "replyUrl": "sso",
    "noGroups": "sso",
    "noPkce": "sso",
    "wallsUnmapped": "dms",
    "anyonePublic": "dms",
    "shallowGroups": "dms",
    "slowSync": "dms",
    "regionWrong": "residency",
    "usTranscription": "residency",
    "retainingVendor": "residency",
}
EXPOSURE = {"wallsUnmapped", "anyonePublic"}
RESIDENCY = {"regionWrong", "usTranscription", "retainingVendor"}


def load(name: str) -> dict[str, Any]:
    out: dict[str, Any] = json.loads(Path(f"config/{name}.json").read_text())
    return out


@dataclass
class Customer:
    id: str
    arrival: int
    dms: str
    idp: str
    language: str
    users: int
    acv: float
    residency: str
    questions: list[tuple[str | None, str]]
    planted: set[str]
    hidden_conditional_access: bool
    firewall_weeks: float
    round_trip: float
    security_review_weeks: float
    artifacts: dict[str, Any] = field(default_factory=dict)

    @cached_property
    def findings(self) -> list[Finding]:
        a = self.artifacts
        out: list[Finding] = []
        if self.idp == "saml":
            out += check_saml_metadata(a["saml"], a["sso_expect"], a["reply_urls"])
        else:
            out += check_oidc_discovery(a["oidc"])
        out += audit(a["dms"], a["plan"]).findings
        out += check_residency(Requirement(self.residency), a["tenant"])
        return out

    @cached_property
    def detected(self) -> set[str]:
        checks = {f.check for f in self.findings if f.severity is not Severity.INFO}
        return {k for k in self.planted if FOUND_BY[k] & checks}

    @cached_property
    def false_alarms(self) -> int:
        explained = set().union(*(FOUND_BY[k] | ALSO_EXPLAINS.get(k, set()) for k in self.planted)) if self.planted else set()
        return sum(1 for f in self.findings if f.severity is Severity.BLOCKER and f.check not in explained)


@dataclass
class Outcome:
    customer: str
    arrival: int
    committed: int
    golive: int | None
    acv: float
    incidents: int
    exposure_incidents: int
    questions: int
    wrong_answers: int
    security_turnaround: float
    planted: int
    found_early: int
    tdm: str
    routed: int = 0  # questions sent to the security team


class World:
    def __init__(self, seed: int, cfg: dict[str, Any] | None = None) -> None:
        self.cfg = cfg or load("world")
        self.k = Keyed(seed)
        self.seed = seed
        self.weeks = self.cfg["weeks"]
        self.start = dt.date.fromisoformat(self.cfg["startDate"])
        self.customers = self._customers()

    def date(self, week: float) -> dt.date:
        return self.start + dt.timedelta(days=round(week * 7))

    def _pick(self, r: Any, weights: dict[str, float]) -> str:
        x = r.random()
        for k, v in weights.items():
            x -= v
            if x <= 0:
                return k
        return next(iter(weights))

    def _customers(self) -> list[Customer]:
        c = self.cfg
        out: list[Customer] = []
        n = 0
        for week in range(c["arrivalWeeks"]):
            r = self.k.rng("arrivals", week)
            count = poisson(r, c["arrivalsPerWeek"])
            for _ in range(count):
                out.append(self._customer(f"C{self.seed}-{n:03d}", week, n))
                n += 1
        return out

    def _customer(self, cid: str, week: int, n: int) -> Customer:
        c = self.cfg
        r = self.k.rng("customer", n)
        dms = self._pick(r, c["dms"])
        idp = "oidc" if r.random() < c["oidcShare"] else "saml"
        lang = self._pick(r, c["languages"])
        users = int(min(3000, max(30, c["usersMedian"] * math.exp(c["usersSigma"] * r.gauss(0, 1)))))
        qlo, qhi = c["questions"]
        nq = r.randint(qlo, qhi)
        german = lang == "de" and r.random() < c["germanQuestionShareDach"]
        qs: list[tuple[str | None, str]] = []
        for _ in range(nq):
            gold, variants = BANK[r.randrange(len(BANK))]
            de = [v for v in variants if is_german(v)]
            pool = de if german and de else [v for v in variants if not is_german(v)] or variants
            qs.append((gold, r.choice(pool)))
        iss = c["issues"]
        planted: set[str] = set()
        for key, p in iss.items():
            if key.startswith("hidden"):
                continue
            if key == "noPkce" and idp != "oidc":
                continue
            if key in ("certExpiring", "weakKey", "replyUrl") and idp != "saml":
                continue
            if key == "anyonePublic" and dms != "sharepoint":
                continue
            if r.random() < p:
                planted.add(key)
        residency = self._pick(r, c["residency"])
        cust = Customer(
            id=cid,
            arrival=week,
            dms=dms,
            idp=idp,
            language=lang,
            users=users,
            acv=users * c["acvPerUser"],
            residency=residency,
            questions=qs,
            planted=planted,
            hidden_conditional_access=r.random() < iss["hiddenConditionalAccess"],
            firewall_weeks=r.uniform(*c["firewallWeeks"]) if dms == "imanage_onprem" and r.random() < iss["hiddenFirewall"] else 0.0,
            round_trip=r.uniform(*c["customerRoundTripWeeks"]),
            security_review_weeks=r.uniform(*c["securityReviewWeeks"]),
        )
        cust.artifacts = self._artifacts(cust, r)
        return cust

    def _artifacts(self, cu: Customer, r: Any) -> dict[str, Any]:
        p = cu.planted
        planned_golive = self.date(cu.arrival + 8)
        expiry = planned_golive + dt.timedelta(days=r.randint(5, 50)) if "certExpiring" in p else planned_golive + dt.timedelta(days=r.randint(200, 700))
        acs = f"https://{cu.id.lower()}.workspace.example/sso/acs"
        out: dict[str, Any] = {
            "sso_expect": SsoExpectations(f"urn:workspace:{cu.id}", acs, planned_golive),
            "reply_urls": [f"https://{cu.id.lower()}.workspace.example/sso" if "replyUrl" in p else acs],
        }
        if cu.idp == "saml":
            cert = artifacts.certificate(f"sts.{cu.id.lower()}.example", expiry, bits=1024 if "weakKey" in p else 2048, slot=r.randrange(3))
            claims = ["emailaddress", "name"] + ([] if "noGroups" in p else ["groups"])
            out["saml"] = artifacts.saml_metadata(f"https://sts.{cu.id.lower()}.example/adfs", [cert], f"https://sts.{cu.id.lower()}.example/adfs/ls", claims)
        else:
            out["oidc"] = artifacts.oidc_discovery(cu.id.lower(), pkce="noPkce" not in p, groups="noGroups" not in p, algs=["RS256"])
        walls = r.randint(1, 3) if "wallsUnmapped" in p else r.randint(0, 2)
        out["dms"] = artifacts.dms_export(
            r, users=min(120, max(30, cu.users // 6)), matters=r.randint(25, 60), walls=walls, nested_depth=3, anyone_docs=r.randint(2, 8) if cu.dms == "sharepoint" else 0
        )
        out["plan"] = artifacts.connector_plan(
            walls_mapped="wallsUnmapped" not in p,
            group_depth=1 if "shallowGroups" in p else 8,
            anyone_public="anyonePublic" in p,
            sync_minutes=240 if "slowSync" in p else 15,
        )
        home = {"DE": "germanywestcentral", "EU": "swedencentral", "UK": "uksouth", "EU_UK": "westeurope"}[cu.residency]
        wrong = {"DE": "westeurope", "EU": "eastus", "UK": "westeurope", "EU_UK": "eastus"}[cu.residency]
        region = wrong if "regionWrong" in p else home
        backup = {"germanywestcentral": "germanynorth", "swedencentral": "northeurope", "uksouth": "ukwest", "westeurope": "northeurope", "eastus": "eastus2"}[region]
        out["tenant"] = artifacts.tenant_plan(region, backup, 365, "usTranscription" in p, "retainingVendor" in p)
        return out


def simulate(world: World, design: dict[str, Any], product: dict[str, Any]) -> tuple[list[Outcome], dict[str, float]]:
    """Plays one design through the region's weeks. Returns per-customer outcomes and region totals."""
    c = world.cfg
    k = world.k
    team = [Tdm(t["name"], frozenset(t["skills"]), frozenset(t["languages"]), t["hours"]) for t in c["tdms"]]
    by_name = {t.name: t for t in team}
    agent = (
        QuestionnaireAgent(load_evidence(), world.start, product["questionnaire"]["minScore"], product["questionnaire"]["minMargin"], product["questionnaire"]["minCoverage"])
        if design["agent"]
        else None
    )
    sec = c["securityTeam"]
    sec_queue: list[list[Any]] = []  # [customer id, questions left]
    state: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, Outcome] = {}
    overload_weeks = 0
    tdm_weeks = 0
    lead_hours_used = 0.0
    for week in range(world.weeks):
        # 1. kickoffs
        for cu in [x for x in world.customers if x.arrival == week]:
            r = k.rng("kickoff", cu.arrival, int(cu.id.split("-")[1]))
            committed = week + 6 + (2 if cu.dms == "imanage_onprem" else 0) + (1 if cu.users > 800 else 0) + math.ceil(len(cu.questions) / 80)
            early = design["checks"] == "kickoff"
            blockers = len([f for f in cu.findings if f.severity is Severity.BLOCKER]) if early else 0
            intake = Intake(cu.id, cu.dms, cu.idp, cu.language, cu.users, len(cu.questions), blockers)
            tdm = allocate(intake, team, match=design["match"], max_load_weeks=product["allocation"]["maxLoadWeeks"])
            dms_family = cu.dms.split("_")[0]
            mult = 1.0 if dms_family in tdm.skills else c["skillMismatchFactor"]
            base = c["baseHours"]
            dms_hours = c["dmsHours"][cu.dms] * mult
            hours = base["kickoff"] + base["sso"] + (0 if cu.idp in tdm.skills else 3) + dms_hours + base["pilot"] + base["golive"]
            lang_factor = 1.0 if cu.language in tdm.languages else c["languageMismatchFactor"]
            found_early: set[str] = set()
            wait = week + cu.round_trip * lang_factor
            if early:
                found_early = set(cu.detected)
                hours += c["fix"]["hours"] * len(found_early) + 0.5 * cu.false_alarms
                if found_early:
                    wait = max(wait, week + max(r.uniform(*c["fix"]["earlyWeeks"]) for _ in found_early) * lang_factor)
            # security questionnaire
            wrong = 0
            to_sec = 0
            for i, (gold, q) in enumerate(cu.questions):
                if agent is None:
                    to_sec += 1
                    continue
                a = agent.answer(q)
                if a.status == "to_security":
                    to_sec += 1
                    continue
                hours += c["draftReview"]["minutesPerDraft"] / 60
                if a.evidence_id != gold:
                    caught = k.u("review", cu.arrival, int(cu.id.split("-")[1]), i) < c["draftReview"]["catchesWrong"]
                    if caught:
                        to_sec += 1
                    else:
                        wrong += 1
            sec_queue.append([cu.id, to_sec])
            tdm.load += hours
            tdm.projects.append(cu.id)
            state[cu.id] = {
                "cu": cu,
                "tdm": tdm.name,
                "committed": committed,
                "hours": hours,
                "wait": wait,
                "late_check_done": early,
                "found_early": found_early,
                "q_done": None if to_sec else float(week),
                "security_clear": None if to_sec else week + cu.security_review_weeks,
                "wrong": wrong,
                "to_sec": to_sec,
                "firewall": cu.firewall_weeks,
                "nudged": False,
                "remaining_planted": set(cu.planted) - found_early,
            }
        # 2. the security team works its queue in arrival order
        cap = sec["hoursPerWeek"] * 60 / sec["minutesPerQuestion"]
        for item in sec_queue:
            if cap <= 0:
                break
            take = min(cap, item[1])
            item[1] -= take
            cap -= take
            if item[1] <= 1e-9 and state[item[0]]["q_done"] is None:
                s = state[item[0]]
                s["q_done"] = week + 1.0
                s["security_clear"] = week + 1.0 + s["cu"].security_review_weeks
                rr = k.rng("sec-errors", int(item[0].split("-")[1]))
                s["wrong"] += sum(1 for _ in range(s["to_sec"]) if rr.random() < sec["errorRate"])
        sec_queue = [i for i in sec_queue if i[1] > 1e-9]
        # 3. delivery managers work, earliest promised date first; the lead steps in where a project is at risk
        lead = c["leadStepInHours"] if design["early_warning"] else 0.0
        for t in team:
            active = sorted([s for s in state.values() if s["tdm"] == t.name and s["cu"].id not in outcomes], key=lambda s: (s["committed"], s["cu"].id))
            tdm_weeks += 1
            if t.load > 3 * t.hours:
                overload_weeks += 1
            cap_t = t.hours
            for s in active:
                if cap_t <= 0:
                    break
                if week < s["wait"] and s["hours"] < 6:
                    continue  # nothing left to do until the customer answers
                h = min(cap_t, s["hours"])
                s["hours"] -= h
                t.load -= h
                cap_t -= h
        if lead > 0:
            risky = [
                s
                for s in state.values()
                if s["cu"].id not in outcomes
                and at_risk(
                    week,
                    s["committed"],
                    s["hours"],
                    by_name[s["tdm"]].hours / max(1, len([x for x in state.values() if x["tdm"] == s["tdm"] and x["cu"].id not in outcomes])),
                    max(s["wait"], s["security_clear"] or 0),
                )
            ]
            for s in sorted(risky, key=lambda s: (s["committed"], s["cu"].id)):
                if lead <= 0:
                    break
                h = min(lead, s["hours"])
                s["hours"] -= h
                by_name[s["tdm"]].load -= h
                lead -= h
                lead_hours_used += h
                if not s["nudged"] and s["wait"] > week:
                    # the lead escalates to the customer's sponsor: their IT answers sooner
                    s["wait"] = max(week + 0.0, s["wait"] - 1.0)
                    s["nudged"] = True
        # 4. pre-go-live checks, go-lives and what breaks on the day
        for s in state.values():
            cu = s["cu"]
            if cu.id in outcomes or s["hours"] > 1e-9 or s["security_clear"] is None:
                continue
            ready = max(s["wait"], s["security_clear"], cu.arrival + s["firewall"])
            if week < ready:
                continue
            if not s["late_check_done"]:
                s["late_check_done"] = True
                r = k.rng("late-check", cu.arrival, int(cu.id.split("-")[1]))
                # the desk's checks run late; today a person checks by hand and finds some of it
                found = set(cu.detected) if design["checks"] == "late" else {p for p in sorted(cu.planted) if r.random() < c["manualCheckFinds"][AREA[p]]}
                found &= s["remaining_planted"]
                if found:
                    s["remaining_planted"] -= found
                    lang_factor = 1.0 if cu.language in by_name[s["tdm"]].languages else c["languageMismatchFactor"]
                    s["wait"] = week + max(r.uniform(*c["fix"]["lateWeeks"]) for _ in found) * lang_factor
                    s["hours"] += c["fix"]["hours"] * len(found)
                    by_name[s["tdm"]].load += c["fix"]["hours"] * len(found)
                    continue
            golive = week
            if cu.hidden_conditional_access or "replyUrl" in s["remaining_planted"]:
                golive += 1  # sign-in fails on the day; one more week
                s["remaining_planted"].discard("replyUrl")
            if golive >= world.weeks:
                continue
            r = k.rng("incidents", cu.arrival, int(cu.id.split("-")[1]))
            left = s["remaining_planted"]
            exposure = 1 if (left & EXPOSURE) and r.random() < c["incident"]["exposureNoticed"] else 0
            lockout = 1 if "certExpiring" in left else 0
            residency = 1 if (left & RESIDENCY) and r.random() < c["incident"]["residencyFound"] else 0
            t = by_name[s["tdm"]]
            t.projects.remove(cu.id)
            outcomes[cu.id] = Outcome(
                cu.id,
                cu.arrival,
                s["committed"],
                golive,
                cu.acv,
                exposure + lockout + residency,
                exposure,
                len(cu.questions),
                s["wrong"],
                (s["q_done"] or week) - cu.arrival,
                len(cu.planted),
                len(s["found_early"]),
                s["tdm"],
                s["to_sec"],
            )
    for s in state.values():
        cu = s["cu"]
        if cu.id not in outcomes:
            outcomes[cu.id] = Outcome(
                cu.id,
                cu.arrival,
                s["committed"],
                None,
                cu.acv,
                0,
                0,
                len(cu.questions),
                s["wrong"],
                (s["q_done"] or world.weeks) - cu.arrival,
                len(cu.planted),
                len(s["found_early"]),
                s["tdm"],
                s["to_sec"],
            )
    totals = {"overload_share": overload_weeks / max(tdm_weeks, 1), "lead_hours": lead_hours_used}
    return [outcomes[x.id] for x in world.customers], totals
