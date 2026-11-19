# VIGIL

> **Cross-Channel Scam Intelligence Network**
> *Turning scattered scam evidence into explainable campaign investigations.*
>
> **PromptWars × AI Vibeathon 2026 Submission**

[![Live Demo](https://img.shields.io/badge/Demo-link%20pending%20deployment-lightgrey)](#project-status)
[![Demo Video](https://img.shields.io/badge/Video-3--Minute%20Walkthrough-red)](#demo-walkthrough)
[![Branch](https://img.shields.io/badge/Branch-main%20only-green)](#repository-rules)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](#license)
[![Mode](https://img.shields.io/badge/Default%20Mode-100%25%20Offline-success)](#quick-start)

---

## 1. Executive Summary

- **Live Deployed Application:** https://vigil-demo-eta.vercel.app (hosted demo on precomputed synthetic data; every page has its own URL). The design is static-first: the public site always works from precomputed synthetic data and upgrades to the live backend when that is awake (see [deployment/DEPLOY.md](deployment/DEPLOY.md)).
- **Demo Video:** *pending.*
- **Core idea:** Playbook Fingerprinting across rotating phone numbers, UPI IDs, and phishing domains, backed by an explicit 5-state association graph and counter-evidence reasoning.

## Project status

This README describes the full v3.1 design. **Phases 1-6 are implemented so far**; everything in the right-hand column is planned and not yet in the code. Progress is tracked in [TASK_TRACKER.md](TASK_TRACKER.md).

| Implemented (Phases 1-6) | Planned (not built yet) |
|---|---|
| Paste evidence, SHA-256 provenance, NFKC normalisation | Dwell similarity and the recurrence window (cut for now) |
| Phone / UPI / email / URL / domain / organisation extraction, masked display | |
| Playbook fingerprint similarity with a gate; behaviour-only `CANDIDATE_ASSOCIATION` links | |
| Five association states with invariants enforced in the data layer; analyst Accept / Reject / Flag with an audit trail | |
| Campaign hypotheses (always labelled hypothesis) with member basis, weakest link and review | |
| Counter-evidence engine (chronology, payment destination, public identifiers, impersonation, language) with confidence adjustment and automatic disputes; findings stay visible after an analyst accepts | CE-6 and CE-8, the F4 risk factor, fuller entity and incident inspectors (deferred) |
| Secret redaction at ingestion (OTP, PIN, CVV, password, card, Aadhaar), best effort | |
| `OBSERVED_MATCH` on exactly equal identifiers (invariant I1) | The held-out evaluation (E6): set drafted by another language model and reviewed by the owner, run once, last |
| Rule-based tactic extraction (English, Hinglish, a few Hindi/Marathi patterns) with exact spans | Render backend deployment (needs the owner's sign-in); the public demo video and final checks (Phase 7) |
| Stage-based risk indicator with an exact contribution ledger | Gemini extractor and ML classifier: **cut**, not planned for the deadline |
| Prompt-injection guard (regex), manipulation badge, no mitigation for flagged text | |
| Tactic timeline and highlighted transcript; graph (React Flow), evidence inspector, static demo mode | |
| Synthetic dataset generator v2 (decoys, two ground truths), the identifier-rotation experiment (E4), association integrity (E3) and the `tactics` / `entities` / `injection` / `latency` suites | |
| Scenario Lab API: 11 deterministic, replayable scenarios (`GET /scenarios`, `POST /scenarios/{name}/run`) | |
| Every page is a real URL (refresh, deep links, Back/Forward); responsive layout with a phone drawer; Investigations list with search and filters | |
| Scenario Lab UI (rotation slider, run and replay, expected versus actual), Reports (JSON and CSV, facts / inferences / analyst actions / counter-evidence / limitations), Settings with "Clear all local data" | |
| Simulated Live Call Analysis: scripted synthetic calls analysed turn by turn, stage tracker, risk meter, English and Hindi guidance, injection safety badge (a simulation: VIGIL does not listen to real calls) | |
| Real-browser QA script (`scripts/qa_browser.mjs`): console errors, overflow, interactions, keyboard flow and a WCAG AA contrast audit, in hosted-demo and live modes | |

**Evaluation (Phase 5): see section 9 and [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).** The paragraph below is the earlier Phase 2 note, kept for its caveats.

**Earlier note (Phase 2).** On the held-out *test templates* of the synthetic dataset the rule extractor scores macro-F1 0.964 (authority-claim recall 0.80 and allegation precision 0.77 are the weak spots). The 10 injection attacks are all flagged. All of this is synthetic data written by the same author as the rules, so the numbers are optimistic and do not predict real-world performance. Reproduce with `python scripts/evaluate_model.py --suite tactics --split test`; results and caveats are in [docs/experiments/](docs/experiments/). The headline identifier-rotation experiment has **not** been run yet, and no result for it is claimed. **The fingerprint recognises a script family (a playbook), never a specific group, person or organisation.** A preliminary diagnostic on the synthetic train/dev data shows it finds most true pairs but also links different campaign instances that run the same script (precision about 0.2 against the "same campaign instance" ground truth). When all templates are pooled it also links structurally similar scripts, for example the two digital-arrest variants and the bank-KYC and electricity-bill SMS scripts, so what counts as a "script family" must be defined before the evaluation (see `DEVELOPMENT_LOG.md`, Session 6). The Phase 5 evaluation will report **both** that original campaign-instance ground truth (with its low precision stated plainly) **and** a script-family ground truth, side by side; no behavioural habits will be added to the generator after seeing results. See `DEVELOPMENT_LOG.md` (Sessions 5 and 6).

---

## 2. The Problem

Digital-arrest, impersonation, and KYC scams in India operate as industrialised scripts across phone calls, SMS/WhatsApp messages, and malicious payment links. Scammers routinely rotate disposable phone numbers, mule UPI IDs, and newly registered domains.
- **Current tools inspect one message or call in isolation**, reacting only to known-bad identifiers.
- Because identifiers rotate rapidly, **10 reports that follow the same scam script can look like 10 unrelated incidents**.
- Fraud teams at fintechs, banks, and response agencies hold fragmented evidence in spreadsheets and chat logs and cannot easily see which reports share an identifier or a script.

---

## 3. What VIGIL Does: Playbook Fingerprints & Association States

Identifiers change; the **behavioural script** does not.

VIGIL extracts an ordered tactic sequence (`AUTHORITY → ALLEGATION → THREAT → ISOLATION → URGENCY → DEMAND`), institution profile, and payment channel into a **Playbook Fingerprint**. It links incidents using explicit, auditable association states:

| Association State | Meaning | Creation Source | Graph Styling |
|---|---|---|---|
| `OBSERVED_MATCH` | Identical normalised identifier observed in evidence. *(Proves a shared identifier, NOT a common origin).* | Exact normalized equality only | Solid thin sky-blue line (`observed match`) |
| `CANDIDATE_ASSOCIATION` | Statistically similar playbook fingerprint or fuzzy identifier requiring analyst review. | System heuristic / algorithm | Dashed amber line (`similarity %`) |
| `ANALYST_VERIFIED_ASSOCIATION` | Confirmed by a human fraud analyst. | Human analyst review action | Solid thick teal line with checkmark |
| `DISPUTED_ASSOCIATION` | Contradicted by high-severity counter-evidence. | Counter-evidence engine or analyst | Dashed red line with warning marker |
| `REJECTED_ASSOCIATION` | Investigated and explicitly dismissed. | Human analyst review action | Faded grey (hidden by default) |

> **Safety Guarantee:** Solid edges indicate observed equality of identifiers, never unsubstantiated criminal attribution. Campaign hypotheses remain unconfirmed until explicitly accepted by an analyst.

---

## 4. Simulation & Data Disclaimer

> ### ⚠️ Mandatory Ethical & Operational Disclaimers
> 1. **100% Synthetic Data:** All data in this repository, demo scenarios, and evaluation suites is entirely synthetic and explicitly labelled `is_synthetic: true`. No real victim information, real private messages, or unredacted credentials are used or stored.
> 2. **Simulated Call Analysis:** VIGIL's call analysis mode is a **scripted transcript playback simulation**. VIGIL does **NOT** intercept, tap, listen to, or record live telecommunications or phone calls.
> 3. **Experimental Heuristic:** The incident risk indicator (0–100) is an **experimental heuristic**, not a statistical probability of guilt or fraud. It provides full factor contributions and cannot be lowered by prompt injection.
> 4. **No Unilateral Enforcement:** VIGIL produces explainable intelligence for human analysts. It does not unilaterally block bank accounts or accuse individuals.

---

## 5. User Interface & Screenshots

*(Interface walkthrough screenshots will be populated upon frontend milestone completion)*

1. **Overview & KPI Dashboard:** Campaign hypotheses, entity distributions, and incoming incident feed.
2. **Investigation Detail & Tactic Timeline:** Utterance-level tactic sequence, entity redaction, and exact risk contribution breakdown.
3. **Cross-Channel Intelligence Graph:** Multi-incident relationship canvas distinguishing `OBSERVED_MATCH`, `CANDIDATE_ASSOCIATION`, and `DISPUTED_ASSOCIATION`.
4. **Evidence Inspector:** Side-by-side excerpt verification, normalisation provenance, and counter-evidence findings.
5. **Simulated Live Call Analysis:** Interactive progressive transcript playback demonstrating real-time stage tracking and injection mitigation.

---

## 6. Architecture

```
                       Browser (React + TypeScript + Vite)
      ┌─────────────────────────────────────────────────────────────────┐
      │  Overview · Investigation Detail · Intelligence Graph (React Flow)│
      │  Campaigns · Scenario Lab · Simulated Live Call · Reports       │
      └────────────────────────────────┬────────────────────────────────┘
                                       │ REST / JSON
                                       ▼
                     FastAPI Application (Modular Monolith)
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  api/           REST Endpoints & Validation Schemas (/api/v1)               │
 │  services/      Incident Management, Graph Service, Review Audit Logs       │
 │  ai_engine/     Normalisation & Provenance Hashing                          │
 │                 Regex & Gazetteers (Phone, UPI, Email, Domain, Org)          │
 │                 Tactic Classifier (Deterministic Lexicon + TF-IDF/LogReg)   │
 │                 Temporal Engine (Stage Sequences & Chronology Validation)   │
 │                 Playbook Fingerprint Similarity & Association Engine         │
 │                 Counter-Evidence Engine (Rules CE-1 through CE-8)           │
 │                 Risk Engine with Persisted Factor Contributions             │
 │                 Prompt-Injection Guard (Regex + Delimiter Protection)       │
 │  storage/       SQLite (SQLAlchemy 2) & NetworkX In-Memory Graph            │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Quick Start (100% Free & Offline-First)

### Prerequisites
- Python 3.11+
- Node.js LTS (v18+)
- Git

### Local Setup
```bash
# 1. Clone the repository
git clone https://github.com/ShriyaP1966/VIGIL.git
cd VIGIL

# 2. Setup backend virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# 3. Setup frontend dependencies
cd frontend
npm ci
cd ..

# 4. (Optional) copy the environment template. Offline mode is the default and needs no .env or API keys.
#    Windows PowerShell: Copy-Item .env.example .env
cp .env.example .env

# 5. Launch the demo (seeds the synthetic incidents, starts the API and the web UI)
python scripts/run_demo.py
```

Open `http://localhost:5173` in your browser. Backend API docs are accessible at `http://localhost:8000/docs`.

Checks: `pytest -q` (repo root), `cd frontend && npm test`, `python scripts/preflight.py`.
To regenerate the precomputed demo data from the real pipeline: `python scripts/export_static_demo.py`.

---

## 8. Demo Walkthrough

1. **Simulated Live Call Analysis:** Run scripted progressive transcript playback. Watch stage chips advance through Authority, Allegation, Threat, and Isolation. Observe that prompt-injection attempts trigger the safety badge without reducing the calculated risk.
2. **Incident Ingestion & Observed Matches:** Ingest a payment request and a phishing URL. Observe an `OBSERVED_MATCH` generated between incidents sharing a normalized UPI handle.
3. **Playbook Candidate Association:** Ingest an incident with rotated phone and UPI identifiers. Observe the generation of a `CANDIDATE_ASSOCIATION` based on behavioral playbook similarity exceeding the candidate threshold.
4. **Counter-Evidence Engine in Action:** Ingest an incident referencing a legitimate public helpline or with incompatible stage chronology. Observe the association immediately transition to `DISPUTED_ASSOCIATION` with rule citations.
5. **Evidence Inspector & Audit Trail:** Drill into any graph edge. Review source text spans, normalisation details, and perform an Analyst Review (Accept/Reject/Flag).

---

## 9. Evaluation & Research Findings

VIGIL evaluates whether behavioural playbook fingerprinting reliably links scam incidents when scammers rotate identifiers:

- **Arm A:** Text-similarity / TF-IDF cosine baseline (its threshold chosen on dev data only).
- **Arm B:** Identifier graph (`OBSERVED_MATCH` connected components).
- **Arm C:** Arm B + counter-evidence (chronology, payment destination, public identifiers, impersonation, language). CE-6 and CE-8 are not implemented, so this is not the full "recurrence window" arm.
- **Arm D (Hero):** Arm C + Playbook Fingerprint matching (`CANDIDATE_ASSOCIATION`).

![Identifier-rotation experiment](docs/experiments/rotation_all.png)

*Pre-registered ([docs/PREREGISTRATION.md](docs/PREREGISTRATION.md)), 10 seeds, mean ± sample std, all numbers generated from [docs/experiments/rotation.json](docs/experiments/rotation.json). Synthetic data; results do not imply real-world performance.* Left: truth (a) a true pair is the same campaign instance. Right: truth (b) a true pair is the same script family (digital arrest = T1+T2+T3, bank KYC = T4, payment link = T5, courier/customs = T6; a bank-KYC to payment-link link counts as false). Top: pairwise F1. Bottom: false association rate.

What it shows, honestly:

- **Identifier linking collapses under rotation:** under (a), arms B and C go from F1 0.74 and 0.90 at r = 0 to 0 at r = 1. Counter-evidence raises precision at no cost in recall (C: precision 1.00 at r = 0, B: 0.67) and, across 50 runs, no observed link touched a legitimate negative or decoy after counter-evidence (1848 did before). Invariant I1 had 0 violations.
- **The fingerprint (D) recovers links that rotation hides, at a cost:** at r = 1 it is the only graph arm that finds pairs (candidate recall about 0.9), but its pairwise F1 is 0.05 under (a) (below the text baseline's 0.20) and about 0.5 under (b) (above the baseline's 0.43), and its false association rate is 0.23 to 0.34 against about 0.03 or less for the others. A minority of wrong candidate links (mostly bank-KYC to payment-link scripts) are chained by connected components into one 75-incident group.
- **D does not beat the text baseline under (a) at any rotation level.** It is better described as a lead generator for an analyst than as an automatic grouping.
- **Decoys were not clean:** awareness notices that quote scams (D1) and reversed-order calls (D3) were linked by candidate links in a large share of runs; legitimate negatives never were (0 of 2000).
- **Post-hoc, reported separately (docs/EXPERIMENTS.md section 10):** after seeing these results, a higher fingerprint threshold (0.80, chosen on dev data only) was tried and evaluated on fresh seeds. Under the script-family truth it cut the false association rate from about 0.22 to about 0.02 and raised F1 from about 0.5 to about 0.9; under the campaign-instance truth it still does not beat the text baseline. It was tuned after the results were seen, on the same generator and templates, so it says nothing about real scripts; **the headline above and the application default (0.75) are unchanged.**
- **Not run:** the held-out set (E6; 25 scenarios drafted by a different language model, not Claude, then reviewed, edited and labelled by the owner; scenario-level scores only, no tactic-level scores). Limits and threats to validity are in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md), section 8.

Other suites (all from `scripts/evaluate_model.py`): E1 tactics macro-F1 on the v2 sample train/dev/test 0.97/0.99/0.97 (test is a fresh sample of the same templates, not independent; the extractor matches wording, so it also labels most awareness notices as scam tactics), E2 entities, E3 integrity, E5 injection 10 of 10 authored attacks, E7 latency (descriptive).

---

## 10. Prompting Approach & Development Methodology

Developed in partnership with **Google Antigravity**:
- **Blueprint-First Discipline:** Strict execution against `PROJECT_BLUEPRINT.md`.
- **Vertical-Slice Phasing:** Step-by-step verifiable phases with explicit "Done means" criteria.
- **Zero Fabrication Rule:** Every metric, latency figure, and evaluation score is produced directly by automated test harnesses.
- **Deterministic Offline Baseline:** All intelligence tiers function without external API dependencies.

---

## 11. Security & Responsible Use

- **Prompt-Injection Defense:** Untrusted transcripts are strictly bounded, validated against rigid Pydantic schemas, and analyzed by regex injection detectors. Flagged input cannot lower risk scores.
- **Privacy by Design:** Phone numbers and UPI handles are masked in the UI (canonical values are stored for exact matching). OTPs, passwords, PINs, CVVs, card numbers and Aadhaar numbers are removed at ingestion (before hashing, storage or logging) and replaced with `[REDACTED:…]`; this is rule-based and **best effort** (see Known Limitations). Phones, UPI handles, emails, domains and bank account numbers are kept because VIGIL matches on them. Use synthetic data only.
- **Size Budget & Hygiene:** Enforced by `scripts/preflight.py` to ensure repository size remains under 10 MB on a single `main` branch.

---

## 12. Documentation Index

- [Architecture Specification](ARCHITECTURE.md)
- [Task & Milestone Tracker](TASK_TRACKER.md)
- [Master Project Blueprint](PROJECT_BLUEPRINT.md)
- [Dataset Card](docs/DATASET_CARD.md)
- [Model Card](docs/MODEL_CARD.md)
- [Experiment Records](docs/EXPERIMENTS.md) and the [Pre-registration](docs/PREREGISTRATION.md) written before they were run
- [Privacy & Ethical Safeguards](docs/PRIVACY.md)

---

## 13. Roadmap & Startup Expansion

1. **Phase 1 (Competition Prototype):** Explainable cross-channel campaign intelligence with synthetic evaluation.
2. **Phase 2 (Analyst Discovery):** Engagement with fraud operations and cyber response teams.
3. **Phase 3 (Enterprise MVP):** Multi-tenant RBAC, cryptographic evidence audit trails, and DPDP Act 2023 compliance.
4. **Phase 4 (Cross-Organization Network):** Privacy-preserving sharing of hashed indicator playbooks between financial institutions.

---

## 14. Known Limitations

- Secret redaction is rule-based and best effort. It does **not** catch spelled-out digits ("four eight two…"), secrets with no cue word nearby ("the number from the sms is 482913"), or non-Luhn card numbers with no "card" cue. Amount-like values right after a currency marker are treated as amounts. A 4-6 digit value after "PIN" is redacted even if it was a postal code ("PIN code" itself is left alone). Plain text sent by the browser reaches the server before it is redacted, so use HTTPS and synthetic data.
- Tactic detection is lexicon rules only: it recognises the phrasings in `data/lexicon.json` and misses others (on unseen templates authority-claim recall was 0.80). Some labels are ambiguous (e.g. "tonight" counts as urgency, "under digital arrest" as threat). Institution class and payment channel are simple priority rules with modest accuracy (0.66-0.75 and 0.66-0.97 across splits). Victim turns are not scored, but a victim's words inside an unlabelled paste are.
- The playbook fingerprint compares the order of detected stages plus the claimed institution and payment channel. It cannot tell apart two groups that run the same script, it ignores dwell time, and its weights and the 0.75 candidate threshold are a-priori choices, not learned. A candidate link is a lead for an analyst, never a conclusion; campaigns are hypotheses even after an analyst accepts them.
- Counter-evidence rules are a-priori priors (severities and confidence impacts are not learned or calibrated). The public-identifier allowlist is a small starter list that must be verified by its maintainer, and the helpline extraction only knows the national cyber crime helpline 1930. CE-4 can only fire on a low-confidence extraction, which the current extractor does not produce; CE-6 and CE-8 are not built. The rules do not separate different campaigns that run the same script.
- The injection guard is a regex layer. It does not catch leetspeak, spaced-out letters or polite paraphrase without trigger words, and benign-sounding text appended without trigger wording can lower the score of a scam that has no payment or credential request (by at most 15 points).
- High dependence on transcription quality when operating on noisy audio.
- Heuristic weights in risk and playbook similarity are design priors, not trained Bayesian posterior probabilities.
- Hindi and Hinglish nuance requires continuous lexicon expansion for regional slang variations.
- Real-time call protection in production requires telecommunications and mobile OS level integrations.
