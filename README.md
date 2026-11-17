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

- **Live Deployed Application:** *pending: not deployed yet.* The design is static-first: the public site always works from precomputed synthetic data and upgrades to the live backend when that is awake (see [deployment/DEPLOY.md](deployment/DEPLOY.md)).
- **Demo Video:** *pending.*
- **Core idea:** Playbook Fingerprinting across rotating phone numbers, UPI IDs, and phishing domains, backed by an explicit 5-state association graph and counter-evidence reasoning.

## Project status

This README describes the full v3.1 design. **Only the Phase 1 vertical slice is implemented so far**; everything else below is planned and not yet in the code. Progress is tracked in [TASK_TRACKER.md](TASK_TRACKER.md).

| Implemented (Phase 1) | Planned (not built yet) |
|---|---|
| Paste evidence, SHA-256 provenance, NFKC normalisation | Tactic classification, injection guard (Phase 2) |
| Phone / UPI / email / URL / domain / organisation extraction, masked display | Playbook fingerprint, candidate associations, campaign hypotheses (Phase 3) |
| `OBSERVED_MATCH` on exactly equal identifiers (invariant I1) | Counter-evidence engine, full inspector, analyst review (Phase 4) |
| Placeholder risk indicator with an exact contribution ledger | Evaluation and the rotation experiment (Phase 5) |
| Graph (React Flow), evidence inspector, static precomputed demo mode | Simulated live call, reports, scenario lab UI (Phase 6) |

No evaluation results exist yet, and none are claimed.

---

## 2. The Problem

Digital-arrest, impersonation, and KYC scams in India operate as industrialised scripts across phone calls, SMS/WhatsApp messages, and malicious payment links. Scammers routinely rotate disposable phone numbers, mule UPI IDs, and newly registered domains.
- **Current tools inspect one message or call in isolation**, reacting only to known-bad identifiers.
- Because identifiers rotate rapidly, **10 separate reports from the same criminal campaign appear as 10 isolated incidents**.
- Fraud teams at fintechs, banks, and response agencies hold fragmented evidence in spreadsheets and chat logs without cross-channel campaign reconstruction.

---

## 3. What VIGIL Does: Playbook Fingerprints & Association States

Identifiers change; the **behavioural script** does not.

VIGIL extracts an ordered tactic sequence (`AUTHORITY → ALLEGATION → THREAT → ISOLATION → URGENCY → DEMAND`), institution profile, and payment channel into a **Playbook Fingerprint**. It links incidents using explicit, auditable association states:

| Association State | Meaning | Creation Source | Graph Styling |
|---|---|---|---|
| `OBSERVED_MATCH` | Identical normalised identifier observed in evidence. *(Proves shared identifier, NOT confirmed criminal syndicate).* | Exact normalized equality only | Solid thin sky-blue line (`observed match`) |
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

# 5. Launch the demo (seeds 3 synthetic incidents, starts the API and the web UI)
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

- **Arm A:** Text-similarity / TF-IDF cosine baseline.
- **Arm B:** Identifier graph (`OBSERVED_MATCH` connected components).
- **Arm C:** Arm B + Temporal reasoning (chronology validation + recurrence windows).
- **Arm D (Hero):** Arm C + Playbook Fingerprint matching (`CANDIDATE_ASSOCIATION`).

*(Evaluation runs, rotation charts, and macro-F1 benchmarks produced by `scripts/evaluate_model.py` will be recorded here).*

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
- **Privacy by Design:** Phone numbers and UPI handles are masked in the UI (canonical values are stored for exact matching). Redaction of OTPs, passwords and card numbers at ingestion is specified in the blueprint (§5.5) but **not implemented yet**; use synthetic data only.
- **Size Budget & Hygiene:** Enforced by `scripts/preflight.py` to ensure repository size remains under 10 MB on a single `main` branch.

---

## 12. Documentation Index

- [Architecture Specification](ARCHITECTURE.md)
- [Task & Milestone Tracker](TASK_TRACKER.md)
- [Master Project Blueprint](PROJECT_BLUEPRINT.md)
- [Dataset Card](docs/DATASET_CARD.md)
- [Model Card](docs/MODEL_CARD.md)
- [Experiment Records](docs/EXPERIMENTS.md)
- [Privacy & Ethical Safeguards](docs/PRIVACY.md)

---

## 13. Roadmap & Startup Expansion

1. **Phase 1 (Competition Prototype):** Explainable cross-channel campaign intelligence with synthetic evaluation.
2. **Phase 2 (Analyst Discovery):** Engagement with fraud operations and cyber response teams.
3. **Phase 3 (Enterprise MVP):** Multi-tenant RBAC, cryptographic evidence audit trails, and DPDP Act 2023 compliance.
4. **Phase 4 (Cross-Organization Network):** Privacy-preserving sharing of hashed indicator playbooks between financial institutions.

---

## 14. Known Limitations

- High dependence on transcription quality when operating on noisy audio.
- Heuristic weights in risk and playbook similarity are design priors, not trained Bayesian posterior probabilities.
- Hindi and Hinglish nuance requires continuous lexicon expansion for regional slang variations.
- Real-time call protection in production requires telecommunications and mobile OS level integrations.
