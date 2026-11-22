"""SSO readiness: a customer's SAML IdP metadata or OIDC discovery document, checked before go-live.

The checks are the ones that cause lockouts and failed logins in the first weeks: a signing certificate that expires
soon after go-live, a weak key or digest, a reply URL that does not match the tenant, no group claim for role mapping,
no PKCE. Metadata is untrusted input and is parsed with defusedxml.
"""

from __future__ import annotations

import base64
import datetime as dt
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from defusedxml import ElementTree

from golive.findings import Finding, Severity

NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
}
REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
GROUP_CLAIMS = {"groups", "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups", "memberof"}
EMAIL_CLAIMS = {"email", "mail", "emailaddress", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"}


@dataclass(frozen=True)
class SsoExpectations:
    """What the workspace tenant expects from the customer's IdP."""

    sp_entity_id: str
    acs_url: str
    go_live: dt.date
    cert_margin_days: int = 60
    needs_groups: bool = True


def _https(url: str) -> bool:
    return urlparse(url).scheme == "https"


def _cert_findings(cert: x509.Certificate, exp: SsoExpectations, i: int) -> list[Finding]:
    out: list[Finding] = []
    not_after = cert.not_valid_after_utc.date()
    label = f"signing certificate {i + 1} (valid until {not_after.isoformat()})"
    if not_after < exp.go_live:
        out.append(
            Finding("saml.cert.expired", Severity.BLOCKER, f"The {label} expires before go-live.", "Roll over to a new signing certificate in the IdP and send updated metadata.")
        )
    elif (not_after - exp.go_live).days < exp.cert_margin_days:
        days = (not_after - exp.go_live).days
        out.append(
            Finding(
                "saml.cert.expiring",
                Severity.WARN,
                f"The {label} expires {days} days after go-live; every user is locked out on that day unless it is rolled over.",
                "Agree a rollover date now and publish the new certificate in metadata ahead of it.",
            )
        )
    key = cert.public_key()
    if isinstance(key, rsa.RSAPublicKey) and key.key_size < 2048:
        out.append(Finding("saml.cert.weak_key", Severity.BLOCKER, f"The {label} uses a {key.key_size}-bit RSA key.", "Issue a certificate with an RSA key of at least 2048 bits."))
    elif not isinstance(key, rsa.RSAPublicKey | ec.EllipticCurvePublicKey):
        out.append(Finding("saml.cert.key_type", Severity.WARN, f"The {label} uses an unusual key type.", "Use RSA 2048+ or an elliptic-curve key."))
    algo = cert.signature_hash_algorithm
    if isinstance(algo, hashes.SHA1):
        out.append(Finding("saml.cert.sha1", Severity.WARN, f"The {label} is signed with SHA-1.", "Reissue it signed with SHA-256."))
    return out


def check_saml_metadata(xml_text: str, exp: SsoExpectations, configured_reply_urls: list[str] | None = None) -> list[Finding]:
    """Checks IdP metadata. [configured_reply_urls] are the reply (ACS) URLs set on the customer's enterprise app, if known."""
    try:
        root = ElementTree.fromstring(xml_text)
    except Exception as e:
        return [
            Finding("saml.metadata.unreadable", Severity.BLOCKER, f"The metadata could not be read: {type(e).__name__}.", "Export the federation metadata XML again from the IdP.")
        ]
    out: list[Finding] = []
    if not root.get("entityID"):
        out.append(Finding("saml.entity_id", Severity.BLOCKER, "The metadata has no entityID.", "Export the IdP's federation metadata, not an app manifest."))
    idp = root.find("md:IDPSSODescriptor", NS)
    if idp is None:
        return [*out, Finding("saml.idp_descriptor", Severity.BLOCKER, "The metadata describes no identity provider.", "Export the IdP's federation metadata.")]

    certs: list[x509.Certificate] = []
    for kd in idp.findall("md:KeyDescriptor", NS):
        if kd.get("use") not in (None, "signing"):
            continue
        for el in kd.findall(".//ds:X509Certificate", NS):
            try:
                certs.append(x509.load_der_x509_certificate(base64.b64decode("".join((el.text or "").split()))))
            except Exception:
                out.append(Finding("saml.cert.unreadable", Severity.BLOCKER, "A signing certificate in the metadata could not be decoded.", "Re-export the metadata."))
    if not certs:
        out.append(Finding("saml.cert.missing", Severity.BLOCKER, "The metadata has no signing certificate.", "Publish the IdP signing certificate in metadata."))
    horizon = exp.go_live + dt.timedelta(days=exp.cert_margin_days)
    rolled_over = any(c.not_valid_after_utc.date() >= horizon for c in certs)
    for i, c in enumerate(certs):
        for f in _cert_findings(c, exp, i):
            if rolled_over and f.check in ("saml.cert.expired", "saml.cert.expiring"):
                # a newer certificate is already published next to it: the rollover is under way
                f = Finding(f.check, Severity.INFO, f.message + " A newer certificate is already published.", "Remove the old certificate after the rollover date.")
            out.append(f)

    sso = idp.findall("md:SingleSignOnService", NS)
    usable = [s for s in sso if s.get("Binding") in (REDIRECT, POST)]
    if not usable:
        out.append(
            Finding("saml.sso.binding", Severity.BLOCKER, "No SingleSignOnService with an HTTP-Redirect or HTTP-POST binding.", "Enable the Redirect or POST binding on the IdP.")
        )
    for s in usable:
        if not _https(s.get("Location", "")):
            out.append(Finding("saml.sso.https", Severity.BLOCKER, f"The sign-in endpoint {s.get('Location')} is not HTTPS.", "Publish an HTTPS sign-in endpoint."))

    formats = {(n.text or "").strip() for n in idp.findall("md:NameIDFormat", NS)}
    if formats and not any(f.endswith(("emailAddress", "persistent")) for f in formats):
        out.append(
            Finding(
                "saml.nameid",
                Severity.WARN,
                "The IdP offers no email or persistent NameID format.",
                "Send the user's email address as NameID, or a persistent identifier with an email claim.",
            )
        )

    attrs = {(a.get("Name") or "").lower() for a in idp.findall("saml:Attribute", NS)}
    if attrs and not attrs & EMAIL_CLAIMS:
        out.append(Finding("saml.claims.email", Severity.BLOCKER, "The IdP does not release an email claim.", "Add the email address to the claims released to the workspace."))
    if exp.needs_groups and attrs and not attrs & GROUP_CLAIMS:
        out.append(
            Finding(
                "saml.claims.groups",
                Severity.WARN,
                "The IdP does not release a groups claim, so roles cannot follow practice groups.",
                "Release a groups claim, or provision groups with SCIM.",
            )
        )

    if configured_reply_urls is not None and exp.acs_url not in configured_reply_urls:
        out.append(
            Finding(
                "saml.reply_url",
                Severity.BLOCKER,
                f"The enterprise app's reply URLs do not include {exp.acs_url}; sign-in will fail with a reply URL mismatch.",
                f"Add {exp.acs_url} as a reply URL and {exp.sp_entity_id} as the identifier.",
            )
        )
    return out


def check_oidc_discovery(doc: dict[str, Any], expected_issuer: str | None = None) -> list[Finding]:
    """Checks an OpenID Connect discovery document (/.well-known/openid-configuration)."""
    out: list[Finding] = []
    issuer = str(doc.get("issuer", ""))
    if not issuer or not _https(issuer):
        out.append(Finding("oidc.issuer", Severity.BLOCKER, "The issuer is missing or not HTTPS.", "Use the tenant's HTTPS issuer URL."))
    elif expected_issuer and issuer.rstrip("/") != expected_issuer.rstrip("/"):
        out.append(
            Finding(
                "oidc.issuer_mismatch",
                Severity.BLOCKER,
                f"The issuer {issuer} is not the tenant agreed at kickoff ({expected_issuer}).",
                "Point the workspace at the customer's own tenant.",
            )
        )
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not _https(str(doc.get(key, ""))):
            out.append(Finding(f"oidc.{key}", Severity.BLOCKER, f"{key} is missing or not HTTPS.", "Use the tenant's discovery document."))
    if "code" not in doc.get("response_types_supported", []):
        out.append(Finding("oidc.code_flow", Severity.BLOCKER, "The authorization code flow is not supported.", "Enable the authorization code flow for the app."))
    if "S256" not in doc.get("code_challenge_methods_supported", []):
        out.append(Finding("oidc.pkce", Severity.WARN, "PKCE with S256 is not advertised.", "Enable PKCE (S256) for the app registration."))
    algs = set(doc.get("id_token_signing_alg_values_supported", []))
    if not algs & {"RS256", "ES256", "PS256"}:
        out.append(Finding("oidc.signing_alg", Severity.BLOCKER, f"ID tokens are not signed with an asymmetric algorithm ({sorted(algs)}).", "Sign ID tokens with RS256 or ES256."))
    if "none" in algs:
        out.append(Finding("oidc.alg_none", Severity.BLOCKER, "Unsigned ID tokens ('none') are allowed.", "Disable the 'none' algorithm."))
    if not {"openid", "email"} <= set(doc.get("scopes_supported", ["openid", "email"])):
        out.append(Finding("oidc.scopes", Severity.BLOCKER, "The openid and email scopes are not both supported.", "Allow the openid and email scopes."))
    claims = set(doc.get("claims_supported", []))
    if claims and "groups" not in claims:
        out.append(
            Finding("oidc.groups", Severity.WARN, "No groups claim is advertised, so roles cannot follow practice groups.", "Add a groups claim, or provision groups with SCIM.")
        )
    return out
