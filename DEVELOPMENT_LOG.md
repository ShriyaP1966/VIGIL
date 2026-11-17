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
- **Not verified:** no browser was available, so the UI has not been clicked through; public deployment not done (needs the owner's Vercel/Render sign-in); Antigravity quota log: **waived by owner: build moved to Claude Code**.

### Next Step (end of Session 2)
- Owner pushes the local commits, deploys the slice (see `deployment/DEPLOY.md`), and approves before Phase 2 starts.

---

## Session 3: 17 Nov 2026 — Secret redaction at ingestion (§5.5), first Phase 2 task

### Prompt used
Owner asked for a plan, then approved it with these decisions: (1) add Aadhaar numbers; (2) keep bank account numbers, UPI handles and phone numbers un-redacted so matching and CE-2 keep working; (3) hash the redacted text and log the §6.1 departure; (4) schema-boundary redaction plus a service-layer backup, failing closed; (5) new `redactions` table, leave the existing `vigil.db` alone; (6) keep no last-4 digits of cards. Scope kept tight (deadline); stop after redaction and propose a Phase 2 plan. The Antigravity quota item was marked "waived by owner: build moved to Claude Code".

### Decision logged: departure from blueprint §6.1
§6.1 says to "keep the original text unchanged and hash it (SHA-256)". §5.5 says never to store OTPs, passwords, full card numbers or bank credentials. They conflict for text that contains a secret. **§5.5 wins for secrets:** `evidence.original_text` is now the text *as stored, after redaction*, and `sha256` covers that stored text. Hashing the raw text would let anyone recover a 4-6 digit OTP by brute force, and the raw text is not retained, so the hash cannot be checked against the raw source. Text without secrets is stored unchanged.

### What was built
- `ai_engine/privacy/redaction.py`: pure Python (`re`, `unicodedata`), offline, no API key, no new dependency. Kinds: OTP, PIN, CVV, PASSWORD, CARD (Luhn, or a card cue), CARD_EXPIRY, AADHAAR (Verhoeff 4-4-4, or an Aadhaar cue), plus short replies to "tell me the OTP/PIN/password" across lines and speaker turns. Detection runs on an NFKC / zero-width-stripped / digit-script-normalised view; only the secret's span is replaced in the original text. Placeholders carry no length or last-4.
- Schema-boundary validators on `EvidenceCreate` (text, speaker turns, provenance) and `IncidentCreate` (title, notes); service-layer backup in `incident_service` that redacts again before any row is created. Both fail closed (nothing stored on error). Seeds and the exporter go through the same path.
- `redactions` table (kind, field, span in stored text, detector version; never the secret) and `redactions` counts on the incident API; UI note on the detail page and the intake form.
- Tests: 83 in `test_redaction.py` (positive and negative tables, idempotence, spans, property test over 400 random secrets, documented limitations) and 8 in `test_redaction_leaks.py` (DB dump of every table, every API response, all logs and stdout/stderr at DEBUG, 422 / forced-500 / fail-closed / validation-bypass paths, demo data).
- **Mutation check:** with detection disabled, 35 tests failed, including the DB, response and log leak tests; the check was reverted.

### Known limitations (best effort, also in the README)
Spelled-out digits; secrets with no cue word nearby; non-Luhn card numbers without a "card" cue; values after a currency marker are treated as amounts; a 4-6 digit value after "PIN" is redacted even if it was a postal code; a 12-digit-looking value after an Aadhaar cue is redacted even if it is not an Aadhaar; random numbers that happen to pass Luhn/Verhoeff may be redacted. The raw text reaches the server before redaction (use HTTPS, synthetic data); a client-side pass was deliberately not built.

### Incident: test runs touched `vigil.db`
Importing the app in tests ran `create_all` on the default `./vigil.db`, which added one **empty** `redactions` table to the owner's existing database (existing rows were unchanged: 3 incidents, 3 evidence, 1 association). Fixed: `conftest.py` now sets an in-memory `DATABASE_URL` before the app is imported, and a re-run left the file's modified time unchanged. Starting the real backend will add the same empty table (no migration tool by design).

### Verification
`pytest -q`: 145 passed. `ruff check`: clean. `npm test`: 19 passed. `tsc` and `vite build`: succeeded. Demo data regenerated from the real pipeline (now includes `redactions`). (Antigravity quota log: waived by owner: build moved to Claude Code.)
