"""A finding is what a readiness check tells the customer's IT team: how bad it is and what to change."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    BLOCKER = "blocker"  # go-live cannot happen until it is fixed
    WARN = "warn"  # go-live can happen, with a dated follow-up
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    check: str
    severity: Severity
    message: str
    fix: str

    def as_dict(self) -> dict[str, str]:
        return {"check": self.check, "severity": self.severity.value, "message": self.message, "fix": self.fix}


def blockers(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity is Severity.BLOCKER]
