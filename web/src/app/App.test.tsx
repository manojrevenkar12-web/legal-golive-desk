import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import fixture from "../test/report.fixture.json";
import { App } from "./App";

afterEach(() => vi.restoreAllMocks());

function serve(status: number, body?: unknown) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(body ? JSON.stringify(body) : null, { status }));
}

describe("dashboard", () => {
  it("shows the headline, both rollout lanes and every design", async () => {
    serve(200, fixture);
    render(<App />);
    await waitFor(() => expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("weeks sooner"));
    expect(screen.getByRole("figure", { name: /^Today:/ })).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: /^With the desk:/ })).toBeInTheDocument();
    expect(screen.getAllByText("No questionnaire agent").length).toBeGreaterThan(0);
  });

  it("says how to make a missing report", async () => {
    serve(404);
    render(<App />);
    await waitFor(() => expect(screen.getByText(/python -m golive.eval.cli heldout/)).toBeInTheDocument());
  });

  it("offers a retry when the report fails", async () => {
    serve(500);
    render(<App />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("HTTP 500"));
  });
});
