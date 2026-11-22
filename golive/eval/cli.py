"""python -m golive.eval.cli dev | heldout | readme | gate | check-lock

The held-out seeds run once: `heldout` writes heldout.lock with the config it ran on and refuses a second run.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from golive.eval.report import block, gate, report_md, write_readme
from golive.eval.run import config_sha, load, run

REPORTS = Path(os.environ.get("GOLIVE_REPORTS", "reports"))
LOCK = Path(os.environ.get("GOLIVE_LOCK", "heldout.lock"))


def _read(name: str) -> dict[str, Any] | None:
    p = REPORTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _write(doc: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{doc['set']}.json").write_text(json.dumps(doc, indent=1) + "\n")


def _comparable(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k != "generated_at"}


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "dev"
    gates = load("gates")
    if cmd == "dev":
        _write(run("dev"))
        return main(["readme"])
    if cmd == "heldout":
        if LOCK.exists():
            print(f"refused: the held-out seeds already ran ({LOCK.read_text().strip()}). They run once.", file=sys.stderr)
            return 2
        doc = run("heldout")
        _write(doc)
        LOCK.write_text(json.dumps({"config_sha": doc["config_sha"], "ran_on": doc["generated_at"]}) + "\n")
        return main(["readme"])
    if cmd == "readme":
        dev, held = _read("dev"), _read("heldout")
        if dev is None:
            print("no reports/dev.json; run `dev` first", file=sys.stderr)
            return 1
        write_readme(Path("README.md"), block(dev, held, gates))
        (REPORTS / "REPORT.md").write_text(report_md(dev, held, gates))
        return 0
    if cmd == "gate":
        failed = False
        for name in ("dev", "heldout"):
            found = _read(name)
            if found is None:
                continue
            for what, ok, measured in gate(found, gates):
                print(f"{name:8} {'pass' if ok else 'FAIL'}  {what}: {measured}")
                failed |= not ok
        return 1 if failed else 0
    if cmd == "check-lock":
        """CI: the committed dev report is what the code produces, and nothing the held-out run read has changed since."""
        dev = _read("dev")
        if dev is None or _comparable(dev) != _comparable(json.loads(json.dumps(run("dev")))):
            print("reports/dev.json is not what the code produces; run `python -m golive.eval.cli dev`", file=sys.stderr)
            return 1
        if LOCK.exists():
            locked = json.loads(LOCK.read_text())["config_sha"]
            if locked != config_sha():
                print(f"config changed after the held-out run (locked {locked}, now {config_sha()})", file=sys.stderr)
                return 1
        print("reports match the code; held-out lock holds")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
