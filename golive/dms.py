"""Document-management permissions, checked before the AI workspace indexes a single matter.

A law firm's DMS (iManage workspaces, SharePoint sites) decides who may read each document: container ACLs,
documents with their own ACL, nested groups and ethical walls that deny whole teams access to a matter. The connector
that feeds the AI workspace has its own idea of who may read what, set by the integration plan. This module computes
both and reports every (user, document) pair the connector would expose that the DMS denies, with the cause, and every
pair it would hide that the DMS allows.

The export format is neutral, so iManage and SharePoint exports map onto it:

    users:      ["u1", ...]
    groups:     {"g-ma": ["u1", "g-ma-partners"], ...}            members are users or groups, nested
    containers: [{"id": "M-1001", "public": false, "acl": ["g-ma"]}]  iManage workspace / SharePoint site
    documents:  [{"id": "D-1", "container": "M-1001", "acl": null | [...], "links": ["anyone" | "org"]}]
    walls:      [{"id": "W-1", "containers": ["M-1001"], "excluded": ["g-lit"]}]
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from golive.findings import Finding, Severity


@dataclass(frozen=True)
class IntegrationPlan:
    """How the connector is set up to read the DMS."""

    mode: str = "per_user"  # "per_user": results trimmed to each user's permissions; "service_account": one index for all
    group_depth: int = 8  # how deep the connector expands nested groups
    walls_mapped: bool = True  # whether ethical walls are mapped into the connector's deny rules
    anyone_links_public: bool = False  # whether documents with an "anyone" link are treated as readable by all users
    acl_sync_minutes: int = 15
    scope: tuple[str, ...] = ()  # container ids to index; empty means all


@dataclass
class PermissionAudit:
    exposed_pairs: int
    hidden_pairs: int
    exposed_documents: int
    causes: dict[str, int]
    sample: list[dict[str, str]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "exposed_pairs": self.exposed_pairs,
            "hidden_pairs": self.hidden_pairs,
            "exposed_documents": self.exposed_documents,
            "causes": self.causes,
            "sample": self.sample,
            "findings": [f.as_dict() for f in self.findings],
        }


def _expand(principals: list[str], groups: dict[str, list[str]], users: set[str], depth: int) -> set[str]:
    """Users reached from [principals], following nested groups up to [depth] levels."""
    out: set[str] = set()
    seen: set[str] = set()
    frontier = [(p, 0) for p in principals]
    while frontier:
        p, d = frontier.pop()
        if p in users:
            out.add(p)
        elif p in groups and p not in seen and d < depth:
            seen.add(p)
            frontier.extend((m, d + 1) for m in groups[p])
    return out


def _readers(export: dict[str, Any], depth: int, walls: bool, anyone_public: bool, wall_depth: int | None = None) -> dict[str, set[str]]:
    """Readers of every document under one way of reading the permissions. [wall_depth] defaults to [depth]."""
    users = set(export["users"])
    groups: dict[str, list[str]] = export.get("groups", {})
    containers = {c["id"]: c for c in export["containers"]}
    excluded: dict[str, set[str]] = defaultdict(set)
    if walls:
        for w in export.get("walls", []):
            blocked = _expand(w["excluded"], groups, users, depth if wall_depth is None else wall_depth)
            for cid in w["containers"]:
                excluded[cid] |= blocked
    cache: dict[tuple[str, ...], set[str]] = {}
    out: dict[str, set[str]] = {}
    for d in export["documents"]:
        c = containers[d["container"]]
        if anyone_public and "anyone" in d.get("links", []):
            readers = set(users)
        elif d.get("acl") is not None:
            key = tuple(sorted(d["acl"]))
            readers = cache.setdefault(key, _expand(list(key), groups, users, depth))
        elif c.get("public"):
            readers = set(users)
        else:
            key = tuple(sorted(c.get("acl", [])))
            readers = cache.setdefault(key, _expand(list(key), groups, users, depth))
        out[d["id"]] = readers - excluded[d["container"]]
    return out


def audit(export: dict[str, Any], plan: IntegrationPlan, max_sync_minutes: int = 60) -> PermissionAudit:
    """Compares the DMS's own permissions with what the connector, as planned, would let each user find."""
    users = set(export["users"])
    in_scope = set(plan.scope) if plan.scope else {c["id"] for c in export["containers"]}
    docs = [d for d in export["documents"] if d["container"] in in_scope]
    truth = _readers(export, depth=64, walls=True, anyone_public=False)
    if plan.mode == "service_account":
        connector = {d["id"]: set(users) for d in docs}
    else:
        connector = _readers(export, depth=plan.group_depth, walls=plan.walls_mapped, anyone_public=plan.anyone_links_public)

    # attribute each exposure to the first planned setting that explains it
    no_walls = _readers(export, depth=64, walls=False, anyone_public=False)
    shallow = _readers(export, depth=plan.group_depth, walls=True, anyone_public=False)
    walls_full = _readers(export, depth=plan.group_depth, walls=True, anyone_public=False, wall_depth=64)
    causes: dict[str, int] = defaultdict(int)
    exposed = hidden = 0
    exposed_docs = 0
    sample: list[dict[str, str]] = []
    by_id = {d["id"]: d for d in docs}
    for did in sorted(by_id):
        extra = connector[did] - truth[did]
        missing = truth[did] - connector[did]
        hidden += len(missing)
        if not extra:
            continue
        exposed += len(extra)
        exposed_docs += 1
        for u in sorted(extra):
            if plan.mode == "service_account":
                cause = "one index for every user"
            elif not plan.walls_mapped and u in no_walls[did]:
                cause = "ethical wall not mapped"
            elif plan.anyone_links_public and "anyone" in by_id[did].get("links", []):
                cause = "'anyone' link treated as public"
            elif u not in walls_full[did]:
                cause = "wall's excluded group nested deeper than the connector reads"
            elif u not in shallow[did]:
                cause = "nested group deeper than the connector reads"
            else:
                cause = "other"
            causes[cause] += 1
            if len(sample) < 10:
                sample.append({"user": u, "document": did, "matter": by_id[did]["container"], "cause": cause})

    findings: list[Finding] = []
    if exposed:
        findings.append(
            Finding(
                "dms.exposure",
                Severity.BLOCKER,
                f"{exposed} user-document pairs across {exposed_docs} documents would be findable in the workspace although the DMS denies them ({', '.join(f'{k}: {v}' for k, v in sorted(causes.items()))}).",
                "Change the integration plan until this count is zero; see the causes.",
            )
        )
    if causes.get("ethical wall not mapped"):
        findings.append(
            Finding(
                "dms.walls", Severity.BLOCKER, "Ethical walls are not mapped into the connector.", "Map every wall's excluded groups to deny rules before indexing walled matters."
            )
        )
    if hidden:
        findings.append(
            Finding(
                "dms.hidden",
                Severity.WARN,
                f"{hidden} user-document pairs the DMS allows would not be findable in the workspace.",
                "Raise the connector's group expansion depth or sync the missing groups; lawyers will otherwise miss documents.",
            )
        )
    anyone = sum(1 for d in docs if "anyone" in d.get("links", []))
    if anyone:
        findings.append(
            Finding(
                "dms.anyone_links",
                Severity.WARN if not plan.anyone_links_public else Severity.BLOCKER,
                f"{anyone} documents in scope carry an 'anyone' sharing link.",
                "Review these links with the firm; do not treat them as readable by every user.",
            )
        )
    if plan.acl_sync_minutes > max_sync_minutes:
        findings.append(
            Finding(
                "dms.acl_sync",
                Severity.WARN,
                f"Permission changes reach the connector after {plan.acl_sync_minutes} minutes; a removed lawyer keeps access that long.",
                f"Sync permissions at least every {max_sync_minutes} minutes, or on change events.",
            )
        )
    return PermissionAudit(exposed, hidden, exposed_docs, dict(causes), sample, findings)
