# VIGIL v3.1 — Master Task & Milestone Tracker

> **Execution Protocol:** Work one phase at a time (§15). Prove each phase's **Done means** before proceeding to the next.
> **Deployment Rule:** A free public deployed link is mandatory. First slice deployed at the end of Phase 1, final deployment in Phase 6, verification in Phase 7.
> **Repository Rules:** Main branch only, repository size strictly < 10 MB, offline mode 100% operational with no API keys, zero fabricated numbers.

---

## Progress Overview

| Phase | Description | Target Date | Status | Deployment Milestone |
|---|---|---|---|---|
| **Phase 0** | Foundation & Guardrails | 17 Nov 2026 | ✅ Done (browser walk-through of placeholder pages not recorded) | Deployment scaffold (`deployment/`) |
| **Phase 1** | Vertical Slice 1 (Ingest → Match → Graph) | 18 Nov 2026 | 🟡 Code complete, 2 items open: public deployment (needs Vercel/Render sign-in), in-browser walk-through. Antigravity quota log waived by owner (build moved to Claude Code) | **First Slice Deployed** (Vercel + Render): *not yet* |
| **Phase 2** | Intelligence Core (Tactics, Guard, Data v1) | 19 Nov 2026 | ✅ Done as scoped by the owner (Gemini, scikit-learn tier and delimiter sandboxing cut); UI not yet viewed in a browser | - |
| **Phase 3** | Associations, Temporal & Playbook Engine | 20 Nov 2026 | ✅ Done as scoped by the owner (dwell, fuzzy candidates, CE-8, side-by-side UI and graph hull cut); UI not yet viewed in a browser. **Finding:** the fingerprint recognises a script family, not a campaign instance (see DEVELOPMENT_LOG Session 5) | - |
| **Phase 4** | Counter-Evidence, Risk Ledger, Inspector | 21 Nov 2026 | ✅ Done as scoped by the owner (CE-6, CE-8, F4, `risk_weights.json` and fuller node inspectors deferred; CE-4 minimal); UI not yet viewed in a browser | - |
| **Phase 5** | Dataset v2, Evaluation & Rotation Hero Experiment | 22 Nov 2026 | ✅ Done as scoped by the owner (E8 cut), and the held-out set (E6) was run once on 19 Nov 2026 (18 of 19 scam scenarios detected, 2 of 6 legitimate falsely flagged). **Findings:** identifier arms collapse at r = 1; the fingerprint recovers links but over-merges (false association rate 0.23-0.34) and does not beat the text baseline under the instance truth; decoys D1 and D3 were linked by candidate links (see docs/EXPERIMENTS.md) | Static demo data generator export (unchanged, re-verified) |
| **Phase 6** | UI Completion, Call Simulation, QA | 23 Nov 2026 | ✅ Done as scoped, except the owner's remote-device check and the Render backend (needs sign-in). Feature freeze declared. Post-hoc tuning experiment reported separately (EXPERIMENTS.md section 10) | **Final Production Deployment** (Vercel on push; Render pending) |
| **Phase 7** | Documentation, Video, Fresh-Clone & Submit | 24 Nov 2026 | 🟡 Assistant's items done (README, docs, screenshots, demo script, fresh-clone, history audit, deployed-link script check). Owner's items remain: record the video, phone check, make the repo public, submit (the licence is added) | **Deployed Link Public Verification** (script done; phone check pending) |
| **Phase 8** | Buffer & Emergency Fallback | 25 Nov 2026 | ⚪ Pending | Standby monitoring |

---

## Phase Details & "Done Means" Checklists

### Phase 0 — Foundation & Guardrails (17 Nov)
**Objective:** Clean, runnable skeleton with guardrails that ensure repository integrity and submission compliance.

#### Tasks
- [x] Initialise git repository on branch `main` and link remote `origin`.
- [x] Create `.gitignore` per §11.2 (no models, no databases, no caches, no secrets).
- [x] Create `.env.example` per Appendix C (offline default, empty Gemini placeholders).
- [x] Create `README.md` skeleton per §19.1.
- [x] Author comprehensive `ARCHITECTURE.md` with dual-adapter deployment specification.
- [x] Author `TASK_TRACKER.md` with phases and exact Done-means checkpoints.
- [x] Formulate Pinned Free-Only Dependency Plan and Lockfile Strategy.
- [x] Establish System Risk Register with mitigations.
- [x] Author `DEVELOPMENT_LOG.md` template for session audit logs.
- [x] Implement `scripts/preflight.py` per §11.3 (three size measures M1/M2/M3, branch checks, secret scans, history scan).
- [x] Implement `scripts/install_hooks.py` to configure local pre-push git hook. *(Script exists; the hook is local to each clone and is installed by running it.)*
- [x] Backend skeleton: FastAPI app, `/health`, CORS, request-ID middleware, standard error handler `{error: {code, message, request_id}}`. *(Error body now also covers HTTP and validation errors.)*
- [x] Database scaffold: SQLite connection via SQLAlchemy 2, base models.
- [x] Frontend skeleton: Vite + React + TypeScript + Tailwind CSS with dark enterprise tokens (§12.2).
- [x] Frontend shell layout: persistent sidebar, top navigation bar, inspector panel, state-based page switching with placeholders. *(No URL router; views are switched in `App.tsx`.)*
- [x] Deployment scaffold: `deployment/render.yaml`, `deployment/vercel.json`, `deployment/DEPLOY.md`. *(Corrected on 17 Nov: Render must run from the repo root.)*
- [x] Test configuration: pytest + Ruff configured for Python; Vitest configured for React.

#### Done Means Checkpoint
- [x] `pytest -q` passes. *(54 passed on 17 Nov.)*
- [x] `npm test` passes. *(19 passed; logic tests only, no DOM component tests because no DOM test library is in the blueprint.)*
- [x] `GET /health` returns `status: ok`, `mode: offline`, `version: 3.1.0` (plus a timestamp).
- [ ] Frontend loads and navigates all placeholder views without console errors. *(`tsc` and `vite build` pass; not yet walked through in a browser.)*
- [x] `python scripts/preflight.py --quick` exits with code 0.
- [x] Commit pushed to `origin main`. *(`a0b0d0d` was on origin at the start of the 17 Nov session; later local commits wait for the owner's push.)*
- [x] `git branch -a` and `git ls-remote --heads origin` confirm that **only** the `main` branch exists.

---

### Phase 1 — Vertical Slice 1: Paste → Entities → Observed Match → Graph → Score (18 Nov)
**Objective:** A functional end-to-end path demonstrable on screen, deployed publicly early.

#### Tasks
- [x] Endpoints: `POST /incidents`, `POST /incidents/{id}/evidence`, `POST /analyze/{id}`, `GET /incidents/{id}`, `GET /graph` (plus `GET /incidents`, `GET /associations/{id}`, `DELETE /data`).
- [x] Text normalisation (Unicode NFKC, zero-width stripping, whitespace collapsing, SHA-256 of the original). Extraction runs on the normalised text. *(Case folding is applied to canonical identifiers, not to stored text.)*
- [x] Deterministic regex & gazetteer entity extraction (Phone E.164, UPI handle, Email, URL, Domain, Organisation).
- [x] Persist entities and mentions. *(The `relationships` table exists but is not populated; structural edges are derived from mentions at graph time.)*
- [x] Implement `OBSERVED_MATCH` association generation for exact shared normalized identifiers with source evidence excerpts.
- [x] Implement baseline additive risk calculation storing factor contributions in `risk_contributions` (placeholder cues; replaced by the tactic classifier in Phase 2).
- [x] Frontend New Investigation: paste transcript/message → creates incident → navigates to Detail. *(Needs the live backend; disabled in the hosted static demo.)*
- [x] Frontend Investigation Detail: masked entities, tactic timeline placeholder (marks no stages until Phase 2), risk badge with contribution list.
- [x] Frontend Intelligence Graph: React Flow canvas showing incident nodes, entity nodes, and solid `OBSERVED_MATCH` edges.
- [x] Minimal Evidence Inspector: opening on node/edge click showing source evidence excerpts.
- [x] Seed script (`scripts/seed_demo.py`) with 3 synthetic incidents (two sharing a UPI ID, one isolated).
- [ ] **Deployment Milestone:** Deploy frontend to Vercel and backend to Render. Document URLs in `deployment/DEPLOY.md`. Resolve all CORS and bundle build errors. *(Blocked: needs the owner's Vercel and Render sign-in. Config and docs are ready; a Render-style boot was verified locally.)*

#### Done Means Checkpoint
- [x] Pasting a synthetic transcript generates an incident and displays masked entities (e.g., `+91 98•••••10`). *(Verified through the API in `test_api_slice.py`; UI not yet walked through in a browser.)*
- [x] The graph displays a solid sky-blue `OBSERVED_MATCH` edge labeled `"observed match"` between two incidents sharing a UPI handle. *(Verified by API and layout unit tests; not yet seen in a browser.)*
- [x] Clicking the edge opens the inspector, displaying the shared identifier and source evidence excerpts. *(Inspector payload verified by API test; click wiring type-checked and built, not yet clicked in a browser.)*
- [x] The third unrelated incident remains disconnected in the graph. *(API test and layout test.)*
- [x] Unit tests pass verifying entity extraction and invariant I1 (no `OBSERVED_MATCH` without exact normalized equality).
- [x] ~~Antigravity weekly quota inspected in **Settings → Models** and logged.~~ **Waived by owner: build moved to Claude Code.**
- [ ] **First slice deployed publicly:** Deployed link opens on an external device and renders the interactive slice. *(Blocked on sign-in, see above.)*

---

### Phase 2 — Intelligence Core: Tactics, Extractors, Injection Guard, Dataset v1 (19 Nov)
**Objective:** Evidence-grounded tactic classification, prompt-injection defense, and the initial synthetic dataset.

#### Tasks
- [x] **Secret redaction at ingestion (§5.5), done first as agreed on 17 Nov** (owner-approved scope: OTP, PIN, CVV, passwords, card and Aadhaar numbers; phones, UPI handles and bank account numbers kept). `ai_engine/privacy/redaction.py`, schema-boundary validators plus a fail-closed service backup, `redactions` table, UI note, leak tests for DB, API responses, logs and error paths. Best effort; limits are documented in the README.
- [x] `Extractor` Protocol and Pydantic schemas in `ai_engine/extraction/interface.py` (extended with per-label spans).
- [x] Rule-based extractor `RuleExtractor` (`ai_engine/extraction/rule_extractor.py`): Appendix A lexicon rules, offline, deterministic. **The scikit-learn tier was cut by the owner**, so there is no `RuleMLExtractor` ML component.
- [x] Lexicon in `data/lexicon.json` (English, Hinglish, a few Devanagari Hindi and Marathi patterns), generated from `scripts/build_lexicon.py`.
- [~] ~~`GeminiExtractor`~~ **Cut by the owner** (deadline). `fallback_used` stays `false`; the offline path is the only path.
- [x] Prompt-injection guard: instruction-detection regex layer, `injection_flags`. **Delimiter sandboxing cut by the owner** (it only matters with an LLM in the loop).
- [x] Risk safety floor: a flagged incident gets no mitigating factor; flagged spans are masked before tactic extraction.
- [x] `scripts/generate_dataset.py` v1: slot templates, rotation parameter, validator. *(Built-in name lists; Faker was not installed or needed.)*
- [~] ~~`scripts/train_classifier.py`~~ **Cut by the owner** along with the scikit-learn classifier.
- [x] `tactic_events` persisted with confidence and span; replaced on re-analysis. Stage-based risk (F1/F2/F3/M1-M3) with an exact-sum ledger, `risk@3.1.1`.
- [x] Frontend: tactic timeline, highlighted transcript spans, manipulation-attempt badge. *(Built, type-checked and logic-tested; not yet viewed in a browser.)*

#### Done Means Checkpoint
- [x] `python scripts/generate_dataset.py --seed 1` outputs valid JSONL < 1 MB. *(178,584 bytes; 112 incidents; byte-identical on regeneration.)*
- [x] `evaluate_model.py --suite tactics` reports per-label P/R/F1 and macro-F1 on template-held-out splits. *(Classifier training is moot: that tier was cut. Test split, run once on the frozen lexicon: macro-F1 0.964. Dev 0.991, train 0.973. Synthetic same-author data, so optimistic. See DEVELOPMENT_LOG.md Session 4 for the weak spots.)*
- [x] Pipeline runs 100% offline with no API key configured.
- [x] ~~Invalid Gemini key or timeout falls back to the rule extractor.~~ **Not applicable: Gemini was cut.**
- [x] 10 adversarial injection test transcripts trigger the manipulation badge with zero reduction in computed risk. *(10/10 flagged, labels and risk unchanged; the attacks are the developer's own, so this is optimistic; limitations are documented.)*
- [x] Investigation Detail highlights exact text spans for extracted tactics. *(Implemented and unit-tested; not yet viewed in a browser.)*

---

### Phase 3 — Associations, Temporal Engine, Fingerprint, Campaign Hypotheses (20 Nov)
**Objective:** Playbook fingerprinting and campaign hypotheses with safety invariants I1–I5 strictly enforced.

#### Tasks
- [x] Association service managing all five states; invariants I1, I2, I3, I5 enforced by ORM listeners. `CANDIDATE_ASSOCIATION` is created, updated or withdrawn by the engine; `ANALYST_VERIFIED_ASSOCIATION` / `REJECTED_ASSOCIATION` only through a review; `DISPUTED_ASSOCIATION` through an analyst FLAG (the rule-based path comes with the counter-evidence engine in Phase 4).
- [x] `reviews` audit table in use; `POST /associations/{id}/review` and `POST /campaigns/{id}/review` (notes are redacted before storage).
- [~] Temporal Engine, **reduced by the owner's cut line**: stage sequence derivation and partial-sequence handling are done (Phase 2 fingerprint + containment). **Dwell profile and recurrence window are cut/deferred** (CE-8 moves to Phase 4).
- [x] Playbook fingerprint similarity (LCS, containment with damping, relative order, composite) per §6.7; dwell similarity omitted and the weights renormalised, as the blueprint allows.
- [x] Association gate: both incidents need >= 3 distinct stages and LCS >= 3, then similarity >= `T_candidate` (0.75, from settings; not tuned).
- [x] Campaign hypothesis builder: components over observed/verified links extended by candidate links, member basis, mean link confidence, weakest link, excluded (disputed/rejected) links. *Deviation:* a group connected only by candidate links is also a hypothesis (behaviour-only).
- [x] Frontend: candidate edges labelled with similarity, legend, inspector with review controls, Campaigns list and detail. *(Built, type-checked and unit-tested; not yet viewed in a browser. The side-by-side playbook comparison and the graph hull are cut.)*
- [~] Fuzzy-identifier candidates: **cut** (not needed for the headline experiment).

#### Done Means Checkpoint
- [x] Property tests enforce I1 (observed matches equal an independent oracle of shared exact identifiers) and I2 (fingerprints cannot create observed or verified states), at rotation 0, 0.5 and 1.0, on train and dev data only.
- [x] A rotated-identifier scenario produces a `CANDIDATE_ASSOCIATION` edge with component scores (graph edge is dashed amber in the UI layout; not yet seen in a browser).
- [x] Decoys fail the gate: legitimate incidents are never linked, the same tactics in reverse order and look-alike benign notices stay unlinked. *(Only hand-built decoys so far; the full decoy set is Phase 5.)*
- [x] Cut-off partial sequences match through containment (LCS equals the fragment, containment 1.0).
- [x] `ACCEPT` sets `ANALYST_VERIFIED_ASSOCIATION` and writes a `reviews` row; the data layer refuses the status without one (I3).
- [x] All campaign views and API outputs use the term "hypothesis"; tests scan API output and source files for forbidden wording (I4).
- [x] All unit and integration tests pass. *(354 backend, 34 frontend.)*

---

### Phase 4 — Counter-Evidence Engine, Risk Ledger, Evidence Inspector (21 Nov)
**Objective:** Explain why incidents might *not* be connected; provide complete evidence traceability.

#### Tasks
- [x] `counter_evidence` table in use; rules **CE-1, CE-2, CE-3, CE-5, CE-7 implemented, CE-4 minimal** (fires only on a low-confidence extraction, which the current extractor never produces, so it is exercised by a test that lowers a mention's confidence). **CE-6 and CE-8 deferred** (recorded as such in `config/counter_evidence_rules.json`). Severities and impacts are a-priori priors, in config.
- [x] Public identifier allowlist `data/public_identifiers.json` (national cyber crime helpline 1930 plus 15 official domains; exact or subdomain match, look-alike domains do not match). *Non-exhaustive; each entry must be verified against its official source by whoever maintains the list.* Required a narrow extraction of "helpline 1930" so a shared public helpline is a real observed match for CE-3 to dispute.
- [x] Confidence adjustment `clip(base + sum of impacts, 0, 1)`; any HIGH finding sets a system-created association to `DISPUTED_ASSOCIATION`; a system dispute reverts when no HIGH finding remains; analyst decisions are never overridden; the risk ledger is recomputed when a link flips between observed and disputed so F3 never counts a disputed link.
- [~] Full Risk Engine with `config/risk_weights.json` and the F4 factor: **deferred by the owner's cut line** (weights stay in code, `risk@3.1.1`).
- [x] `GET /associations/{id}` inspector payload now carries findings (with rule version and evidence refs), `dispute` source and the base to adjusted confidence.
- [~] Frontend Evidence Inspector: the counter-evidence panel, dispute and accepted-with-findings notes, component breakdown, stage excerpts and review controls are done. **Fuller entity-node and incident-node inspectors and side-by-side excerpt comparison: deferred by the owner's cut line.**
- [x] Seed scenarios (9 seeded incidents now): CE-3 shared public helpline (adjusted confidence 0.20, disputed), CE-1 chronology inversion (0.45, disputed), CE-2 conflicting payment destinations (0.70 to 0.60, stays observed).
- [x] Findings aggregated on campaign hypotheses (read-time, worst first, severity summary, count and worst severity on the list).

#### Done Means Checkpoint
- [x] Unit tests for each rule, positive and negative (29 pure-rule tests) plus 20 end-to-end tests through the pipeline.
- [x] A HIGH finding transitions an association to `DISPUTED_ASSOCIATION` (tested, with a mutation check); the graph layout renders disputed edges dashed red with a warning label (layout unit-tested; not yet seen in a browser).
- [x] Findings remain visible after an analyst accepts: in the inspector payload and aggregated on the hypothesis, including after accepting the hypothesis itself.
- [x] Risk contributions sum exactly to the score, including after a dispute-triggered recompute (tested on the seeds).
- [~] The Evidence Inspector renders the §12.5.1 fields for **associations**; entity and incident nodes show only a short summary (deferred).
- [x] The hand-written held-out set was never created or touched.

---

### Phase 5 — Dataset v2, Evaluation & The Rotation Experiment (22 Nov)
**Objective:** Rigorous scientific evaluation, multi-seed benchmark execution, and the hero rotation chart.

#### Tasks
- [x] Dataset generator v2: 6 templates × 15 variants, 40 legitimate negatives, 20 decoys (four types), unique identifiers, script-family ground truth; the 10 injection attacks are in `data/injection_attacks.json`. Frozen and pre-registered (`docs/PREREGISTRATION.md`) before any experiment.
- [x] The 25 held-out scenarios exist in `data/heldout/heldout.jsonl` (19 scam, 6 legitimate), drafted by a different language model (not Claude) and reviewed, edited and labelled by the owner, Shriya Patil. Format checked only; **evaluated once** (see below). No per-utterance tactic labels, so tactic-level scores are not measured (scenario-level detection and false-alarm rate only).
- [~] Evaluation harness `scripts/evaluate_model.py`: suites `tactics`, `entities`, `associations`, `rotation`, `injection`, `latency` run and committed; `heldout` is implemented and guarded (refuses an empty file and a second run) but **not run**.
- [x] Hero Rotation Experiment (E4): arms A, B, C, D at r in 0, 0.25, 0.5, 0.75, 1.0, 10 seeds (1001-1010), both ground truths, two scored slices.
- [x] Pairwise F1, false association rate, candidate precision/recall (`docs/experiments/rotation.json`).
- [x] `scripts/plot_results.py` chart PNGs (about 108 KB each, limit 200 KB; matplotlib is a dev-only dependency in `scripts/requirements-dev.txt`).
- [x] `docs/EXPERIMENTS.md` (tables generated from the JSON), `docs/DATASET_CARD.md`, `docs/MODEL_CARD.md`.
- [x] Scenario Lab API (`GET /api/v1/scenarios`, `POST /api/v1/scenarios/{name}/run`): 11 deterministic scenarios replayed through the real pipeline in an isolated database. The Scenario Lab UI and static-mode scenario data are Phase 6.

#### Done Means Checkpoint
- [x] Every metric in `docs/EXPERIMENTS.md` is reproducible via CLI with recorded seeds (a test re-runs one full experiment cell and checks the tables against the JSON; the full E4 takes about 40 minutes).
- [x] False association rate and candidate precision/recall explicitly reported for all arms.
- [~] Suite E3: **0 I1 violations; 0 observed links touch a negative or decoy after counter-evidence** (1848 before it), negatives are never linked. **But decoys D1 (awareness notices) and D3 (reversed order) were linked by behaviour-only candidate links in a large share of runs**, so the blueprint goal that decoys must not form a campaign hypothesis is not met for them. Reported as is; the decoys were not changed.
- [x] Held-out suite evaluated exactly once and logged (19 Nov 2026): **18 of 19 scam scenarios detected (missed H21), 2 of 6 legitimate scenarios falsely flagged (H15, H17)**; tactic-level scores not measured. Not re-run.
- [x] Honest scientific interpretation documented (where D helps and where it degrades), including that D does not beat the text baseline under the instance truth.
- [x] Generated rotation chart PNG committed (< 200 KB).

---

### Phase 6 — UI Completion, Simulated Live Call Analysis, QA (23 Nov)
**Objective:** Polished, accessible dark enterprise interface; interactive call simulation; feature freeze.

#### Tasks
- [x] Overview: real counts from the pipeline (KPI cards), a recent-evidence feed and a graph snapshot (counts of incidents, indicators and observed / candidate / disputed links).
- [x] Investigations list (`/incidents`) with search, risk-level and channel filters, sorting, empty and no-match states.
- [x] Campaigns page: member list with stage chips, **side-by-side playbook alignment grid**, links with counter-evidence, review actions.
- [x] Scenario Lab UI: 11 scenarios by category, rotation slider (any value live; five precomputed levels in the hosted demo), Run and Replay (reports whether a replay is identical), expected-versus-actual table. Failing expectations are shown as "Differs", not hidden.
- [x] Reports: five separate sections (observed facts, model inferences, analyst actions, counter-evidence, limitations), JSON and CSV downloads (CSV neutralises spreadsheet formulas).
- [x] Settings: processing-mode panel (offline rules is the only available mode; the cloud extractor is shown as cut), transparency notes, **"Clear all local data"** with a confirmation step (live backend only; checked end to end in a real browser).
- [x] **Simulated Live Call Analysis**: simulation notice, four scripted synthetic calls (English, Hinglish, injection attempt, genuine bank call), turn-by-turn analysis by the real pipeline, highlighted transcript, six stage chips lighting in sequence, risk meter with contributions, English and Hindi guidance, safety badge on the injection attempt. Works offline and in the hosted demo (precomputed frames).
- [x] UI states: loading skeletons, empty states, error banners with retry, success and error toasts in a live region.
- [~] Accessibility: automated WCAG AA text-contrast audit of nine pages (it found real failures; the muted-text and red colours were fixed), visible focus rings, ARIA labels and meters, graph table view, keyboard-only workflow checked in a browser. **Not** a full audit with a screen reader or axe.
- [x] `scripts/export_static_demo.py` now also exports scenarios (rotation scenarios at five levels), reports (JSON and CSV) and the call simulations; tests check the committed files equal what the endpoints produce.
- [x] Client dual adapter (`HttpApi` + `StaticApi`) with sleeping-backend detection and the mode badge.
- [~] **Deployment milestone:** the Vercel site redeploys on every push (Root Directory `frontend`; the owner reports earlier pushes did not deploy until that was set). **Render (backend) is not set up**: it needs the owner's sign-in. The static fallback was verified in a real browser with no backend.
- [x] Post-hoc tuning experiment (owner-requested, separate from the headline): see docs/EXPERIMENTS.md section 10.
- [x] Formal **Feature Freeze** declared in `DEVELOPMENT_LOG.md` (Session 8).

#### Done Means Checkpoint
- [~] Every button, filter and modal works: the main interactions of every page are exercised by `scripts/qa_browser.mjs` (54 checks static, 50 live); not literally every control.
- [x] Every association edge has an explainable reason and opens the Evidence Inspector (Phases 3-4; re-checked by the browser QA).
- [x] Simulated Live Call Analysis works completely offline and shows stage progression.
- [x] Keyboard-only navigation completes the core workflow (sidebar, list, case, inspector open and close).
- [x] Zero console errors or uncaught exceptions on the 12 routes tested, at 1280 px and 390 px, in static and live mode.
- [ ] **Public deployed link verified from a remote device in incognito with the backend asleep and awake.** Pending: the owner's check on a phone; the local browser QA does not replace it.
- [x] Feature freeze committed to the repository.

---

### Phase 7 — Documentation, Demo Video, Fresh-Clone Test, Submit (24 Nov)
**Objective:** Flawless submission package, verified fresh clone, and final submission.

#### Tasks
- [x] `README.md` finalised for judges: live URL, architecture diagram (Mermaid), pre-registered headline tables first (generated from the JSON, test-checked), the post-hoc row clearly labelled, the held-out result stated plainly including the 2 of 6 false alarms, a limitations section, an AI-assistants note. The quick start now says 9 seeded incidents.
- [x] `ARCHITECTURE.md` rewritten as built; `docs/API_SPEC.md` and `docs/PRIVACY.md` written to match the code; dataset and model cards current.
- [x] Eight screenshots from the live site in `docs/screenshots/` (all under 200 KB; `scripts/capture_screenshots.mjs`).
- [~] 3-minute demo video: **script and shot list written** (`docs/DEMO_SCRIPT.md`, live site and synthetic data only); **recording and upload are the owner's**, then add the link to the README.
- [x] Fresh-clone test on the final code commit (`a3e1fc2`), in an empty directory, no API keys: 481 backend and 140 frontend tests, build and preflight pass.
- [x] `python scripts/preflight.py --history`: M1 4.2 MB, M2 2.2-2.8 MB, M3 pass, secret scan pass, no historical blob over 1 MB (largest 328 KB); independent history scan found no secret-like strings and no `.env`, database or key file.
- [~] Deployed link: checked by script (40 of 40 checks, `scripts/check_deployed.mjs`); **the check from a real phone on cellular data is the owner's** (`docs/FINAL_CHECKLIST.md`).
- [ ] Validate requirements on the Hack2skill dashboard. **Owner.**
- [ ] Formal submission. **Owner.**
- [ ] Make the repository public. **Owner** (checklist in `docs/FINAL_CHECKLIST.md`). The LICENSE (MIT) is added.

#### Done Means Checkpoint
- [x] Fresh clone sets up and runs offline using only the README's instructions with zero API keys (also run in live mode: 50 of 50 browser checks against the clone's own backend, in the earlier clone test).
- [x] `preflight.py --history` passes all checks (M1 < 8 MB, M2 < 9 MB, M3 < 9 MB, only `main`).
- [ ] Public repository confirmed accessible in a logged-out private session. **After the owner flips it.**
- [x] Live link loads, works with no backend, and shows the synthetic-data labels on desktop and phone width (script); deep links survive a refresh.
- [ ] Submission recorded on the competition portal. **Owner.**

---

### Phase 8 — Buffer & Emergency Fallback (25 Nov)
**Objective:** Final review; address critical issues only.

#### Tasks
- [ ] Monitor public deployment stability.
- [ ] Verify submission receipts.
- [ ] If and only if a genuine submission defect is identified, use Attempt 2.
