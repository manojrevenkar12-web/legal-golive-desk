import { useState } from "react";

import { Checks } from "../features/checks/Checks";
import { DesignCompare } from "../features/designs/DesignCompare";
import { Reviews } from "../features/reviews/Reviews";
import { RolloutBoard } from "../features/rollout/RolloutBoard";
import { type Report, type SetName, one, pct, useReport } from "../shared/data/report";
import { Failed, Loading, Missing } from "../shared/ui/states";
import styles from "./App.module.css";

function initialSet(): SetName {
  const q = new URLSearchParams(window.location.search).get("set");
  return q === "dev" ? "dev" : "heldout";
}

function Headline({ report }: { report: Report }) {
  const d = report.designs.desk!;
  const sq = report.designs.status_quo!;
  const s = d.weeks_saved_vs_status_quo;
  return (
    <div className={styles.headline}>
      <h1>
        Law firms went live {one(s[0])} weeks sooner, {pct(d.on_time_share[0])} of them on the date promised at kickoff.
      </h1>
      <p>
        {report.facts.customers} simulated EMEA customers over {report.seeds.length} {report.set === "heldout" ? "held-out" : "development"} seeds. Today they take{" "}
        {one(sq.weeks_to_golive[0])} weeks and {pct(sq.on_time_share[0])} land on time; the desk takes {one(d.weeks_to_golive[0])}. The 95% interval on the weeks saved is{" "}
        {one(s[1])} to {one(s[2])}. P1 incidents after go-live fall from {one(sq.p1_per_10_golives[0])} to {one(d.p1_per_10_golives[0])} per 10 go-lives.
      </p>
    </div>
  );
}

export function App() {
  const [set, setSet] = useState<SetName>(initialSet);
  const { state, retry } = useReport(set);
  return (
    <div className={styles.page}>
      <header className={styles.top}>
        <div>
          <p className={styles.name}>legal-golive-desk</p>
          <p className={styles.what}>Go-live readiness, security reviews and staffing for rolling out a legal AI workspace</p>
        </div>
        <div className={styles.switch} role="group" aria-label="Which seeds to show">
          {(["heldout", "dev"] as const).map((s) => (
            <button key={s} aria-pressed={set === s} onClick={() => setSet(s)}>
              {s === "heldout" ? "Held-out seeds" : "Development seeds"}
            </button>
          ))}
        </div>
      </header>
      <main className={styles.main}>
        {state.status === "loading" && <Loading />}
        {state.status === "error" && <Failed message={state.message} onRetry={retry} />}
        {state.status === "missing" && <Missing set={set} onDev={() => setSet("dev")} />}
        {state.status === "ready" && (
          <>
            <Headline report={state.report} />
            <RolloutBoard report={state.report} />
            <DesignCompare report={state.report} />
            <Checks report={state.report} />
            <Reviews report={state.report} />
            <footer className={styles.foot}>
              <p>
                Seeds {state.report.seeds.join(", ")}, config {state.report.config_sha}, generated {state.report.generated_at}. Everything here is simulated: the customers,
                their IT teams and the security team are a model; the checkers, the questionnaire agent and the staffing rules are the real code, run on generated files. See
                the README for the limits.
              </p>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
