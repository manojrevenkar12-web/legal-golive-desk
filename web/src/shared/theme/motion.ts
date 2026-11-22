import { useReducedMotion } from "framer-motion";

/** The page's one orchestrated moment: rollout bars grow from kickoff to go-live, row by row. */
export function useGrow() {
  const reduce = useReducedMotion();
  return (row: number) =>
    reduce
      ? { initial: false as const }
      : { initial: { scaleX: 0 }, animate: { scaleX: 1 }, transition: { duration: 0.55, delay: 0.15 + row * 0.018, ease: [0.2, 0.7, 0.2, 1] as const } };
}
