import datetime as dt

from golive.findings import Severity
from golive.sso import SsoExpectations, check_oidc_discovery, check_saml_metadata
from golive.world.artifacts import certificate, oidc_discovery, saml_metadata

GO = dt.date(2026, 12, 1)
EXP = SsoExpectations("https://ws.example/sp", "https://ws.example/acs", GO)
CLAIMS = ["email", "groups"]


def checks(findings, severity=None):
    return {f.check for f in findings if severity is None or f.severity is severity}


def meta(*certs, claims=CLAIMS, url="https://idp.firm.example/sso"):
    return saml_metadata("https://idp.firm.example", list(certs), url, claims)


def test_healthy_metadata_has_no_blockers():
    f = check_saml_metadata(meta(certificate("idp", GO + dt.timedelta(days=400))), EXP, [EXP.acs_url])
    assert not checks(f, Severity.BLOCKER)
    assert not checks(f, Severity.WARN)


def test_certificate_expiring_soon_after_golive_is_flagged_with_days():
    f = check_saml_metadata(meta(certificate("idp", GO + dt.timedelta(days=20))), EXP)
    w = [x for x in f if x.check == "saml.cert.expiring"]
    assert w and "20 days after go-live" in w[0].message


def test_certificate_expired_before_golive_blocks():
    f = check_saml_metadata(meta(certificate("idp", GO - dt.timedelta(days=1))), EXP)
    assert "saml.cert.expired" in checks(f, Severity.BLOCKER)


def test_rollover_in_progress_downgrades_the_old_certificate():
    old, new = certificate("idp", GO + dt.timedelta(days=10)), certificate("idp", GO + dt.timedelta(days=700), slot=1)
    f = check_saml_metadata(meta(old, new), EXP)
    assert "saml.cert.expiring" in checks(f, Severity.INFO)
    assert "saml.cert.expiring" not in checks(f, Severity.WARN)


def test_weak_key_blocks():
    f = check_saml_metadata(meta(certificate("idp", GO + dt.timedelta(days=400), bits=1024)), EXP)
    assert "saml.cert.weak_key" in checks(f, Severity.BLOCKER)


def test_reply_url_mismatch_blocks_and_names_the_fix():
    f = check_saml_metadata(meta(certificate("idp", GO + dt.timedelta(days=400))), EXP, ["https://old.example/acs"])
    r = [x for x in f if x.check == "saml.reply_url"]
    assert r and r[0].severity is Severity.BLOCKER and EXP.acs_url in r[0].fix


def test_missing_claims():
    f = check_saml_metadata(meta(certificate("idp", GO + dt.timedelta(days=400)), claims=["name"]), EXP)
    assert {"saml.claims.email", "saml.claims.groups"} <= checks(f)


def test_plain_http_sign_in_blocks():
    f = check_saml_metadata(meta(certificate("idp", GO + dt.timedelta(days=400)), url="http://idp.firm.example/sso"), EXP)
    assert "saml.sso.https" in checks(f, Severity.BLOCKER)


def test_hostile_xml_is_refused_not_expanded():
    bomb = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">]><x>&b;</x>'
    assert checks(check_saml_metadata(bomb, EXP)) == {"saml.metadata.unreadable"}
    assert checks(check_saml_metadata("not xml", EXP)) == {"saml.metadata.unreadable"}


def test_oidc_healthy_and_problems():
    assert not check_oidc_discovery(oidc_discovery("firm", pkce=True, groups=True, algs=["RS256"]))
    bad = check_oidc_discovery(oidc_discovery("firm", pkce=False, groups=False, algs=["HS256", "none"]))
    assert {"oidc.pkce", "oidc.groups"} <= checks(bad, Severity.WARN)
    assert {"oidc.signing_alg", "oidc.alg_none"} <= checks(bad, Severity.BLOCKER)


def test_oidc_issuer_must_be_the_agreed_tenant():
    doc = oidc_discovery("other", pkce=True, groups=True, algs=["RS256"])
    assert "oidc.issuer_mismatch" in checks(check_oidc_discovery(doc, "https://login.firm.example/firm/v2.0"))
