"""The delivery lead's engine: who takes which go-live, which projects are at risk, what the region reports.

Everything here reads what delivery can see at kickoff: the customer's DMS, identity provider, language, size and
security-review size, and the findings of the readiness checks. Nothing reads how the project will really go.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intake:
    customer: str
    dms: str  # imanage_cloud, imanage_onprem, sharepoint, netdocuments
    idp: str  # saml, oidc
    language: str
    users: int
    questions: int
    blockers: int  # blocker findings from the readiness checks at kickoff (0 when checks have not run)


@dataclass
class Tdm:
    name: str
    skills: frozenset[str]
    languages: frozenset[str]
    hours: float  # project hours a week
    load: float = 0.0  # hours of open work assigned
    projects: list[str] = field(default_factory=list)


def complexity(i: Intake) -> float:
    """Expected delivery hours from what is known at kickoff."""
    dms = {"imanage_onprem": 30.0, "imanage_cloud": 14.0, "sharepoint": 12.0, "netdocuments": 12.0}[i.dms]
    return 6 + 8 + dms + 16 + 6 + min(i.users / 100, 8) + 3 * i.blockers + i.questions / 40


def allocate(i: Intake, team: list[Tdm], match: bool, max_load_weeks: float = 2.5) -> Tdm:
    """Picks the delivery manager for a new go-live.

    With [match], the integration skill and the customer's language count and nobody is loaded past [max_load_weeks]
    weeks of work unless everyone is; without it, the manager with the fewest projects takes it, as many teams do.
    """
    if not match:
        return min(team, key=lambda t: (len(t.projects), t.name))
    need = {i.dms.split("_")[0], i.idp}

    def score(t: Tdm) -> tuple[float, str]:
        weeks = (t.load + complexity(i)) / t.hours
        s = 3.0 * len(need & t.skills) + (2.0 if i.language in t.languages else 0.0) - 1.5 * weeks
        if weeks > max_load_weeks:
            s -= 10
        return (-s, t.name)

    return min(team, key=score)


def at_risk(week: int, committed: int, remaining_hours: float, weekly_hours: float, waiting_until: int) -> bool:
    """A project is at risk when, at its current pace, it lands after the date promised to the customer."""
    pace = max(weekly_hours, 1.0)
    projected = max(week + remaining_hours / pace, waiting_until)
    return projected > committed
