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
`pytest -q`: 145 passed. `ruff check`: clean. `npm test`: 19 passed. `tsc` and `vite build`: succeeded. Demo data regenerated from the real pipeline (now includes `redactions`).

---

## Session 4: 17 Nov 2026 — Phase 2: intelligence core

### Prompt used
Owner approved Phase 2 in this order: (1) rule-based extractor, lexicon and tactic_events, (2) stage-based risk with an exact-sum ledger, (3) injection guard with the 10-transcript test, (4) dataset generator v1 with validator, (5) tactic timeline in the UI. **Cut by owner:** Gemini extractor, scikit-learn classifier (and `train_classifier.py`), delimiter sandboxing. Keep Hindi/Marathi to a handful. Rules: report metrics honestly, never tune numbers, one local commit per item, no push, preflight and all tests before each commit, re-run the static demo export, update tracker and log, stop at the end with the Phase 3 plan.

### Commits (local, not pushed)
`03c2778` 2.1 extractor, lexicon, tactic_events · `155ca46` 2.2 stage-based risk · `21a6310` 2.3 injection guard · `fcc4bdf` 2.4 dataset generator, validator, evaluation · `a582750` 2.5 UI timeline, highlights, badge · plus the commit containing this entry.

### What was built
- **Extractor:** `RuleExtractor` over `data/lexicon.json` (generated by `scripts/build_lexicon.py`; a test fails if they drift). Rules run on a normalised view (NFKC, zero-width removed) and spans map back to the original text. Victim turns are never scored. Institution class, payment channel and language are derived from the same text. Pasted `Speaker: text` transcripts are split into turns. `tactic_events` are persisted per span and replaced on re-analysis. The `fingerprint` now holds stage order, institution, payment, language and channel (the full temporal engine is Phase 3).
- **Risk (`risk@3.1.1`):** F1 per stage (6/10/14/16/8/18, credential 18) with an explicit +70 cap row, F2 +10 for three stages in canonical order, F3 for observed matches to ELEVATED+ incidents, M1/M2/M3 each limited to what was already added so the score never goes below 0. Every entry cites the utterance that fired and the ledger always sums to the score. Seeded demo: 86 CRITICAL, 58 ELEVATED, 0 LOW.
- **Injection guard:** nine regex rule groups on the normalised view. A flag records `injection_flags`, masks the flagged span before tactic extraction and disables every mitigating factor for that incident.
- **Dataset v1:** 6 templates x 12 plus 40 negatives = 112 incidents, 571 utterances, 178 KB, byte-identical on regeneration. Split by template: train T1/T4, dev T2/T5, test T3/T6. Synthetic-only identifiers; the validator runs every text through the secret redactor.
- **UI:** timeline of the six stages in observed order, highlighted transcript, manipulation badge. Renders text only.

### Metrics (all produced by `scripts/evaluate_model.py`, files in `docs/experiments/`)
Caveat on every number: synthetic data written by the same author as the rules, so scores are optimistic and do not predict real-world performance. The owner's hand-written held-out set is the unbiased check.

| split (templates) | macro-F1 | micro-F1 | stage-sequence exact match |
|---|---|---|---|
| **test** (T3, T6, N5, N6), run once on the frozen lexicon | **0.964** | 0.944 | 0.806 |
| dev (T2, T5, N3, N4), after fixes | 0.991 | 0.990 | 1.000 |
| train (T1, T4, N1, N2), after fixes | 0.973 | 0.982 | 0.921 |

First dev run, before any rule fix: macro-F1 0.956 (FALSE_ALLEGATION precision 0.71, URGENCY recall 0.91, institution accuracy 0.55). I then fixed defects found on dev and train; **the test split was not used for any fix.**

**Test split per label** (support / precision / recall / F1): authority claim 30 / 1.00 / **0.80** / 0.89; allegation 24 / **0.77** / 1.00 / 0.87; threat 11 / 1.00 / 1.00 / 1.00; isolation 10 / 1.00 / 1.00 / 1.00; urgency 21 / 0.91 / 1.00 / 0.96; payment demand 21 / 1.00 / 1.00 / 1.00; credential request 10 / 1.00 / 1.00 / 1.00; benign cue 6 / 1.00 / 1.00 / 1.00; OTHER_SUSPICIOUS: no examples in this dataset, so not scored. Per language micro-F1 on test: English 0.936, Hinglish 0.952, Marathi 1.000 (12 labels, tiny sample). Institution class accuracy 0.75, payment channel accuracy 0.92.

**Where it is weak, stated plainly:**
- *Authority claim recall 0.80 on unseen templates:* 6 misses, all in T3 phrasings the rules do not cover ("I am the nodal officer … at the Department of Telecommunications", "I am …, a TRAI representative").
- *Allegation precision 0.77:* a demand to "pay the customs duty" (T6) is misread as an allegation, because "customs duty" is an allegation cue.
- *Urgency:* the word "tonight" fires urgency on threats such as "will disconnect tonight" / "police will reach your address tonight"; the generator labels those as threats only. This is label ambiguity, not tuned away.
- *Other known ambiguities:* "under digital arrest" counts as threat as well as isolation; "never share it with anyone" in an OTP notice fires isolation when the secret is not named; the institution class is a fixed priority list, so a script that names several agencies gets the first class (institution accuracy is only 0.66-0.75 across the three splits); on train, payment accuracy is 0.66 because the generator labels bank-KYC SMS as link payment even when the message has no link.
- OTHER_SUSPICIOUS has no support in the data and was never evaluated.

**Rule fixes made on dev/train (each generalisable, none on test):** agency names ("Narcotics Control Bureau") no longer count as allegations; URLs are masked before tactic matching (a domain like `duty-pay-748.example` fired a payment demand); "N minutes left" and "dues pending" recognised; "is ready" no longer counts as a benign cue; an authority claim of the form "This is <agency>" was added; "never share your OTP" is no longer isolation. Guard: removed over-broad terms "verified" and "trusted" after a false positive.

**Injection suite:** 10/10 attacks flagged and neutralised (labels and risk unchanged). The extractor is already largely inert to such text, so this mainly proves the guard recognises these phrasings and the mitigation lock works (checked by a mutation test). Documented misses: leetspeak, spaced-out letters, polite paraphrase without trigger words. A real weakness: benign cues appended without any trigger wording can still lower a *demand-free* scam's score by up to 15; scams that request money or credentials are never mitigated.

### Design decisions
- Victim turns carry no tactics, and an unlabelled paste is one utterance (so a victim's reaction inside an unlabelled paste can be scored).
- Mitigations are capped at what was already added, so the ledger stays exact and non-negative (M2 shows -6, not -10, in its single-weak-stage example).
- `weak evidence` means a rule confidence below 0.8 (an a-priori constant).
- Rule iteration used dev and train only; the test split was run once after the lexicon was frozen.

### Verification
`pytest -q`: 275 passed. `ruff check`: clean. `npm test`: 28 passed. `tsc` and `vite build`: succeeded. Two mutation checks: removing the injection flag from the risk call fails the mitigation-lock test; earlier the redactor mutation check still stands. Static demo re-exported from the real pipeline. **Not verified:** the UI has not been viewed in a browser.

---

## Session 5: 17 Nov 2026 — Phase 3: fingerprint, associations, campaign hypotheses

### Prompt used
Owner approved Phase 3 in this order: (1) playbook fingerprint similarity per §6.7 with the gate, (2) association service with all five states, I2 enforced, reviews table and review endpoints (I3), (3) campaign hypothesis builder with /campaigns (I4), (4) UI: candidate edges with similarity %, Campaigns list and detail, (5) tests: I1/I2 property tests, decoys, containment, determinism. **Cut/deferred:** dwell similarity, fuzzy-identifier candidates, CE-8, the side-by-side UI, the graph hull. `T_candidate` stays 0.75 and is not tuned on test. Same rules (honest results, local commits per item, no push, preflight and tests before each commit).

### Commits (local, not pushed)
`4ba02e0` 3.1 fingerprint similarity · `ec928a2` 3.2 association service and review · `c9f2583` 3.3 campaign hypotheses · `c172135` 3.4 UI · `acee4e9` 3.5 property tests · plus the commit containing this entry.

### What was built
- **Fingerprint (`fingerprint@3.1.0`):** LCS, containment (damped by min(1, len/4)), relative-order consistency, institution and payment match; dwell omitted and the weights renormalised (0.65/0.15/0.10 over 0.90). Language and channel are never inputs. Gate: both incidents >= 3 distinct stages and LCS >= 3. Symmetric and deterministic.
- **Association service:** the engine compares each analysed incident with all others and creates, updates or withdraws behaviour-only `CANDIDATE_ASSOCIATION` rows with component scores, one excerpt per stage per incident, and a plain-language explanation. An exact identifier arriving later upgrades a candidate to `OBSERVED_MATCH` (match type COMBINED); an observed pair whose behaviour also matches keeps its single row and gains the playbook scores. Reviews: ACCEPT -> ANALYST_VERIFIED, REJECT -> REJECTED, FLAG -> DISPUTED, with the review row written first.
- **Invariants in the data layer:** ORM listeners raise on a behaviour-only OBSERVED_MATCH (I1/I2), on creating or flipping to an analyst status without a recorded review (I3) and on an association without evidence or explanation (I5).
- **Campaign hypotheses (`campaign@3.1.0`):** components over observed and verified links extended by candidate links; member basis OBSERVED / CANDIDATE / ANALYST; confidence is the mean link confidence, weakest link always shown; disputed and rejected links are excluded but listed. Rebuilds are deterministic and idempotent; analyst-reviewed hypotheses keep their id and status.
- **UI:** candidate edges labelled with similarity, inspector with component breakdown, stage excerpts and live review controls (disabled with an explanation in the static demo), Campaigns list and detail pages. A fourth seeded incident (same script, rotated identifiers) makes the demo show a candidate link: observed link, candidate link at similarity 1.00, one hypothesis of 3 incidents at mean link confidence 0.875 (incident 4 is behaviour-only).

### Decisions and deviations
- **Deviation from the blueprint:** a group connected only by candidate links is also a campaign hypothesis (behaviour-only). Blueprint §6.8 seeds hypotheses on observed matches only, so a campaign whose identifiers were all rotated could never appear.
- No F4 risk factor (candidate association +5): it belongs to the Phase 4 risk engine, and adding it now would need cascading re-analysis.
- A candidate with no remaining support is deleted if no analyst touched it; reviewed hypotheses are kept as history when their links disappear. A hypothesis accepted earlier keeps its status when new incidents join it (membership change since the review is not flagged yet).
- `T_candidate` comes from `settings.T_CANDIDATE` (0.75) and was not tuned.

### Finding to act on: the fingerprint recognises a script family, not a campaign instance
Diagnostic (scratch computation, **train and dev splits only, test split untouched, no tuning**), counting a pair as true when both incidents share `campaign_instance_id`:

| rotation | split | true pairs | candidates | precision | recall |
|---|---|---|---|---|---|
| 0.0 | train / dev | 24 / 24 | 121 / 105 | 0.18 / 0.17 | 0.92 / 0.75 |
| 0.5 | train / dev | 24 / 24 | 90 / 132 | 0.21 / 0.18 | 0.79 / 1.00 |
| 1.0 | train / dev | 24 / 24 | 90 / 124 | 0.18 / 0.18 | 0.67 / 0.92 |

Every false positive is a pair from the SAME template but a DIFFERENT campaign instance (e.g. T1-T1, T4-T4, T5-T5); there were **no cross-template false positives**. In this generator, different instances of one template follow an identical script, so no behavioural method could separate them. Misses are mostly gate failures on cut-off calls with fewer than 3 stages or low-similarity fragments. Consequence for Phase 5: against the blueprint's ground truth (true pair = same `campaign_instance_id`), arm D will show many false associations, so the rotation experiment will probably show it helping recall and hurting precision. This is a property of the data design, not something to tune away. **Decision for the owner before Phase 5:** (a) keep the ground truth and report it honestly, (b) also report a script-family ground truth, and/or (c) give each instance a pre-declared, documented behavioural habit (e.g. its own stage order or optional stage) before any evaluation is run. Whatever is chosen must be fixed before the experiment, not after seeing results.

### Verification (Session 5)
`pytest -q`: 354 passed (1 min 43 s, because the property tests run the real pipeline). `ruff check`: clean. `npm test`: 34 passed. `tsc` and `vite build`: succeeded. Mutation check: weakening the gate (1 stage, LCS 1) fails five tests in three files; reverted. Static demo re-exported from the real pipeline (now includes campaigns). **Not verified:** the UI has not been viewed in a browser. Property and decoy tests use hand-built decoys and the train/dev splits only; the full decoy set and the real association evaluation are Phase 5.

---

## Session 6: 17 Nov 2026 — repo check, push rule, Phase 5 ground-truth decision, then Phase 4

### Repo state check (owner asked, run before any new work)
`git status` clean and up to date with `origin/main`; `git fetch origin` succeeded; `git rev-list --left-right --count origin/main...HEAD` = **0 0** (nothing ahead or behind); GitHub holds all 25 commits up to `bb70b52`; `git ls-remote --heads origin` lists only `refs/heads/main`; local identity `ShriyaP1966 <shriyapatil1966@gmail.com>`. Every commit on GitHub has the email shriyapatil1966@gmail.com; the three earliest (`8160b7a`, `bf933b8`, `a0b0d0d`) carry the name "Shriya Patil" with the same email and were left alone (history is never rewritten). The owner's two pushes had worked.

### Push rule changed by the owner
CLAUDE.md now allows pushing to origin main only after preflight and all tests pass; never force-push, never another branch, never rewrite history; pushes go out under the owner's identity with the credentials already on the machine, with no attribution lines; a sign-in prompt or a rejected push means stop and report; push after each verified phase and show that GitHub matches local.

### Decision recorded BEFORE any Phase 5 experiment: two ground truths, side by side
Phase 5 reports (a) the original **campaign-instance** ground truth (true pair = same `campaign_instance_id`), with its expected low precision stated plainly, and (b) a **script-family** ground truth (true pair = same `campaign_template_id` among campaign incidents; negatives and decoys are non-pairs under both), together in every table and chart and for every arm and rotation level. **Option (c) is rejected:** no behavioural habits, instance-specific phrasing or stage-order quirks are added to the generator after results have been seen; the generator and templates are frozen for the evaluation, and any change is made and logged before results exist. Why: the Session 5 diagnostic (train/dev, precision about 0.2, all false positives within one template, none across templates) shows the fingerprint recognises a script family; changing the data to rescue the headline number would be tuning on results. Recorded in `PROJECT_BLUEPRINT.md` section 8.1 and 8.3 (the original definitions are kept). README and UI copy describe the fingerprint as recognising a script family or playbook, never a specific group, person or organisation.

### Phase 4 (same session): counter-evidence engine
**Prompt used:** build, in order: (1) counter-evidence engine with CE-1, CE-2, CE-3, CE-5, CE-7, confidence adjustment, HIGH sets DISPUTED, findings stay visible after an analyst accepts; (2) seed scenarios for CE-3, CE-1, CE-2; (3) inspector counter-evidence panel and aggregation on hypotheses; (4) tests (one positive and one negative per rule, the DISPUTED transition, visibility after acceptance). CE-4, CE-6, CE-8 minimal or deferred; defer F4, `risk_weights.json` and the fuller node inspectors. Same rules; push at the end of the phase.

**Commits:** `061e1d3` 4.1 engine · `4fd2413` 4.2 seed scenarios · `4502ad3` 4.3 inspector panel and campaign aggregation · `cc06161` 4.4 end-to-end tests · plus the commit containing this entry.

**Built.** Pure rules in `ai_engine/counter_evidence/rules.py` with severities, impacts and thresholds in `config/counter_evidence_rules.json` (priors, not probabilities): CE-1 chronology (>= 3 shared stages, order consistency < 0.6, HIGH, -0.30), CE-2 different payment destination (a shared phone or domain but disjoint UPI handles, MEDIUM, -0.10), CE-3 benign-context identifier (allowlisted public identifier, or an identifier shared with an incident labelled legitimate = benign-cue event and LOW risk; HIGH, -0.40), CE-4 weak extraction (minimal; MEDIUM, -0.15), CE-5 inconsistent impersonation (MEDIUM, -0.10), CE-7 language difference (LOW, -0.02, context only). CE-6 and CE-8 are recorded as deferred. `counter_evidence_service` stores findings, sets `adjusted_confidence = clip(base + sum of impacts, 0, 1)`, makes a system-created link DISPUTED on any HIGH finding, reverts a system dispute when no HIGH finding remains, never overrides an analyst decision, and triggers a risk-ledger recompute when a link flips (so F3 never counts a disputed link). Findings are replaced on every evaluation, so they are never duplicated. Campaign hypotheses aggregate the stored findings at read time (never stale, never hidden by a review). `data/public_identifiers.json` lists the national cyber crime helpline 1930 and 15 official domains (non-exhaustive; entries must be verified by whoever maintains them). To make a shared public helpline testable, a narrow extraction of "helpline ... 1930" / "dial 1930" was added (explicit forms only, never a bare number).

**Bug found and fixed on the way:** `_refresh_risk` first used a bulk delete followed by inserts; SQLite reused row ids while the old objects were still cached, tripping an identity-map warning. It now replaces the ledger through the relationship, and SQLAlchemy warnings are test errors from now on.

**Real seeded outcomes (asserted by tests):** public-helpline link 3-5 DISPUTED by CE-3 (adjusted 0.20 = 0.70 - 0.40 - 0.10 CE-5); chronology link 6-7 DISPUTED by CE-1 (0.45); payment link 8-9 stays OBSERVED with CE-2 (0.70 to 0.60); the Phase 3 links now carry CE-5/CE-7 (1-2: 0.75 to 0.63; the 1-4 candidate: 1.00 to 0.98). Disputed links form no hypothesis; two hypotheses remain (3 incidents, 2 incidents).

**Effect on the generated data (diagnostic, train and dev ingested together, rotation 0.5, test split untouched, no tuning):** 18 observed + 329 candidate + 6 disputed associations. The only disputes (6) are legitimate bank notices that all cite helpline 1930 (CE-3); CE-5 fired on 64 links and CE-7 on 87 (confidence reductions only, no dispute). **The counter-evidence rules do nothing about the script-family finding:** 179 candidate links connect different campaign instances of the same template and none of them is touched by a rule.

**Correction to Session 5.** I wrote that the fingerprint produced "no cross-template false links". That held only because each split contains just two very different templates. With train and dev pooled, 123 candidate links connect different templates: T1-T2 (59; both digital-arrest scripts), T4-T5 (48; the bank-KYC and electricity-bill SMS scripts) and T2-T4 (16; mostly cut-off T2 calls). So the fingerprint links structurally similar scripts, which is what it is designed to do. **Consequence for the Phase 5 decision:** ground truth (b) was recorded as "same `campaign_template_id`", which would count T1-T2 and T4-T5 as false positives even though they are plausibly one family. The owner must fix the family definition (for example an explicit, pre-declared map: digital-arrest = T1, T2, T3; bank-KYC = T4; payment-link = T5; courier-customs = T6, versus the template-level definition) BEFORE any experiment is run; it is not changed here.

**Verification:** `pytest -q`: 412 passed (about 1 min 47 s). `ruff check`: clean. `npm test`: 40 passed. `tsc` and `vite build`: succeeded. Mutation checks: disabling the dispute fails the CE-1/CE-3 tests; letting the engine override analyst statuses fails the acceptance test. Static demo re-exported (9 incidents, 5 associations, 2 hypotheses). Item 3 was committed after targeted backend tests and the full frontend suite; the full backend suite ran green before item 4's commit. **Not verified:** the UI has not been viewed in a browser. (Antigravity quota log: waived by owner: build moved to Claude Code.)

---

## Session 7: 17 Nov 2026 — two UI bugs, deployment by push, then Phase 5

### Two UI bugs on the live site (fixed before Phase 5, small commits)
**Refresh lost the page.** A dependency-free History API router (`frontend/src/router/`, `7f4d157`) gives every page a real URL (`/campaigns`, `/campaigns/<id>`, `/incidents/<id>`, `/graph`, `/scenarios`, ...), keeps the evidence inspector in `?assoc=<id>`, supports Back/Forward and shows a page-not-found with a link home; the pages are wired to it in `9cdf589`. react-router was not added (not in the blueprint). **Phone layout.** Below 768 px the sidebar is a drawer (hamburger, closes on tap outside, nav tap or Escape), the top bar shrinks, the inspector becomes an overlay and page padding is smaller (`d1be8cc`). Checked in headless Edge through the DevTools protocol against the built app: 43 checks, no horizontal page scroll on 11 pages at 390 px; deep links, refresh, Back/Forward and the drawer behave. A PowerShell rewrite corrupted the encoding of seven page files on the way; they were restored from git and the edit redone with the edit tool. `frontend/vercel.json` is committed with a test that every route matches its rewrite (`b74cdf6`); the live URL is recorded in `deployment/DEPLOY.md` and the README. Ruff also flagged an unused import, removed in `b9eb6fa`.

### Push and deployment
The owner set Vercel's Root Directory to `frontend`, so a push to `main` redeploys; no CLI use. Pushed `ebce38e..e764bc6` after preflight and all tests; the remote lists only `main` and matches local. (A stray interactive Python process I started by mistake with a bad command was stopped; a hung `pip install` of my own was stopped and retried with `--only-binary`.)

### Phase 5 (owner approved with decisions recorded before any experiment)
**Prompt used:** dataset v2 with 20 decoys, freeze, pre-registration commit with the generator hash; E4 rotation experiment (arms A-D, r = 0, 0.25, 0.5, 0.75, 1.0, at least 10 seeds, both ground truths side by side); E3; chart PNG under 200 KB, EXPERIMENTS.md, DATASET_CARD.md, MODEL_CARD.md; Scenario Lab API; cut E8; family map (digital arrest = T1+T2+T3, bank KYC = T4, payment link = T5, courier/customs = T6; T4-T5 counted false); `T_candidate` stays 0.75; the owner writes the held-out set (placeholder and README only, not read).

**Commits:** `7d0929f` 5.1 generator v2 · `a6b9a9c` pre-registration · `150dab7` 5.2 harness · `0360ffb` 5.3 results and documents · `f754db2` 5.4 Scenario Lab API · plus the commit containing this entry.

**Built.** Generator `gen@2.0`: 15 variants per template (90 campaign incidents), 40 negatives, 20 decoys (D1 awareness notices that quote scams, D2 benign notices citing the helpline 1930 and the cybercrime portal, D3 scam-like calls in reversed order, D4 vague notes), identifiers unique across a dataset (v1 could collide by chance), `script_family` ground truth. The pre-registration (`docs/PREREGISTRATION.md`) fixed arms, metrics, seeds 1001-1010, hashes and the tau_A calibration (dev only, seed 900) before any run. Harness: `backend/app/services/replay_service.py` replays records through the real services in an isolated in-memory database; `scripts/eval_metrics.py` holds the pure metric functions; `scripts/evaluate_model.py` has suites tactics, entities, associations, rotation, injection, latency and a guarded heldout (refuses an empty file and a second run). Arms B and C are read from the same run as D; a test shows this equals separate runs with counter-evidence or candidates switched off. Scenario Lab: 11 scenarios (4 campaigns with a rotation slider, 2 negative or ambiguous, 4 decoy/ambiguous/counter-evidence, 1 injection), each with expectations shown as pass, fail or informational.

**Results (all from scripts; details in docs/EXPERIMENTS.md).** Identifier arms B and C: F1 under truth (a) 0.74 and 0.90 at r = 0, both 0 at r = 1. Counter-evidence: precision 1.0 vs 0.67 at r = 0 with the same recall; 1848 identifier links touched a negative or decoy before it, 0 after (50 runs); 0 I1 violations; negatives never linked (0 of 2000). Fingerprint arm D: F1 0.05 under (a) (below the text baseline's 0.20), about 0.5 under (b) (above 0.43), false association rate 0.23-0.34, candidate recall about 0.9 at r = 1. **D does not beat the text baseline under the instance truth at any rotation level.** Decoys D1 and D3 were linked by candidate links (100 and 185 of 250); D2 and D4 never. **Cause of D's over-merging** (diagnostic after the results, `scripts/diagnose_candidates.py`, seed 1001): 160 of 880 candidate links are false under (b), mostly T4-T5 (the declared confusion), and connected components chain them into one 75-incident group.

**Not done / not claimed.** The owner's held-out set (E6) has not been written or run. No tuning of `T_candidate`, the clustering or the decoys was done after seeing results; a tuned threshold or a different clustering for D is listed as a next experiment (dev data only). Arm C is not the blueprint's full "recurrence window" arm (CE-6 and CE-8 not implemented). E8 cut.

**Things found on the way.** The bank-KYC Scenario Lab expectation was wrong, not the pipeline: some T4 SMS texts never mention the link, so they cannot share a domain even at r = 0; the expectation now comes from the generator's own mention annotations. A disclaimer that said "never a confirmed campaign" tripped the forbidden-wording test, so the wording was changed (the rule forbids that phrase even in a negation). E1 re-run on the v2 sample: macro-F1 0.97 / 0.99 / 0.97 (train/dev/test; test is a fresh sample of the same templates and the lexicon is unchanged, so not independent). The extractor labels most awareness notices as scam tactics because it matches wording, not intent.

**Verification:** `pytest -q` 447 passed (about 6 min, includes a re-run of one full experiment cell and the tables-versus-JSON check); `ruff check` clean; `npm test` 116 passed; `tsc` clean; preflight passed. The static demo re-export differs only in timestamps, so it was not recommitted.

### Held-out set added (18 Nov 2026, during Phase 6)
The 25-scenario held-out set was drafted by a different language model (not Claude), then reviewed, edited and labelled by the owner, Shriya Patil. At the owner's instruction it was converted mechanically to `data/heldout/heldout.jsonl` (markdown links reduced to plain URLs, drafting notes removed, one id fixed, a corrupted word fixed, a real-person name and possibly real phone numbers replaced by invented ones; wording not rewritten). Format checked only (`load_heldout`); the heldout suite was **not run**, and the texts were not used to change any rule, lexicon, threshold or test. The file has no per-utterance tactic labels, so every `tactic_labels` is `[]` and E6 was narrowed, before any run, to scenario-level scam detection and the false-alarm rate on the legitimate scenarios; tactic-level scores are not measured on this set (pre-registration amendment 2). The `whatsapp` channel is recorded as `sms` with `channel: whatsapp` in `notes`, because `whatsapp` is not in the documented channel set and adding it would have needed new validation code. Scenario type, group and a tricky flag are kept in `notes`.
