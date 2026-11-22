import { motion } from "framer-motion";
import { useState } from "react";

import type { Report, Rollout } from "../../shared/data/report";
import { useGrow } from "../../shared/theme/motion";
import styles from "./rollout.module.css";

const ROW = 11;
const GAP = 3;
const LEFT = 4;
const W = 520;

interface Hover {
  lane: string;
  r: Rollout;
  x: number;
  y: number;
}

function Lane({ name, title, rows, weeks, color, onHover }: { name: string; title: string; rows: Rollout[]; weeks: number; color: string; onHover: (h: Hover | null) => void }) {
  const grow = useGrow();
  const x = (w: number) => LEFT + (w / weeks) * (W - LEFT - 8);
  const h = rows.length * (ROW + GAP) + 24;
  const late = rows.filter((r) => r.golive !== null && r.golive > r.committed).length;
  const incidents = rows.reduce((n, r) => n + r.incidents, 0);
  const ticks = Array.from({ length: Math.floor(weeks / 4) + 1 }, (_, i) => i * 4);
  return (
    <figure className={styles.lane} aria-label={`${title}: ${rows.length} customers, ${late} past the committed date, ${incidents} P1 incidents`}>
      <figcaption className={styles.laneHead}>
        <span className={styles.swatch} style={{ background: color }} aria-hidden />
        <span className={styles.laneTitle}>{title}</span>
        <span className={styles.laneFacts}>
          {late} late, {incidents} P1 {incidents === 1 ? "incident" : "incidents"}
        </span>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${h}`} className={styles.svg} role="img" aria-hidden>
        <defs>
          <pattern id={`hatch-${name}`} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="5" height="5" fill="var(--surface)" />
            <line x1="0" y1="0" x2="0" y2="5" stroke="var(--late)" strokeWidth="2.4" />
          </pattern>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={0} y2={h - 20} stroke="var(--grid)" />
            <text x={x(t)} y={h - 6} className={styles.axis} textAnchor="middle">
              {t === 0 ? "week 0" : t}
            </text>
          </g>
        ))}
        {rows.map((r, i) => {
          const y = i * (ROW + GAP);
          const end = r.golive ?? weeks;
          const onTime = Math.min(end, r.committed);
          return (
            <g
              key={r.customer}
              className={styles.row}
              onMouseEnter={() => onHover({ lane: title, r, x: x(end), y })}
              onMouseLeave={() => onHover(null)}
            >
              <rect x={0} y={y - 1} width={W} height={ROW + GAP} fill="transparent" />
              <motion.rect
                x={x(r.arrival)}
                y={y}
                width={Math.max(x(onTime) - x(r.arrival), 2)}
                height={ROW}
                rx={3}
                fill={color}
                style={{ originX: 0 }}
                {...grow(i)}
              />
              {end > r.committed && (
                <motion.rect
                  x={x(r.committed) + 1}
                  y={y}
                  width={Math.max(x(end) - x(r.committed) - 1, 2)}
                  height={ROW}
                  rx={3}
                  fill={`url(#hatch-${name})`}
                  stroke="var(--late)"
                  strokeWidth={1}
                  style={{ originX: 0 }}
                  {...grow(i + 6)}
                />
              )}
              <line x1={x(r.committed)} x2={x(r.committed)} y1={y - 1.5} y2={y + ROW + 1.5} stroke="var(--ink)" strokeWidth={1.5} />
              {r.incidents > 0 && <circle cx={x(end) + 7} cy={y + ROW / 2} r={4.2} fill="var(--critical)" stroke="var(--surface)" strokeWidth={2} />}
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

export function RolloutBoard({ report }: { report: Report }) {
  const [hover, setHover] = useState<Hover | null>(null);
  const t = report.timeline_first_seed;
  const weeks = Math.max(24, ...[...t.status_quo, ...t.desk].map((r) => (r.golive ?? 0) + 2));
  return (
    <section className={styles.board} aria-labelledby="board-title">
      <div className={styles.head}>
        <h2 id="board-title">The same {t.desk.length} customers, rolled out twice</h2>
        <p className={styles.sub}>
          Seed {report.seeds[0]}, in order of signing. Each bar runs from kickoff to go-live; the black tick is the date promised at kickoff.
        </p>
        <ul className={styles.legend}>
          <li>
            <span className={styles.keyHatch} aria-hidden /> weeks past the promised date
          </li>
          <li>
            <span className={styles.keyTick} aria-hidden /> promised date
          </li>
          <li>
            <span className={styles.keyDot} aria-hidden /> P1 incident after go-live
          </li>
        </ul>
      </div>
      <div className={styles.lanes}>
        <Lane name="today" title="Today" rows={t.status_quo} weeks={weeks} color="var(--today)" onHover={setHover} />
        <Lane name="desk" title="With the desk" rows={t.desk} weeks={weeks} color="var(--desk)" onHover={setHover} />
      </div>
      <p className={styles.tip} aria-live="polite">
        {hover ? (
          <>
            <strong>{hover.r.customer}</strong>, {hover.lane.toLowerCase()}: kickoff week {hover.r.arrival}, promised week {hover.r.committed},{" "}
            {hover.r.golive === null ? "not live inside the horizon" : `live week ${hover.r.golive}`}
            {hover.r.golive !== null && hover.r.golive > hover.r.committed ? `, ${hover.r.golive - hover.r.committed} weeks late` : ""}
            {hover.r.incidents > 0 ? `, ${hover.r.incidents} P1 after go-live` : ""}
          </>
        ) : (
          "Point at a customer to read its dates."
        )}
      </p>
    </section>
  );
}
