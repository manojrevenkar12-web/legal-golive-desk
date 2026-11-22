import random

from golive.dms import IntegrationPlan, audit
from golive.findings import Severity
from golive.world.artifacts import dms_export


def firm():
    """Two practices, a nested group, a walled matter, and an 'anyone' link."""
    return {
        "users": ["ann", "bob", "cat", "dan"],
        "groups": {"g-corp": ["ann", "g-corp-1"], "g-corp-1": ["bob"], "g-lit": ["cat", "g-lit-1"], "g-lit-1": ["dan"]},
        "containers": [
            {"id": "M1", "public": False, "acl": ["g-corp"]},
            {"id": "M2", "public": False, "acl": ["g-corp", "g-lit"]},
        ],
        "documents": [
            {"id": "D1", "container": "M1", "acl": None, "links": ["anyone"]},
            {"id": "D2", "container": "M2", "acl": None, "links": []},
        ],
        "walls": [{"id": "W1", "containers": ["M2"], "excluded": ["g-lit"]}],
    }


def test_correct_plan_exposes_nothing():
    a = audit(firm(), IntegrationPlan())
    assert a.exposed_pairs == 0 and a.hidden_pairs == 0
    assert not [f for f in a.findings if f.severity is Severity.BLOCKER]


def test_unmapped_wall_exposes_the_walled_practice():
    a = audit(firm(), IntegrationPlan(walls_mapped=False))
    assert a.exposed_pairs == 2  # cat and dan would find D2
    assert a.causes == {"ethical wall not mapped": 2}
    assert {"dms.exposure", "dms.walls"} <= {f.check for f in a.findings}


def test_service_account_index_exposes_everything_the_dms_denies():
    a = audit(firm(), IntegrationPlan(mode="service_account"))
    assert a.causes == {"one index for every user": a.exposed_pairs}
    assert a.exposed_pairs == 4  # cat, dan on D1; cat, dan on D2


def test_anyone_link_treated_as_public_is_a_blocker():
    a = audit(firm(), IntegrationPlan(anyone_links_public=True))
    assert a.causes == {"'anyone' link treated as public": 2}
    assert any(f.check == "dms.anyone_links" and f.severity is Severity.BLOCKER for f in a.findings)


def test_shallow_groups_hide_documents_from_nested_members():
    a = audit(firm(), IntegrationPlan(group_depth=1))
    assert a.exposed_pairs == 0 and a.hidden_pairs == 2  # bob, nested in corp, loses D1 and D2
    assert any(f.check == "dms.hidden" for f in a.findings)


def test_shallow_groups_let_a_nested_member_of_a_walled_off_group_through():
    e = firm()
    e["containers"][1]["acl"].append("dan")  # dan is also granted the matter directly; only the wall denies him
    a = audit(e, IntegrationPlan(group_depth=1))
    assert a.causes == {"wall's excluded group nested deeper than the connector reads": 1}
    assert a.sample[0] == {"user": "dan", "document": "D2", "matter": "M2", "cause": a.sample[0]["cause"]}


def test_slow_sync_warns():
    assert any(f.check == "dms.acl_sync" for f in audit(firm(), IntegrationPlan(acl_sync_minutes=240)).findings)


def test_generated_firm_with_a_correct_plan_is_clean():
    e = dms_export(random.Random(4), users=80, matters=30, walls=3, nested_depth=3, anyone_docs=2)
    a = audit(e, IntegrationPlan(group_depth=8))
    assert a.exposed_pairs == 0 and a.hidden_pairs == 0
    assert audit(e, IntegrationPlan(walls_mapped=False)).exposed_pairs > 0
