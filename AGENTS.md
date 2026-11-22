# AGENTS.md

How to work in this repository, for people and coding agents alike.

## Fast feedback

```bash
pip install -r requirements.txt
ruff check . && ruff format --check . && mypy && pytest -q   # about 5 seconds
python -m golive.eval.cli dev                                 # 3 dev seeds, about 4 seconds; rewrites reports/ and the README block
python -m golive.eval.cli gate                                # exits 1 if a gate fails
cd web && npm ci && npm test && npm run build                 # dashboard
```

## Invariants

1. **The truth stays in the world.** `golive/world/` decides which problems each customer's setup has, how slow their IT
   and security reviewers are and what breaks after go-live. Product code (`golive/sso.py`, `dms.py`, `residency.py`,
   `questionnaire.py`, `delivery.py`, `golive/service/`) never imports `golive.world` or `golive.eval`. A test enforces it.
2. **The world does not read the product's settings.** `World(seed)` reads only `config/world.json`. The product's
   thresholds live in `config/product.json` and reach the simulation only through the design being played.
3. **Same luck for every design.** Every random draw comes from `Keyed(seed).rng(tag, *ids)`, keyed by what it is about,
   never by the order things happen in. Never iterate a set while drawing random numbers; sort it first.
4. **The model reads and code decides.** The questionnaire agent's retrieval and the optional Claude rephraser only
   propose. Code decides whether an answer is drafted (score, margin, coverage), refuses a rephrasing that drops the
   citation or adds a number, and never cites expired evidence. A person approves every draft before it is sent.
5. **Customer files are untrusted input.** SAML metadata is parsed with defusedxml; API inputs are size-capped; a
   question's text never changes what the agent is allowed to do.
6. **Settings in config.** Thresholds, rates and team sizes are in `config/*.json`, not in code.
7. **Reports are generated.** `reports/*.json`, `reports/REPORT.md` and the README block between the results markers
   are written by `golive.eval.cli`. Never edit them by hand. CI fails if `reports/dev.json` differs from what the code
   produces.

## The held-out rule

`config/seeds.json` holds dev seeds `[1, 2, 3]` and held-out seeds `[9101, 9102, 9103]`. Tune only on dev. Gates in
`config/gates.json` are set on dev before the held-out run and never loosened after it. `python -m golive.eval.cli heldout`
runs once and writes `heldout.lock` with the config hash; a second run is refused, and CI fails if any config file
changes after the lock.
