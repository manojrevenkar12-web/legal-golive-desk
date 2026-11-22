import { ORDER, SHORT, one, pct, type Report } from "../../shared/data/report";
import styles from "./reviews.module.css";

export function Reviews({ report }: { report: Report }) {
  const sq = report.designs.status_quo!;
  const desk = report.designs.desk!;
  return (
    <section className={styles.section} aria-labelledby="reviews-title">
      <div className={styles.block}>
        <h2 id="reviews-title">Security reviews</h2>
        <p className={styles.lede}>
          The questionnaire agent drafts an answer only from approved, unexpired evidence that matches clearly and covers what was asked, and cites it. Everything else goes
          to the security team. A person approves every draft before it is sent.
        </p>
        <dl className={styles.facts}>
          <div>
            <dt>Questions drafted from evidence</dt>
            <dd>{pct(desk.drafted_share[0])}</dd>
          </div>
          <div>
            <dt>Weeks until the review is answered</dt>
            <dd>
              {one(desk.security_turnaround_weeks[0])} <span>today {one(sq.security_turnaround_weeks[0])}</span>
            </dd>
          </div>
          <div>
            <dt>Wrong answers sent, per 1,000</dt>
            <dd>
              {one(desk.wrong_answers_per_1000[0])} <span>today {one(sq.wrong_answers_per_1000[0])}</span>
            </dd>
          </div>
        </dl>
      </div>
      <div className={styles.block}>
        <h2>The team behind it</h2>
        <p className={styles.lede}>
          Five delivery managers with 22 project hours a week each, and a lead who steps into projects heading past their date. Overload is the share of manager-weeks with
          more open work than hours.
        </p>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Design</th>
              <th scope="col">Manager-weeks over capacity</th>
              <th scope="col">Lead hours a week stepping in</th>
            </tr>
          </thead>
          <tbody>
            {ORDER.map((n) => (
              <tr key={n}>
                <th scope="row">{SHORT[n]}</th>
                <td>{pct(report.designs[n]!.overload_share)}</td>
                <td>{one(report.designs[n]!.lead_hours_per_week)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
