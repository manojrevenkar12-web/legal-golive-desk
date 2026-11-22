import styles from "./states.module.css";

export function Loading() {
  return (
    <div className={styles.state} role="status" aria-live="polite">
      <span className={styles.pulse} aria-hidden />
      Reading the report…
    </div>
  );
}

export function Failed({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className={styles.state} role="alert">
      <p>{message}</p>
      <button className={styles.button} onClick={onRetry}>
        Load the report again
      </button>
    </div>
  );
}

export function Missing({ set, onDev }: { set: string; onDev: () => void }) {
  return (
    <div className={styles.state}>
      <p>
        There is no {set === "heldout" ? "held-out" : "development"} report yet. Run <code>python -m golive.eval.cli {set}</code> to write it.
      </p>
      {set === "heldout" && (
        <button className={styles.button} onClick={onDev}>
          Show the development seeds
        </button>
      )}
    </div>
  );
}
