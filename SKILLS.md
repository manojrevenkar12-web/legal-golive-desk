# SKILLS.md

Repeatable tasks, each with the commands that finish it.

## Add a readiness check
1. Add the check to `golive/sso.py`, `dms.py` or `residency.py`, returning `Finding(check, severity, message, fix)`.
   The message says what breaks for the customer; the fix says what to change.
2. If the world should plant it, add the problem to `config/world.json` (rate), `golive/world/artifacts.py` (write it into
   the file), and `FOUND_BY` / `AREA` in `golive/world/world.py`.
3. Unit test it on a generated file in `tests/`, then `python -m golive.eval.cli dev` and check `false_alarms` stays 0.

## Add approved evidence for security reviews
1. Add the statement to `config/evidence.json` with an owner-approved text, keywords in English and German, and `valid_until`.
2. If questions in the world should be answered by it, add phrasings to `golive/world/questions.py`.
3. `pytest tests/test_questionnaire.py` and a dev run: wrong answers per 1,000 must not rise.

## Change a threshold
Edit `config/product.json`, run `python -m golive.eval.cli dev`, read the README block. Never after the held-out run.

## Run the held-out seeds (once)
`python -m golive.eval.cli heldout`, then `python scripts/screenshots.py`, commit `reports/`, `heldout.lock`, the README
and the screenshots together.

## Run the service
`uvicorn golive.service.app:app --reload`, then POST to `/checks/sso/saml`, `/checks/sso/oidc`, `/checks/dms`,
`/checks/residency`, `/questionnaires/answer`, `/delivery/assign`. OpenAPI docs at `/docs`.
