import datetime as dt
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from golive.eval import cli
from golive.eval.report import END, START, block, gate
from golive.service.app import app
from golive.world.artifacts import certificate, oidc_discovery, saml_metadata

DEV = json.loads(Path("reports/dev.json").read_text())
GATES = json.loads(Path("config/gates.json").read_text())


def test_committed_dev_report_passes_its_gates():
    assert all(ok for _, ok, _ in gate(DEV, GATES))


def test_a_worse_desk_fails_the_gates():
    bad = json.loads(json.dumps(DEV))
    bad["designs"]["desk"]["exposure_per_10_golives"] = [0.4, 0.1, 0.8]
    assert not all(ok for _, ok, _ in gate(bad, GATES))


def test_readme_block_is_generated_between_markers():
    b = block(DEV, None, GATES)
    assert b.startswith(START) and b.endswith(END) and "held-out seeds have not been run" in b


def test_heldout_runs_once(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "LOCK", tmp_path / "heldout.lock")
    monkeypatch.setattr(cli, "REPORTS", tmp_path)
    monkeypatch.setattr(cli, "run", lambda s: {**DEV, "set": s})
    (tmp_path / "dev.json").write_text(json.dumps(DEV))
    monkeypatch.setattr("golive.eval.cli.write_readme", lambda *a: True)
    assert cli.main(["heldout"]) == 0
    assert (tmp_path / "heldout.json").exists()
    assert cli.main(["heldout"]) == 2


client = TestClient(app)


def test_saml_endpoint():
    go = dt.date(2026, 12, 1)
    xml = saml_metadata("https://idp.x", [certificate("idp", go + dt.timedelta(days=15))], "https://idp.x/sso", ["email", "groups"])
    r = client.post(
        "/checks/sso/saml", json={"metadata_xml": xml, "sp_entity_id": "sp", "acs_url": "https://ws/acs", "go_live": go.isoformat(), "configured_reply_urls": ["https://ws/acs"]}
    )
    assert r.status_code == 200 and r.json()["ready"] is True
    assert [f["check"] for f in r.json()["findings"]] == ["saml.cert.expiring"]


def test_oidc_endpoint():
    r = client.post("/checks/sso/oidc", json={"discovery": oidc_discovery("f", pkce=True, groups=True, algs=["none"])})
    assert r.json()["ready"] is False


def test_dms_endpoint_and_bad_input():
    export = {
        "users": ["a", "b"],
        "groups": {},
        "containers": [{"id": "M", "public": False, "acl": ["a"]}],
        "documents": [{"id": "D", "container": "M", "acl": None, "links": []}],
        "walls": [],
    }
    r = client.post("/checks/dms", json={"export": export, "mode": "service_account"})
    assert r.status_code == 200 and r.json()["audit"]["exposed_pairs"] == 1
    assert client.post("/checks/dms", json={"export": {"users": []}}).status_code == 422


def test_residency_endpoint():
    r = client.post("/checks/residency", json={"residency": "DE", "tenant": {"region": "westeurope", "backup_region": "germanynorth", "retention_days": 30}})
    assert [f["check"] for f in r.json()["findings"]] == ["residency.tenant"]


def test_questionnaire_endpoint_and_limits():
    r = client.post("/questionnaires/answer", json={"questions": ["Do you hold ISO 27001 certification?", "Do you hold cyber insurance?"], "today": "2026-11-23"})
    assert (r.json()["drafted"], r.json()["to_security"]) == (1, 1)
    assert client.post("/questionnaires/answer", json={"questions": ["x" * 3000]}).status_code == 413
    assert client.post("/questionnaires/answer", json={"questions": ["q"] * 501}).status_code == 422


def test_assign_endpoint():
    body = {
        "intake": {"customer": "C", "dms": "sharepoint", "idp": "oidc", "language": "en", "users": 100, "questions": 40, "blockers": 0},
        "team": [{"name": "ana", "skills": ["imanage"], "languages": ["de"]}, {"name": "ben", "skills": ["sharepoint", "oidc"], "languages": ["en"]}],
    }
    assert client.post("/delivery/assign", json=body).json()["manager"] == "ben"


@pytest.mark.parametrize("path", ["/checks/sso/saml", "/checks/residency"])
def test_malformed_bodies_are_422(path):
    assert client.post(path, json={}).status_code == 422
