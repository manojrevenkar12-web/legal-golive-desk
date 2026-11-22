"""Real configuration artifacts for a simulated customer, generated from the issues the world planted in them.

The world decides which problems a customer's setup has; this module writes the files a customer's IT team would send
(SAML metadata with a real certificate, an OIDC discovery document, a DMS permission export with the connector plan,
the tenant plan) with exactly those problems in them. The product's checkers then read the files, not the flags.
"""

from __future__ import annotations

import base64
import datetime as dt
import itertools
import random
from functools import lru_cache
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from golive.dms import IntegrationPlan
from golive.residency import Subprocessor, TenantPlan


@lru_cache(maxsize=4)
def _key(bits: int, slot: int) -> rsa.RSAPrivateKey:
    # key generation is slow; a few keys are reused across customers, certificates are not
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def certificate(cn: str, not_after: dt.date, bits: int = 2048, slot: int = 0) -> bytes:
    key = _key(bits, slot)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    start = dt.datetime.combine(not_after - dt.timedelta(days=730), dt.time(), tzinfo=dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(dt.datetime.combine(not_after, dt.time(12), tzinfo=dt.UTC))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.DER)


def saml_metadata(entity: str, certs: list[bytes], sso_url: str, claims: list[str], nameid: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress") -> str:
    keys = "".join(
        f'<md:KeyDescriptor use="signing"><ds:KeyInfo><ds:X509Data><ds:X509Certificate>{base64.b64encode(c).decode()}</ds:X509Certificate></ds:X509Data></ds:KeyInfo></md:KeyDescriptor>'
        for c in certs
    )
    attrs = "".join(f'<saml:Attribute Name="{c}"/>' for c in claims)
    return (
        '<?xml version="1.0"?>'
        '<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" '
        f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" entityID="{entity}">'
        '<md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
        f"{keys}<md:NameIDFormat>{nameid}</md:NameIDFormat>"
        f'<md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="{sso_url}"/>'
        f"{attrs}</md:IDPSSODescriptor></md:EntityDescriptor>"
    )


def oidc_discovery(tenant: str, pkce: bool, groups: bool, algs: list[str]) -> dict[str, Any]:
    base = f"https://login.{tenant}.example/{tenant}/v2.0"
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "jwks_uri": f"{base}/keys",
        "response_types_supported": ["code", "id_token"],
        "code_challenge_methods_supported": ["S256"] if pkce else [],
        "id_token_signing_alg_values_supported": algs,
        "scopes_supported": ["openid", "email", "profile"],
        "claims_supported": ["sub", "email", "name"] + (["groups"] if groups else []),
    }


def dms_export(r: random.Random, users: int, matters: int, walls: int, nested_depth: int, anyone_docs: int) -> dict[str, Any]:
    """A firm's DMS: practice groups nested [nested_depth] deep, matters with group ACLs, some walled off."""
    us = [f"u{i:04d}" for i in range(users)]
    practices = ["corp", "lit", "ip", "tax", "re", "emp"]
    groups: dict[str, list[str]] = {}
    for p in practices:
        members = [u for u in us if r.random() < 1 / len(practices) * 1.4]
        # a chain of nested groups: g-p -> g-p-1 -> ... ; the deepest level holds part of the practice
        chain = [f"g-{p}", *(f"g-{p}-{k}" for k in range(1, nested_depth + 1))]
        for a, b in itertools.pairwise(chain):
            groups[a] = [*groups.get(a, []), b]
        split = len(members) // 2
        groups.setdefault(chain[0], []).extend(members[:split])
        groups.setdefault(chain[-1], []).extend(members[split:])
    containers: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    for m in range(matters):
        p = practices[m % len(practices)]
        public = r.random() < 0.08
        containers.append({"id": f"M-{m:04d}", "public": public, "acl": [f"g-{p}"] + ([f"g-{r.choice(practices)}"] if r.random() < 0.2 else [])})
        for k in range(r.randint(4, 12)):
            own = r.random() < 0.06
            documents.append({"id": f"D-{m:04d}-{k:02d}", "container": f"M-{m:04d}", "acl": [r.choice(us)] if own else None, "links": []})
    for d in r.sample(documents, min(anyone_docs, len(documents))):
        d["links"] = ["anyone"]
    wall_list = []
    for w in range(walls):
        target = r.choice(containers)
        target["public"] = False
        excluded = r.choice([g for g in groups if g.startswith("g-") and g.count("-") == 1 and g not in target["acl"]] or ["g-lit"])
        wall_list.append({"id": f"W-{w}", "containers": [target["id"]], "excluded": [excluded]})
        # the walled-off practice still holds the matter through a cross-practice grant, which only the wall denies
        target["acl"].append(excluded)
    return {"users": us, "groups": groups, "containers": containers, "documents": documents, "walls": wall_list}


def connector_plan(walls_mapped: bool, group_depth: int, anyone_public: bool, sync_minutes: int) -> IntegrationPlan:
    return IntegrationPlan(mode="per_user", group_depth=group_depth, walls_mapped=walls_mapped, anyone_links_public=anyone_public, acl_sync_minutes=sync_minutes)


def tenant_plan(region: str, backup: str, retention: int, us_transcription: bool, retaining_vendor: bool) -> TenantPlan:
    subs = [
        Subprocessor("Azure OpenAI", "model inference", region, True),
        Subprocessor("Anthropic via Azure", "model inference", region, True),
        Subprocessor("Datadog", "operational logs", "westeurope", False),
    ]
    if us_transcription:
        subs.append(Subprocessor("Speech service", "audio transcription", "eastus", True))
    if retaining_vendor:
        subs.append(Subprocessor("Search vendor", "semantic search", region, True, zero_retention=False))
    return TenantPlan(region, backup, retention, tuple(subs))
