# CLAUDE.md — VIGIL standing rules

Source of truth: `PROJECT_BLUEPRINT.md`, `ARCHITECTURE.md`, `TASK_TRACKER.md`. If code and these docs disagree, the docs win unless the user says otherwise. These rules apply to every session.

## Environment
- Windows 11, PowerShell is the primary shell. Do not use Linux-only commands (`tail`, `head`, `grep`, `sed`, `rm -rf`, `export`). Use `Select-Object -Last N`, `Select-String`, `Remove-Item`, `$env:VAR`, or the dedicated Read/Grep/Glob tools.
- Python: use the repo venv, `.\.venv\Scripts\python.exe`. Run Python tools from the repo root (`C:\Projects\VIGIL`).
- Work only inside `C:\Projects\VIGIL`.

## Repository rules (blueprint C2, §11)
- Repo size stays under 10 MB (aim under 5 MB). Never commit large files and delete them later: history keeps them.
- Single branch: `main`. No other branches locally or on the remote.
- Never commit secrets, `.env`, `*.db`/`*.sqlite*`, `.venv/`, `node_modules/`, `dist/`, trained models or media. Only `.env.example` (empty values) is allowed.
- Run `python scripts/preflight.py` before every commit and before every push. Fix failures; do not bypass.
- Product wording: the playbook fingerprint recognises a *script family / playbook*, never a specific group, person or organisation.
- Commit specific paths (`git add <paths>`), check `git status` and `git diff --cached --stat` first.

## Git rules (user-mandated)
1. Every commit is authored as `ShriyaP1966 <shriyapatil1966@gmail.com>`. Before any commit, check `git config user.name` and `git config user.email`. If they differ, set them for this repo only (`git config --local`, never `--global`) and tell the user.
2. No `Co-Authored-By` lines, "Generated with Claude Code" lines, or any other Claude/AI attribution in commit messages or PR descriptions. Plain commit messages only.
3. May push to origin main only after preflight and all tests pass. Never force-push, never push any other branch, never rewrite history.
   - Before each push run `python scripts/preflight.py` and the full test suites; if anything fails, do not push.
   - Pushes go out under the user's own identity (`ShriyaP1966 <shriyapatil1966@gmail.com>`), using the credentials already configured on this machine. Never change the author, never use any other credentials, never add `Co-Authored-By` or any Claude attribution.
   - If git asks for a sign-in or the push is rejected, stop and tell the user exactly what it said. No workarounds, never `--force`.
   - Push after each phase is finished and verified (and after any explicit request), then show that `git ls-remote --heads origin` lists only `main` and that `git log origin/main` matches local.
   - Commit locally after each numbered work item.
4. Never amend, rebase or rewrite existing commits. Never force-push.

## Autonomy
Work independently within the approved phase; do not wait for approval on each step. Edit files, add tests, run pytest/ruff/Vitest/preflight and make local commits freely, following the blueprint. Fix failures and re-run until checks pass.

Stop and ask the user first ONLY if an action would:
- delete files or folders, or kill processes;
- install a dependency that is not already in the blueprint;
- touch anything outside `C:\Projects\VIGIL`;
- put the repo near the 10 MB limit, or add secrets, `.env`, `.db`, `.venv`, `node_modules` or `dist` to git;
- need the user to sign in to something (Vercel, Netlify, Render, GitHub).

**Phase gate:** do not start the next phase until the user approves. When a phase's gaps are closed and checks are green, stop and summarise (what changed, preflight output, commits made).

## Product and safety rules
- **Offline first (C6):** the app must run fully offline with no API keys. Gemini is an optional enhancement that falls back to the rule/ML extractor.
- **Free static-first deployed link (C8, §14):** a free, public, static-first deployed link is required. It must work with the backend asleep (precomputed JSON via `StaticApi`). No paid hosting, no card.
- **`OBSERVED_MATCH` is never a confirmed campaign.** It only means the same normalised identifier appeared in two evidence records. A campaign is always a *hypothesis* until an analyst accepts it. Never write "confirmed campaign", "criminal", "guilty", or "real-time call protection" in UI or reports.
- **Safety invariants I1–I5 must always hold and stay unit-tested:**
  - I1: `OBSERVED_MATCH` only when normalised identifiers are exactly equal.
  - I2: no fingerprint, ML or Gemini output can create `OBSERVED_MATCH` or `ANALYST_VERIFIED_ASSOCIATION`.
  - I3: `ANALYST_VERIFIED_ASSOCIATION` requires an explicit analyst review recorded in `reviews`.
  - I4: a campaign is presented as a hypothesis until an analyst accepts it.
  - I5: every association has at least one evidence reference and a plain-language explanation; counter-evidence is stored separately and shown next to it.
- **Never fabricate results (C7):** no metric, score, test output or demo number that a script or test did not actually produce. Report test output as it is, including failures. Static demo data must be generated by `scripts/export_static_demo.py` from real pipeline output, never hand-typed.
- All data is synthetic and labelled synthetic (C5). Untrusted text is never rendered as HTML and URLs are never fetched.
- Risk is an experimental heuristic, not a probability; contributions must sum exactly to the displayed score.
