"""Runs every design on the same simulated region and summarises what happened, with 95% intervals."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import statistics
from pathlib import Path
from typing import Any

from golive.world.world import AREA, Outcome, World, simulate

CONFIGS = ("world", "product", "designs", "gates", "seeds")


def config_sha() -> str:
    h = hashlib.sha256()
    for n in CONFIGS:
        h.update(Path(f"config/{n}.json").read_bytes())
    return h.hexdigest()[:12]


def load(name: str) -> Any:
    return json.loads(Path(f"config/{name}.json").read_text())


def per_customer(o: Outcome, weeks: int) -> dict[str, float]:
    live = o.golive is not None
    return {
        "live": 1.0 if live else 0.0,
        "weeks_to_golive": float(o.golive - o.arrival) if live and o.golive is not None else float("nan"),
        "on_time": 1.0 if live and o.golive is not None and o.golive <= o.committed else 0.0,
        "incidents": float(o.incidents),
        "exposure_incidents": float(o.exposure_incidents),
        "wrong_answers": float(o.wrong_answers),
        "questions": float(o.questions),
        "security_turnaround": o.security_turnaround,
        "revenue_in_horizon": o.acv * (weeks - o.golive) / 52 if live and o.golive is not None else 0.0,
        "planted": float(o.planted),
        "found_early": float(o.found_early),
        "routed": float(o.routed),
    }


def summary(rows: list[dict[str, float]]) -> dict[str, float]:
    live = [r for r in rows if r["live"]]
    n_live = max(len(live), 1)
    q = sum(r["questions"] for r in rows)
    return {
        "weeks_to_golive": statistics.fmean(r["weeks_to_golive"] for r in live) if live else float("nan"),
        "on_time_share": sum(r["on_time"] for r in rows) / max(len(rows), 1),
        "live_share": len(live) / max(len(rows), 1),
        "p1_per_10_golives": 10 * sum(r["incidents"] for r in live) / n_live,
        "exposure_per_10_golives": 10 * sum(r["exposure_incidents"] for r in live) / n_live,
        "wrong_answers_per_1000": 1000 * sum(r["wrong_answers"] for r in rows) / max(q, 1),
        "security_turnaround_weeks": statistics.fmean(r["security_turnaround"] for r in rows),
        "drafted_share": 1 - sum(r["routed"] for r in rows) / max(q, 1),
        "revenue_in_horizon": sum(r["revenue_in_horizon"] for r in rows),
    }


def boot(rows: list[dict[str, float]], n: int = 1000, seed: int = 7) -> dict[str, list[float]]:
    """Each metric with a 95% interval, resampling customers."""
    base = summary(rows)
    r = random.Random(seed)
    samples = [summary([rows[r.randrange(len(rows))] for _ in rows]) for _ in range(n)]
    out = {}
    for k, v in base.items():
        vals = sorted(s[k] for s in samples)
        out[k] = [round(v, 4), round(vals[int(0.025 * n)], 4), round(vals[int(0.975 * n) - 1], 4)]
    return out


def run(set_name: str) -> dict[str, Any]:
    seeds = load("seeds")[set_name]
    designs = load("designs")
    product = load("product")
    rows: dict[str, list[dict[str, float]]] = {d: [] for d in designs}
    region: dict[str, dict[str, list[float]]] = {d: {"overload_share": [], "lead_hours": []} for d in designs}
    revenue_per_seed: dict[str, list[float]] = {d: [] for d in designs}
    facts: dict[str, Any] = {"customers": 0, "planted_problems": 0, "found_at_kickoff": 0, "false_alarms": 0, "questions": 0}
    by_kind: dict[str, list[int]] = {}
    timeline: dict[str, list[dict[str, Any]]] = {}
    weeks = 0
    for seed in seeds:
        world = World(seed)
        weeks = world.weeks
        facts["customers"] += len(world.customers)
        facts["planted_problems"] += sum(len(c.planted) for c in world.customers)
        facts["found_at_kickoff"] += sum(len(c.detected) for c in world.customers)
        facts["false_alarms"] += sum(c.false_alarms for c in world.customers)
        facts["questions"] += sum(len(c.questions) for c in world.customers)
        for c in world.customers:
            for p in c.planted:
                n = by_kind.setdefault(p, [0, 0])
                n[0] += 1
                n[1] += p in c.detected
        for name, d in designs.items():
            outcomes, totals = simulate(world, d, product)
            rs = [per_customer(o, world.weeks) for o in outcomes]
            rows[name].extend(rs)
            if seed == seeds[0] and name in ("status_quo", "desk"):
                timeline[name] = [{"customer": o.customer, "arrival": o.arrival, "committed": o.committed, "golive": o.golive, "incidents": o.incidents} for o in outcomes[:40]]
            revenue_per_seed[name].append(sum(r["revenue_in_horizon"] for r in rs))
            for k, v in totals.items():
                region[name][k].append(v)
    doc: dict[str, Any] = {
        "set": set_name,
        "seeds": seeds,
        "config_sha": config_sha(),
        "generated_at": dt.date.today().isoformat(),
        "weeks": weeks,
        "facts": {**facts, "planted_by_kind": {k: {"planted": v[0], "found_at_kickoff": v[1], "area": AREA[k]} for k, v in sorted(by_kind.items())}},
        "timeline_first_seed": timeline,
        "designs": {},
    }
    base = rows["status_quo"]
    for name, d in designs.items():
        s = boot(rows[name])
        doc["designs"][name] = {
            "label": d["label"],
            **s,
            "overload_share": round(statistics.fmean(region[name]["overload_share"]), 4),
            "lead_hours_per_week": round(statistics.fmean(region[name]["lead_hours"]) / weeks, 2),
            "weeks_saved_vs_status_quo": paired_diff(rows[name], base, "weeks_to_golive"),
            "revenue_in_horizon_per_seed": round(statistics.fmean(revenue_per_seed[name]), 0),
        }
    return doc


def paired_diff(a: list[dict[str, float]], b: list[dict[str, float]], key: str, n: int = 1000, seed: int = 11) -> list[float]:
    """How many weeks sooner a design goes live than the status quo, on the same customers, with a 95% interval."""
    pairs = [(x[key], y[key]) for x, y in zip(a, b, strict=True) if x["live"] and y["live"]]
    if not pairs:
        return [0.0, 0.0, 0.0]
    d = [y - x for x, y in pairs]
    r = random.Random(seed)
    means = sorted(statistics.fmean(d[r.randrange(len(d))] for _ in d) for _ in range(n))
    return [round(statistics.fmean(d), 3), round(means[int(0.025 * n)], 3), round(means[int(0.975 * n) - 1], 3)]
