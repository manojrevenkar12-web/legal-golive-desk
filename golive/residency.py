"""Data residency and subprocessors, checked against what the customer's contract and DPA require."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from golive.findings import Finding, Severity

# region -> jurisdiction; Azure region names, since the workspace runs on Azure
JURISDICTION = {
    "germanywestcentral": "DE",
    "germanynorth": "DE",
    "westeurope": "EU",
    "northeurope": "EU",
    "swedencentral": "EU",
    "francecentral": "EU",
    "uksouth": "UK",
    "ukwest": "UK",
    "eastus": "US",
    "eastus2": "US",
    "westus3": "US",
}
# which jurisdictions satisfy each requirement
ALLOWED = {"DE": {"DE"}, "EU": {"DE", "EU"}, "UK": {"UK"}, "EU_UK": {"DE", "EU", "UK"}, "ANY": {"DE", "EU", "UK", "US"}}


@dataclass(frozen=True)
class Requirement:
    residency: str = "EU"  # DE, EU, UK, EU_UK, ANY
    zero_retention_models: bool = True  # model providers keep no customer content
    max_retention_days: int = 365
    no_training_on_content: bool = True


@dataclass(frozen=True)
class Subprocessor:
    name: str
    purpose: str
    region: str
    processes_content: bool
    zero_retention: bool = True
    trains_on_content: bool = False


@dataclass(frozen=True)
class TenantPlan:
    region: str
    backup_region: str
    retention_days: int
    subprocessors: tuple[Subprocessor, ...] = field(default_factory=tuple)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> TenantPlan:
        return TenantPlan(d["region"], d["backup_region"], int(d["retention_days"]), tuple(Subprocessor(**s) for s in d.get("subprocessors", [])))


def check(req: Requirement, plan: TenantPlan) -> list[Finding]:
    ok = ALLOWED[req.residency]
    out: list[Finding] = []

    def where(region: str) -> str:
        return JURISDICTION.get(region, "UNKNOWN")

    if where(plan.region) not in ok:
        out.append(
            Finding(
                "residency.tenant",
                Severity.BLOCKER,
                f"The tenant would run in {plan.region} ({where(plan.region)}), outside the required {req.residency}.",
                "Provision the tenant in a region inside the required jurisdiction.",
            )
        )
    if where(plan.backup_region) not in ok:
        out.append(
            Finding(
                "residency.backup",
                Severity.BLOCKER,
                f"Backups would be kept in {plan.backup_region} ({where(plan.backup_region)}).",
                "Pair the tenant with a backup region inside the required jurisdiction.",
            )
        )
    if plan.retention_days > req.max_retention_days:
        out.append(
            Finding(
                "residency.retention",
                Severity.BLOCKER,
                f"Content is kept {plan.retention_days} days; the contract allows {req.max_retention_days}.",
                "Set the tenant's retention to the contracted limit.",
            )
        )
    for s in plan.subprocessors:
        if s.processes_content and where(s.region) not in ok:
            out.append(
                Finding(
                    "residency.subprocessor",
                    Severity.BLOCKER,
                    f"{s.name} ({s.purpose}) processes content in {s.region} ({where(s.region)}).",
                    f"Route {s.purpose} to an in-region deployment, or get the customer's written approval.",
                )
            )
        if s.processes_content and req.zero_retention_models and not s.zero_retention:
            out.append(
                Finding("residency.retention.subprocessor", Severity.BLOCKER, f"{s.name} keeps content after processing.", "Use the zero-retention endpoint for this subprocessor.")
            )
        if s.processes_content and req.no_training_on_content and s.trains_on_content:
            out.append(Finding("residency.training", Severity.BLOCKER, f"{s.name} may train on customer content.", "Use an endpoint contractually excluded from training."))
        if where(s.region) == "UNKNOWN":
            out.append(
                Finding("residency.unknown_region", Severity.WARN, f"{s.name} runs in an unlisted region ({s.region}).", "Confirm the region and add it to the subprocessor list.")
            )
    return out
