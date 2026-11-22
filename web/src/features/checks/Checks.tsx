import { AREA, PROBLEM, type ProblemKind, type Report } from "../../shared/data/report";
import styles from "./checks.module.css";

const AREAS: ProblemKind["area"][] = ["sso", "dms", "residency"];

export function Checks({ report }: { report: Report }) {
  const kinds = Object.entries(report.facts.planted_by_kind);
  const max = Math.max(...kinds.map(([, k]) => k.planted));
  const f = report.facts;
  return (
    <section className={styles.section} aria-labelledby="checks-title">
      <div className={styles.text}>
        <h2 id="checks-title">What the kickoff checks read</h2>
        <p>
          The world writes each customer's real setup files with problems planted in them: SAML metadata with a real X.509 certificate, an OIDC discovery document, a
          DMS permission export with its connector plan, the tenant plan. The checkers read the files, not the flags.
        </p>
        <p className={styles.count}>
          <strong>{f.found_at_kickoff}</strong> of {f.planted_problems} planted problems found at kickoff, with {f.false_alarms} blocker{" "}
          {f.false_alarms === 1 ? "finding" : "findings"} no planted problem explains.
        </p>
      </div>
      <div className={styles.areas}>
        {AREAS.map((a) => (
          <div key={a} className={styles.area}>
            <h3>{AREA[a]}</h3>
            <ul>
              {kinds
                .filter(([, k]) => k.area === a)
                .sort((x, y) => y[1].planted - x[1].planted)
                .map(([name, k]) => (
                  <li key={name}>
                    <span className={styles.what}>{PROBLEM[name] ?? name}</span>
                    <span className={styles.bar} aria-hidden>
                      <span style={{ width: `${(k.planted / max) * 100}%` }} />
                    </span>
                    <span className={styles.n}>
                      {k.found_at_kickoff}/{k.planted}
                    </span>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
