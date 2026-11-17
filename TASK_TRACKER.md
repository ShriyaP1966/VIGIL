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
| **Phase 4** | Counter-Evidence, Risk Ledger, Inspector | 21 Nov 2026 | ⚪ Pending | - |
| **Phase 5** | Dataset v2, Evaluation & Rotation Hero Experiment | 22 Nov 2026 | ⚪ Pending | Static demo data generator export |
| **Phase 6** | UI Completion, Call Simulation, QA | 23 Nov 2026 | ⚪ Pending | **Final Production Deployment** (Dual-mode) |
| **Phase 7** | Documentation, Video, Fresh-Clone & Submit | 24 Nov 2026 | ⚪ Pending | **Deployed Link Public Verification** |
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
- [ ] Implement `counter_evidence` table and rules CE-1 through CE-8 (§6.10).
- [ ] Author public identifier allowlist in `data/public_identifiers.json` (official helplines, bank domains).
- [ ] Implement confidence adjustment logic; enforce invariant that HIGH severity findings set status to `DISPUTED_ASSOCIATION`.
- [ ] Implement full Risk Engine with configurable weights (`config/risk_weights.json`) and persisted factor contributions.
- [ ] Implement `GET /associations/{id}` inspector endpoint returning complete payload (§9).
- [ ] Frontend Evidence Inspector: side-by-side excerpt comparisons, normalisation details, component score breakdown, counter-evidence panel, review controls.
- [ ] Seed scenarios testing counter-evidence: public helpline reuse (CE-3), chronology inversion (CE-1), conflicting payment destinations (CE-2).

#### Done Means Checkpoint
- [ ] Unit tests pass for each counter-evidence rule (both positive trigger and negative control cases).
- [ ] A HIGH severity finding transitions an association to `DISPUTED_ASSOCIATION` and renders a warning marker in the graph.
- [ ] Counter-evidence findings remain visible and prominent even after an analyst manually accepts an association.
- [ ] Risk contributions in `risk_contributions` sum exactly to the displayed 0–100 score.
- [ ] The Evidence Inspector renders all required fields (§12.5.1) for associations, entities, and incidents.
- [ ] Hand-written held-out evaluation set remains completely untouched.

---

### Phase 5 — Dataset v2, Evaluation & The Rotation Experiment (22 Nov)
**Objective:** Rigorous scientific evaluation, multi-seed benchmark execution, and the hero rotation chart.

#### Tasks
- [ ] Dataset generator v2: full campaign templates (6 templates × 12–15 variants), 40 legitimate negatives, 20 decoys, 10 injection attacks.
- [ ] Author the 25 hand-written held-out evaluation scenarios (written by hand, never seen during training).
- [ ] Implement test harness `scripts/evaluate_model.py` supporting suites: `tactics`, `entities`, `associations`, `rotation`, `injection`, `heldout`, `latency`.
- [ ] Execute Hero Rotation Experiment (E4): compare Arms A, B, C, D across rotation levels $r \in \{0.0, 0.25, 0.5, 0.75, 1.0\}$ across $\ge 10$ seeds.
- [ ] Calculate Pairwise F1, False Association Rate, and Candidate Precision/Recall.
- [ ] Implement `scripts/plot_results.py` to generate rotation benchmark chart PNG (< 200 KB).
- [ ] Author `docs/EXPERIMENTS.md`, `docs/DATASET_CARD.md`, and `docs/MODEL_CARD.md`.
- [ ] Scenario Lab API (`GET /scenarios`, `POST /scenarios/{name}/run`).

#### Done Means Checkpoint
- [ ] Every metric in `docs/EXPERIMENTS.md` is reproducible via CLI with recorded seeds.
- [ ] False association rate and candidate precision/recall explicitly reported for all arms.
- [ ] Suite E3 confirms zero false `OBSERVED_MATCH` edges across all decoys and negatives.
- [ ] Hand-written held-out suite evaluated exactly once and logged.
- [ ] Honest scientific interpretation documented (highlighting rotation regimes where Arm D excels vs. where it degrades).
- [ ] Generated rotation chart PNG committed (< 200 KB).

---

### Phase 6 — UI Completion, Simulated Live Call Analysis, QA (23 Nov)
**Objective:** Polished, accessible dark enterprise interface; interactive call simulation; feature freeze.

#### Tasks
- [ ] Complete Overview dashboard: real database KPI cards, activity feed, graph snapshot.
- [ ] Complete Investigations list with search and risk filters.
- [ ] Complete Campaigns page: side-by-side playbook sequence alignment, member list, review actions.
- [ ] Complete Scenario Lab UI: scenario selector, rotation slider, deterministic run/replay, expected vs. actual diff.
- [ ] Complete Reports view: structured exports (Observed Facts, Model Inferences, Analyst Actions, Counter-Evidence, Limitations) in JSON and CSV.
- [ ] Complete Settings view: processing mode selector, transparency disclaimers, **"Clear all local data"** action (`DELETE /data`).
- [ ] Implement **Simulated Live Call Analysis** page:
  - Prominent disclaimer banner: *"Simulation: scripted transcript playback. VIGIL does not intercept or listen to real calls."*
  - Progressive streaming transcript with tactic keyword highlighting.
  - Interactive 6-stage tracker chips lighting up in sequence.
  - Live heuristic risk gauge with real-time contribution list.
  - Multi-lingual guidance cards (English and Hindi).
  - Adversarial injection demonstration showing safety badge activation.
- [ ] Comprehensive UI states: loading skeletons, empty states, error banners, success toasts.
- [ ] Accessibility: WCAG AA contrast, visible focus rings, ARIA labels, alternative accessible Table View for the graph canvas.
- [ ] Implement `scripts/export_static_demo.py` to compile demo JSON bundles into `frontend/public/demo-data/`.
- [ ] Client API dual-adapter (`HttpApi` + `StaticApi`) with automatic sleeping backend detection and UI badge.
- [ ] **Deployment Milestone:** Final deployment to Vercel and Render. Verify static fallback behavior when backend is stopped.
- [ ] Declare formal **Feature Freeze** in `DEVELOPMENT_LOG.md`.

#### Done Means Checkpoint
- [ ] Every button, filter, and modal functions correctly across the entire application.
- [ ] Every association edge has an explainable reason and triggers the Evidence Inspector.
- [ ] Simulated Live Call Analysis operates completely offline and showcases real-time stage progression.
- [ ] Keyboard-only navigation completes the core investigation workflow.
- [ ] Zero unhandled JavaScript console errors on any route.
- [ ] **Public Deployed Link verified:** Application operates seamlessly from a remote device in incognito mode with backend sleeping and awake.
- [ ] Feature freeze formally committed to repository.

---

### Phase 7 — Documentation, Demo Video, Fresh-Clone Test, Submit (24 Nov)
**Objective:** Flawless submission package, verified fresh clone, and final submission.

#### Tasks
- [ ] Finalise `README.md`: include verified live demo URL, architecture diagram, methodology, and honest benchmark tables.
- [ ] Finalise all documentation: `ARCHITECTURE.md`, `API_SPEC.md`, `PRIVACY.md`, `DATASET_CARD.md`, `MODEL_CARD.md`.
- [ ] Capture and compress UI screenshots ($\le 8$ images, each $< 200\text{ KB}$).
- [ ] Record 3-minute demo video following §19.2 script; host externally (YouTube/Drive); add link to README.
- [ ] Execute **Fresh-Clone Test** (§11.5) in a clean directory outside the project.
- [ ] Run `python scripts/preflight.py --history`: verify M1, M2, and M3 size limits; verify zero historical secrets or blobs $> 1\text{ MB}$.
- [ ] Verify deployed link from an independent smartphone on cellular data.
- [ ] Validate submission requirements on Hack2skill dashboard (§0.2).
- [ ] Execute formal submission (Attempt 1 of 2).

#### Done Means Checkpoint
- [ ] Fresh clone successfully sets up and runs offline using only README instructions with zero API keys.
- [ ] `preflight.py --history` passes all checks (M1 < 8 MB, M2 < 9 MB, M3 < 9 MB, only `main` branch).
- [ ] Public GitHub repository confirmed accessible in logged-out private browser session.
- [ ] Live deployed link loads instantly, demonstrates all features, and displays appropriate mode badges.
- [ ] Submission successfully recorded on competition portal before evening of 24 Nov.

---

### Phase 8 — Buffer & Emergency Fallback (25 Nov)
**Objective:** Final review; address critical issues only.

#### Tasks
- [ ] Monitor public deployment stability.
- [ ] Verify submission receipts.
- [ ] If and only if a genuine submission defect is identified, use Attempt 2.
