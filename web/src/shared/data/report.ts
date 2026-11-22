import { useCallback, useEffect, useState } from "react";

export type SetName = "heldout" | "dev";
export type Interval = [number, number, number];

export interface DesignRow {
  label: string;
  weeks_to_golive: Interval;
  on_time_share: Interval;
  live_share: Interval;
  p1_per_10_golives: Interval;
  exposure_per_10_golives: Interval;
  wrong_answers_per_1000: Interval;
  security_turnaround_weeks: Interval;
  drafted_share: Interval;
  revenue_in_horizon: Interval;
  overload_share: number;
  lead_hours_per_week: number;
  weeks_saved_vs_status_quo: Interval;
  revenue_in_horizon_per_seed: number;
}

export interface Rollout {
  customer: string;
  arrival: number;
  committed: number;
  golive: number | null;
  incidents: number;
}

export interface ProblemKind {
  planted: number;
  found_at_kickoff: number;
  area: "sso" | "dms" | "residency";
}

export interface Report {
  set: SetName;
  seeds: number[];
  config_sha: string;
  generated_at: string;
  weeks: number;
  facts: {
    customers: number;
    planted_problems: number;
    found_at_kickoff: number;
    false_alarms: number;
    questions: number;
    planted_by_kind: Record<string, ProblemKind>;
  };
  timeline_first_seed: Record<"status_quo" | "desk", Rollout[]>;
  designs: Record<string, DesignRow>;
}

export type LoadState = { status: "loading" } | { status: "error"; message: string } | { status: "missing" } | { status: "ready"; report: Report };

/** Loads reports/<set>.json as written by `python -m golive.eval.cli dev` or `heldout`. */
export function useReport(set: SetName): { state: LoadState; retry: () => void } {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    setState({ status: "loading" });
    fetch(`./reports/${set}.json`)
      .then(async (res) => {
        if (!live) return;
        if (res.status === 404) return setState({ status: "missing" });
        if (!res.ok) throw new Error(`The report did not load (HTTP ${res.status}).`);
        const report = (await res.json()) as Report;
        if (live) setState({ status: "ready", report });
      })
      .catch((err: unknown) => live && setState({ status: "error", message: err instanceof Error ? err.message : String(err) }));
    return () => {
      live = false;
    };
  }, [set, attempt]);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, retry };
}

export const ORDER = ["status_quo", "desk", "checks_late", "no_skill_match", "no_agent", "no_early_warning"] as const;

/** Short names for charts; the table shows each design's full label. */
export const SHORT: Record<string, string> = {
  status_quo: "Today",
  desk: "The desk",
  checks_late: "Checks only before go-live",
  no_skill_match: "Least-busy manager",
  no_agent: "No questionnaire agent",
  no_early_warning: "No lead stepping in",
};

/** Plain names for the problems the world plants in customers' setup files. */
export const PROBLEM: Record<string, string> = {
  certExpiring: "Signing certificate expires soon after go-live",
  weakKey: "1024-bit signing key",
  replyUrl: "Reply URL missing on the enterprise app",
  noGroups: "No groups claim for role mapping",
  noPkce: "No PKCE on the OIDC app",
  wallsUnmapped: "Ethical walls not mapped to the connector",
  anyonePublic: "'Anyone' links treated as readable by all",
  shallowGroups: "Connector reads nested groups one level deep",
  slowSync: "Permission changes sync every 4 hours",
  regionWrong: "Tenant outside the contracted region",
  usTranscription: "Transcription subprocessor in the US",
  retainingVendor: "Subprocessor keeps content",
};

export const AREA: Record<ProblemKind["area"], string> = { sso: "Sign-in", dms: "Document permissions", residency: "Data residency" };

export const pct = (x: number) => `${Math.round(x * 100)}%`;
export const one = (x: number) => x.toFixed(1);
export const money = (x: number) => `$${(x / 1e6).toFixed(2)}M`;
export const interval = (v: Interval, f: (x: number) => string = one) => `${f(v[0])} (${f(v[1])}–${f(v[2])})`;
