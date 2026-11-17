# VIGIL — Development Log & Audit Trail

> **Audit Policy:** Every phase execution, prompt used, preflight result, and architectural decision is recorded chronologically.

---

## Session 1: 17 Nov 2026 — Project Initialization & Guardrails (Phase 0)

### Actions Taken
- Read `PROJECT_BLUEPRINT.md` in its entirety as the single source of truth.
- Configured `.gitignore` adhering strictly to Section 11.2 (ignoring all models, binary weights, SQLite databases, caches, and environment secrets).
- Configured `.env.example` adhering to Appendix C (defaulting to offline mode, zero required keys).
- Configured `README.md` skeleton following the 14 required sections in Section 19.1.
- Initialized git repository on branch `main`, staged initial files, and committed with message `"Add blueprint, .gitignore, README skeleton, .env.example"`.
- Paused git push per user safety instructions until explicit approval received.
- Upon receiving `"push"`, pushed commit `8160b7a` to `origin main`.
- Verified with `git branch -a` and `git ls-remote --heads origin` that **only** the `main` branch exists locally and on remote.
- Authored comprehensive `ARCHITECTURE.md` covering the modular monolith topology, dual-adapter static-first deployment, the 5 association states, safety invariants I1–I5, temporal engine, playbook similarity formulation, counter-evidence engine, risk contribution ledger, and preflight specification.
- Authored `TASK_TRACKER.md` enumerating Phases 0 through 8 with exact "Done means" checkpoints and mandatory deployment milestones.

### Preflight & Size Check
- Commit: `8160b7a`
- Active branch: `main`
- Remote branches: `origin/main` only

### Next Step
- Submit implementation plan and await user approval before writing any application code.

---

## Session 2: 17 Nov 2026 — Phase 1 audit and gap closure

### Prompts used
1. Read the blueprint, architecture and tracker; run `git status`/`git log`; compare the tracker with the code; report what is done and missing in Phase 1; create `CLAUDE.md` with the standing rules; write no application code; wait.
2. Follow-up rules and autonomy grant: author commits as `ShriyaP1966`, no AI attribution, never `git push`, never rewrite history; fix the Phase 1 gaps independently, run preflight before every commit, stop and ask only for deletions, new dependencies, outside-repo access, near-limit size or secrets in git, and sign-ins; do not start Phase 2.

### Audit findings (the tracker showed nothing ticked, but a large commit `a0b0d0d` already existed)
- **Critical:** `.gitignore` rule `models/` also ignored `backend/app/models/`, so the ORM package was never committed and a fresh clone could not start the API.
- **Fabricated demo data:** `export_static_demo.py` and the static adapter contained hand-typed values (risk 78/72/10, an invented SHA-256, a six-stage fingerprint, an F2 factor the code never produced). Real pipeline output is 60/60/0.
- **Deployment config:** Render used `rootDir: backend` with `app.main:app` (cannot import `backend.*`/`ai_engine.*`); no startup seeding on an ephemeral disk; the health probe ignored `VITE_API_BASE_URL` and would treat an SPA HTML 200 as a live backend.
- **UI vs spec:** graph was a card list, not React Flow; inspector review buttons had no backend; detail page showed invented tactic stages; several copy claims overstated behaviour.
- **Logic:** risk cues matched substrings (`fir` inside `confirm`), a bank mention counted as authority impersonation, F3 ignored the ELEVATED condition, I1 check was a tautology, extraction ran on un-normalised text (zero-width characters could evade matching), URL canonicalisation kept trailing punctuation and `www.`, error bodies did not follow the standard format and 500s leaked exception text.
- **Not implemented, not in Phase 1 scope:** redaction of OTP/password/card numbers at ingestion (§5.5), rate limiting (§9/§10), `relationships` table population.

### Work done (all local commits, nothing pushed)
`56d83e2` track ORM package + CLAUDE.md · `90fb82a` backend hardening and tests · `a84b289` demo data from the real pipeline · `33b4f70` deployment fixes · `733e8cf` frontend slice · plus the documentation commit that contains this entry.

### Verification (actual results)
- `pytest -q`: 54 passed. `ruff check backend ai_engine scripts`: all checks passed.
- `npm test`: 19 passed. `npm run build` (tsc + vite): succeeded.
- Render-style boot (`uvicorn backend.app.main:app` from the repo root, `SEED_ON_START=true`, real socket): `/health` ok, 3 incidents (risk 0/60/60), one `OBSERVED_MATCH` edge, CORS restricted to the configured origin, standard 404 body.
- `python scripts/preflight.py --quick`: all checks passed before every commit (M1 about 0.5 MB, M2 about 0.2 MB).
- **Not verified:** no browser was available, so the UI has not been clicked through; public deployment not done (needs the owner's Vercel/Render sign-in); Antigravity quota not logged (owner action).

### Next Step
- Owner pushes the local commits, deploys the slice (see `deployment/DEPLOY.md`), logs the Antigravity quota, and approves before Phase 2 starts.
