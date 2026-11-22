from golive.delivery import Intake, Tdm, allocate, at_risk, complexity
from golive.findings import Severity
from golive.residency import Requirement, Subprocessor, TenantPlan, check


def intake(**kw):
    base = {"customer": "C1", "dms": "imanage_cloud", "idp": "saml", "language": "de", "users": 300, "questions": 120, "blockers": 0}
    return Intake(**{**base, **kw})


def team():
    return [
        Tdm("ana", frozenset({"imanage", "saml"}), frozenset({"de", "en"}), 22),
        Tdm("ben", frozenset({"sharepoint", "oidc"}), frozenset({"en"}), 22),
    ]


def test_on_prem_imanage_and_blockers_cost_more():
    assert complexity(intake(dms="imanage_onprem")) > complexity(intake())
    assert complexity(intake(blockers=4)) == complexity(intake()) + 12


def test_matching_picks_the_manager_with_the_skills_and_language():
    assert allocate(intake(), team(), match=True).name == "ana"
    assert allocate(intake(dms="sharepoint", idp="oidc", language="en"), team(), match=True).name == "ben"


def test_matching_does_not_overload_the_best_fit():
    t = team()
    t[0].load = 22 * 3  # three weeks of work already
    assert allocate(intake(), t, match=True, max_load_weeks=3.0).name == "ben"


def test_without_matching_the_fewest_projects_take_it():
    t = team()
    t[0].projects = ["x"]
    assert allocate(intake(), t, match=False).name == "ben"


def test_at_risk_uses_pace_and_waiting():
    assert not at_risk(week=2, committed=8, remaining_hours=40, weekly_hours=10, waiting_until=0)
    assert at_risk(week=2, committed=8, remaining_hours=80, weekly_hours=10, waiting_until=0)
    assert at_risk(week=2, committed=8, remaining_hours=10, weekly_hours=10, waiting_until=9)


def plan(region="germanywestcentral", backup="germanynorth", subs=()):
    return TenantPlan(region, backup, 365, tuple(subs))


def blockers(findings):
    return {f.check for f in findings if f.severity is Severity.BLOCKER}


def test_german_tenant_meets_a_german_requirement():
    assert not check(Requirement("DE"), plan())


def test_eu_backup_breaks_a_germany_only_contract():
    assert blockers(check(Requirement("DE"), plan(backup="westeurope"))) == {"residency.backup"}


def test_us_transcription_and_retaining_vendor_are_caught():
    subs = [Subprocessor("Speech", "transcription", "eastus", True), Subprocessor("Search", "search", "westeurope", True, zero_retention=False)]
    assert blockers(check(Requirement("EU"), plan(subs=subs))) == {"residency.subprocessor", "residency.retention.subprocessor"}


def test_logs_without_content_may_leave_the_region():
    assert not check(Requirement("DE"), plan(subs=[Subprocessor("Logs", "ops logs", "westeurope", False)]))


def test_unknown_region_warns():
    f = check(Requirement("ANY"), plan(subs=[Subprocessor("X", "y", "moon-1", False)]))
    assert {x.check for x in f} == {"residency.unknown_region"}
