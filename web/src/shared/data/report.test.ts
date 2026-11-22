import { describe, expect, it } from "vitest";

import { interval, money, pct } from "./report";

describe("report helpers", () => {
  it("formats shares, money and intervals", () => {
    expect(pct(0.846)).toBe("85%");
    expect(money(3077861)).toBe("$3.08M");
    expect(interval([4.7, 4.25, 5.19])).toBe("4.7 (4.3–5.2)");
  });
});
