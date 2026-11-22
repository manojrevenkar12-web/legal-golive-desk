import { useState } from "react";

import { type DesignRow, ORDER, SHORT, interval, money, one, pct, type Report } from "../../shared/data/report";
import styles from "./designs.module.css";

const COLOR: Record<string, string> = { status_quo: "var(--today)", desk: "var(--desk)" };
const W = 560;
const LABEL = 190;
const ROW = 34;

function WeeksChart({ designs }: { designs: Record<string, DesignRow> }) {
  const [hover, setHover] = useState<string | null>(null);
  const max = Math.ceil(Math.max(...ORDER.map((n) => designs[n]!.weeks_to_golive[2])) + 1);
  const x = (w: number) => LABEL + (w / max) * (W - LABEL - 16);
  const ticks = Array.from({ length: Math.floor(max / 2) + 1 }, (_, i) => i * 2);
  const h = ORDER.length * ROW + 28;
  return (
    <figure className={styles.chart} aria-label="Weeks from kickoff to go-live for every design, with 95% intervals">
      <svg viewBox={`0 0 ${W} ${h}`} className={styles.svg} role="img" aria-hidden>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={0} y2={h - 22} stroke="var(--grid)" />
            <text x={x(t)} y={h - 6} textAnchor="middle" className={styles.axis}>
              {t}
            </text>
          </g>
        ))}
        {ORDER.map((n, i) => {
          const v = designs[n]!.weeks_to_golive;
          const y = i * ROW + ROW / 2;
          const color = COLOR[n] ?? "var(--ink-3)";
          return (
            <g key={n} onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(null)}>
              <rect x={0} y={y - ROW / 2} width={W} height={ROW} fill={hover === n ? "var(--grid)" : "transparent"} rx={4} />
              <text x={0} y={y + 4} className={n in COLOR ? styles.nameStrong : styles.name}>
                {SHORT[n]}
              </text>
              <line x1={x(v[1])} x2={x(v[2])} y1={y} y2={y} stroke={color} strokeWidth={2} strokeLinecap="round" />
              <circle cx={x(v[0])} cy={y} r={5.5} fill={color} stroke="var(--surface)" strokeWidth={2} />
              <text x={x(v[2]) + 10} y={y + 4} className={styles.value}>
                {one(v[0])}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className={styles.caption}>
        {hover
          ? `${SHORT[hover]}: ${interval(designs[hover]!.weeks_to_golive)} weeks to go-live, ${pct(designs[hover]!.on_time_share[0])} on the promised date.`
          : "Weeks from kickoff to go-live. Dot: mean; line: 95% interval over customers."}
      </figcaption>
    </figure>
  );
}

export function DesignCompare({ report }: { report: Report }) {
  const d = report.designs;
  return (
    <section className={styles.section} aria-labelledby="designs-title">
      <div className={styles.text}>
        <h2 id="designs-title">Which part of the desk does the work</h2>
        <p>
          Every design meets the same customers with the same luck: the same setup problems, the same slow IT teams, the same questionnaires. Taking one part away
          shows what that part is worth.
        </p>
      </div>
      <WeeksChart designs={d} />
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption className={styles.srOnly}>Every design's results on the {report.set} seeds</caption>
          <thead>
            <tr>
              <th scope="col">Design</th>
              <th scope="col">Weeks saved vs today</th>
              <th scope="col">On the promised date</th>
              <th scope="col">P1 per 10 go-lives</th>
              <th scope="col">Documents exposed per 10</th>
              <th scope="col">Wrong answers per 1,000</th>
              <th scope="col">Live revenue in horizon, per seed</th>
            </tr>
          </thead>
          <tbody>
            {ORDER.map((n) => {
              const r = d[n]!;
              return (
                <tr key={n} className={n === "desk" ? styles.mine : undefined}>
                  <th scope="row">
                    <span className={styles.rowName}>{SHORT[n]}</span>
                    <span className={styles.rowLabel}>{r.label}</span>
                  </th>
                  <td>{n === "status_quo" ? "–" : interval(r.weeks_saved_vs_status_quo)}</td>
                  <td>{pct(r.on_time_share[0])}</td>
                  <td>{r.p1_per_10_golives[0].toFixed(2)}</td>
                  <td>{r.exposure_per_10_golives[0].toFixed(2)}</td>
                  <td>{one(r.wrong_answers_per_1000[0])}</td>
                  <td>{money(r.revenue_in_horizon_per_seed)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
