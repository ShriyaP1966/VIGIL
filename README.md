# VIGIL

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Live demo](https://img.shields.io/badge/Live%20demo-vigil--demo--eta.vercel.app-blue)](https://vigil-demo-eta.vercel.app)
[![Data](https://img.shields.io/badge/Data-100%25%20synthetic-orange)](#limitations-please-read)

**VIGIL is an offline-first, explainable tool that helps an analyst see which scam reports share an identifier or a script.**
*PromptWars × AI Vibeathon 2026 submission.*

In India, "digital arrest" and other financial-impersonation scams (fake police, customs, bank or courier staff) spread across
phone calls, SMS and WhatsApp. Scammers keep swapping phone numbers, UPI IDs and domains, so ten reports of the same script look
like ten unrelated cases. VIGIL reads each report, extracts its tactics and identifiers, links reports with auditable states, and
shows counter-evidence next to every link. **It never declares a campaign by itself: a group of linked reports is only a
hypothesis until a person accepts it.** All data is synthetic.

**▶ Live demo: https://vigil-demo-eta.vercel.app** (static site on precomputed synthetic data, no install)

**Contents:** [Try it in 2 minutes](#try-it-in-2-minutes) · [What makes it different](#what-makes-it-different) ·
[Key results](#key-results) · [Run it locally](#run-it-locally) · [Limitations](#limitations-please-read) ·
[Built with AI coding assistants](#built-with-ai-coding-assistants) · [More detail (collapsed)](#more-detail) · [Licence](#licence)

![VIGIL overview page on the live demo, showing synthetic cases and the synthetic-data labels](docs/screenshots/01-overview.png)

---

## Try it in 2 minutes

Open the [live demo](https://vigil-demo-eta.vercel.app). Every step below exists in the hosted demo today (a test checks these
claims against the demo data).

1. **Overview.** Note the "Hosted demo: precomputed synthetic data" badge and the synthetic-data notice. Nine synthetic cases.
2. **Intelligence Graph** ([`/graph`](https://vigil-demo-eta.vercel.app/graph)). Click each kind of line to open the **Evidence Inspector**
   (or use the direct link):
   * a **solid blue** line between INC-0001 and INC-0002: the same UPI handle in both ([direct](https://vigil-demo-eta.vercel.app/graph?assoc=1));
   * a **dashed amber** line from INC-0001 to INC-0004: a similar script with rotated identifiers, no shared identifier
     ([direct](https://vigil-demo-eta.vercel.app/graph?assoc=2));
   * a **dashed red** (disputed) line between INC-0003 and INC-0005: both cite the public helpline 1930, so counter-evidence rule CE-3
     disputes the link ([direct](https://vigil-demo-eta.vercel.app/graph?assoc=3)). A second one (INC-0006 to INC-0007, CE-1, incompatible
     order) is at [`?assoc=4`](https://vigil-demo-eta.vercel.app/graph?assoc=4).
3. **Campaigns** ([`/campaigns`](https://vigil-demo-eta.vercel.app/campaigns)). Two *hypotheses*, both unreviewed. Open the first (three incidents) and read the
   playbook alignment grid. Accept/Reject needs the local app.
4. **Scenario Lab** ([`/scenarios`](https://vigil-demo-eta.vercel.app/scenarios)). Open "Digital arrest: central-agency impersonation" and drag **Identifier rotation**
   from 0 to 1: the three exact-identifier links disappear and three behaviour-only candidate links remain. Click **Replay**: identical result.
5. **An incident** ([`/incidents/1`](https://vigil-demo-eta.vercel.app/incidents/1)). Read the **tactic timeline**, the highlighted transcript and the risk ledger, whose
   contributions sum exactly to the score.
6. *Bonus:* [**Simulated Call Analysis**](https://vigil-demo-eta.vercel.app/simulated-call): pick "Scam call with an injected instruction" and press Play (a simulation of scripted text; VIGIL does not listen to calls).

## What makes it different

| Link type | What it means | What it does **not** mean |
|---|---|---|
| **Observed match** | exactly the same normalised identifier (phone, UPI, domain…) appears in two reports | proof that one group or one campaign is behind both |
| **Candidate association** | a similar *script*, with **no** shared identifier: a lead to investigate | a conclusion; the fingerprint alone can never make a link "observed" (only an exactly shared identifier can) |
| **Analyst-verified association** | a person reviewed the evidence and accepted the link (recorded in an audit trail) | a statement about any named person or organisation |

* **Counter-evidence engine.** Rules look for reasons a link might be wrong (a public helpline shared by two notices, incompatible
  order of stages, different payment destinations). Findings are shown **next to** the evidence, can dispute a link automatically, and
  stay visible even after an analyst accepts it.
* **Nothing is called a confirmed campaign automatically.** A group of linked reports is a **hypothesis** until an analyst accepts it,
  and the interface and reports say so everywhere. Five safety invariants (I1-I5) enforce this in the data layer and are tested.
* **Playbook** = the ordered steps a scam script follows (authority → allegation → threat → isolation → urgency → demand), plus the
  claimed institution and payment channel. **Script family** = incidents that run the same kind of playbook (for example "digital arrest").
  The fingerprint recognises a script family, **never** a specific group, person or organisation.

## Key results

Synthetic data written by the same author as the rules, so the numbers are optimistic and say nothing about real traffic. The rotation
experiment was **pre-registered** before it was run ([docs/PREREGISTRATION.md](docs/PREREGISTRATION.md)). Each line is generated from
`docs/experiments/*.json`; full tables are under [More detail](#more-detail).

<!-- BEGIN:readme-keyresults -->
* **Pre-registered: rotating identifiers breaks identifier linking.** Under the campaign-instance truth, the identifier graph (B) and B with counter-evidence (C) fall from F1 0.74 and 0.90 with no rotation to 0.00 and 0.00 when every identifier is replaced.
* **Counter-evidence raises precision at no cost in recall:** with no rotation, precision 1.00 for C against 0.67 for B.
* **The playbook fingerprint (D) recovers links that rotation hides, but over-merges.** At r = 0.5 its F1 is 0.05 under the instance truth (the plain text baseline A scores 0.21) and 0.50 under the script-family truth, with a false association rate of 0.25.
* **Post-hoc, tuned after seeing those results (fresh seeds, reported separately):** a higher threshold lifts D to F1 0.90 with a false association rate of 0.019 under the script-family truth (from 0.51 and 0.233), but only 0.12 under the instance truth. The headline and the application default (`T_CANDIDATE = 0.75`) are unchanged.
* **Held-out set, run once:** 18 of 19 scam scenarios had a scam tactic detected (missed: H21, a cut-off call), but **2 of 6 legitimate scenarios (H15 and H17) were flagged as scams, a false-alarm rate of 2 of 6.** Tactic-level scores were not measured. Small, synthetic set.
<!-- END:readme-keyresults -->

## Run it locally

100% free and offline; no API key is needed or used. Prerequisites: Python 3.11+, Node.js 18+, Git.

```bash
git clone https://github.com/ShriyaP1966/VIGIL.git
cd VIGIL
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd frontend && npm ci && cd ..
cp .env.example .env               # optional; Windows PowerShell: Copy-Item .env.example .env
python scripts/run_demo.py         # seeds the 9 synthetic incidents, starts the API and the web UI
```

Open http://localhost:5173 (API docs at http://localhost:8000/docs). The local app adds what the hosted demo cannot do: paste your own
synthetic evidence, accept or reject links, and "Clear all local data". Checks: `pytest -q`, `cd frontend && npm test`,
`python scripts/preflight.py`.

## Limitations (please read)

* **All data is synthetic**, and the generator, the lexicon and the rules share an author. Scores are optimistic. Nothing here
  says how VIGIL would perform on real traffic, and it must not be used with real victims' data.
* **The held-out set is small** (19 scam, 6 legitimate), drafted by a different language model and reviewed by the owner, and
  synthetic. **Tactic-level scores were not measured on it.** Its rates are very imprecise: one legitimate scenario is 17 points.
* **The held-out false alarms are real:** 2 of 6 legitimate scenarios (H15, H17) were flagged as scams, and 18 of 19 scam
  scenarios were detected (H21 missed). The likely cause is that the extractor matches wording, not intent, for
  example an awareness notice that quotes scam phrases; this is **unverified**. The rules were **not** changed afterwards.
  **A future fix** would use the speaker's role and intent (who is saying it and why), not only wording.
* **The fingerprint over-merges within script families.** Different instances of one template run an identical script, so it
  cannot tell them apart (precision against the instance truth is low), and with connected-component grouping a few wrong
  links merge many incidents. A tuned threshold helps on this synthetic data but was chosen after seeing results (post-hoc).
* **Decoys are still linked.** Awareness notices that quote scams (D1) and reversed-order calls (D3) were linked by candidate
  links in a large share of runs (100 and 185 of 250 in the headline runs); benign-identifier (D2) and vague-note (D4) decoys
  were not.
* **Counter-evidence is partial:** CE-6 and CE-8 are not built, severities are a-priori priors, and the public-identifier list is
  a small starter list.
* **Extraction is lexicon rules only.** It misses phrasings it has not seen, some words are ambiguous ("tonight" reads as
  urgency), and Hindi, Marathi and Hinglish coverage is thin. The injection guard is a regex layer and does not catch
  obfuscated or paraphrased attacks.
* **Secret redaction is best effort** (spelled-out digits, secrets with no cue word and unusual formats are missed); use
  synthetic data and HTTPS. See [docs/PRIVACY.md](docs/PRIVACY.md).
* **Deployment:** the public site is static (precomputed data); a hosted backend was not set up. Accessibility was audited
  automatically (contrast, keyboard flow), not with a screen reader. Protecting people during live calls would need telecom or
  mobile-OS integration, which VIGIL does not attempt.
* **Not a product.** It is a research prototype: no accounts, no access control, no claim of fitness for any real-world use.

## Built with AI coding assistants

This project was built with AI coding assistants, in three stages.

1. **Blueprint.** The project blueprint (`PROJECT_BLUEPRINT.md`) was drafted with Claude in a chat. The development log treats it as
   the starting input.
2. **Initial scaffold: Phase 0 and most of Phase 1** (setup, backend, frontend, AI-engine skeleton, deployment scaffold). Built in
   **Google Antigravity**, using Gemini and Claude Sonnet 4.6.
3. **Everything after: finishing Phase 1, then Phases 2 to 7**, including the evaluation harness, the experiments, the call
   simulation, the reports and these documents. Built with **Claude Code** (Anthropic) under the owner's direction. Its first session
   audited the scaffold and fixed real defects, among them hand-typed demo values that were replaced by real pipeline output, a
   `.gitignore` rule that had kept the ORM package out of git, and deployment settings that would not have worked (log, Session 2).

How the work was kept honest: small reviewed steps under a standing rules file (`CLAUDE.md`), and a development log
(`DEVELOPMENT_LOG.md`) that records each session's prompt, decisions, mistakes and fixes. Every metric comes from a script,
experiments were pre-registered, and the held-out set was drafted by a different language model (not Claude) and then reviewed,
edited and labelled by the owner, Shriya Patil. Treat the code as AI-assisted and verify it with the tests, the browser QA script
and the reproduction commands rather than taking this README's word.

## More detail

<details>
<summary><b>Screenshots</b> (live site, synthetic data)</summary>

| | |
|---|---|
| ![Investigation detail with the tactic timeline and risk ledger](docs/screenshots/02-investigation-detail.png) | ![Intelligence graph with the Evidence Inspector open on an observed match](docs/screenshots/03-graph-and-evidence-inspector.png) |
| ![Campaign hypothesis with the playbook alignment grid](docs/screenshots/04-campaign-playbook-alignment.png) | ![Scenario Lab at identifier rotation 1: no observed links, three candidate links](docs/screenshots/05-scenario-lab-rotation-1.png) |
| ![Simulated call analysis with the manipulation-attempt safety badge](docs/screenshots/06-simulated-call-injection.jpg) | ![Structured report with facts, inferences, analyst actions, counter-evidence and limitations](docs/screenshots/07-report.jpg) |
| ![Phone layout with the navigation drawer open](docs/screenshots/08-mobile-drawer.png) | |

</details>

<details>
<summary><b>Architecture</b> (diagram and pipeline; details in <a href="ARCHITECTURE.md">ARCHITECTURE.md</a>)</summary>

```mermaid
flowchart LR
  subgraph Browser["Browser: React 18, TypeScript, Vite, Tailwind, React Flow"]
    UI["Pages + History-API router<br/>(every page a real URL)"]
    A{"ApiClient<br/>probes /api/v1/health"}
    UI --> A
  end
  A -- "backend answers" --> H["HttpApi"]
  A -- "none / asleep" --> S["StaticApi<br/>/demo-data/*.json"]
  H --> API
  subgraph Backend["FastAPI, offline, no API key"]
    API["REST /api/v1"] --> SV["services"] --> AI["ai_engine: redaction, extraction,<br/>injection guard, fingerprint, counter-evidence"]
    SV --> DB[("SQLite")]
  end
  EX["scripts/export_static_demo.py<br/>(runs the real pipeline)"] --> S
```

Per incident: redact secrets → normalise and extract identifiers → exact matches → injection guard → tactic extraction → risk
ledger → playbook fingerprint (candidates only) → counter-evidence (a high finding disputes a link) → campaign hypotheses.
Safety invariants **I1-I5**: an observed match needs exactly equal identifiers; no model output can create an observed or
analyst-verified link; analyst statuses need a recorded review; a campaign is a hypothesis until accepted; every link has evidence
and a plain-language explanation.

</details>

<details>
<summary><b>Full benchmark tables</b> (pre-registered headline, post-hoc row, held-out set)</summary>

Four arms: **A** text similarity (TF-IDF); **B** identifier graph (exact matches); **C** B plus counter-evidence (CE-1, 2, 3, 4, 5, 7;
CE-6 and CE-8 are not built); **D** C plus the playbook fingerprint (`T_candidate = 0.75`). Two ground truths, always together:
**(a)** a true pair is the same campaign instance; **(b)** a true pair is the same script family (digital arrest = T1+T2+T3, bank KYC = T4,
payment link = T5, courier/customs = T6; a bank-KYC to payment-link link counts as **false**). Rotation `r` is the chance each identifier
is replaced between incidents (0 = never, 1 = always). 10 seeds, 150 incidents per run (90 campaign, 40 legitimate, 20 decoys).

**Headline: the pre-registered configuration** (all numbers generated from [docs/experiments/rotation.json](docs/experiments/rotation.json)).

![Identifier-rotation experiment: pairwise F1 and false association rate for arms A to D at five rotation levels, under both ground truths](docs/experiments/rotation_all.png)

<!-- BEGIN:readme-headline -->
**Ground truth (a) same campaign instance**; cells are pairwise F1 / false association rate:

| rotation r | A | B | C | D |
|---|---:|---:|---:|---:|
| 0.0 | 0.20 / 0.036 | 0.74 / 0.003 | 0.90 / 0.000 | 0.05 / 0.339 |
| 0.5 | 0.21 / 0.034 | 0.47 / 0.004 | 0.61 / 0.000 | 0.05 / 0.327 |
| 1.0 | 0.20 / 0.032 | 0.00 / 0.003 | 0.00 / 0.000 | 0.05 / 0.302 |

**Ground truth (b) same script family**; cells are pairwise F1 / false association rate:

| rotation r | A | B | C | D |
|---|---:|---:|---:|---:|
| 0.0 | 0.43 / 0.007 | 0.10 / 0.004 | 0.11 / 0.000 | 0.51 / 0.257 |
| 0.5 | 0.43 / 0.006 | 0.06 / 0.004 | 0.06 / 0.000 | 0.50 / 0.249 |
| 1.0 | 0.42 / 0.005 | 0.00 / 0.003 | 0.00 / 0.000 | 0.51 / 0.228 |
<!-- END:readme-headline -->

**Post-hoc and exploratory.** After seeing the headline, a higher fingerprint threshold was tried: **chosen on dev data only**, protocol
committed before the fresh-seed run, then evaluated on 10 fresh seeds (2001-2010). It was **tuned after the results were seen**, on the
same generator and templates, so it shows nothing about new scripts. **The headline and the application default (`T_CANDIDATE = 0.75`)
are unchanged.**

<!-- BEGIN:readme-posthoc -->
**(a) same campaign instance** (fresh seeds, F1 / false association rate):

| rotation r | D, pre-registered (T=0.75) | D, post-hoc (T=0.80/components) |
|---|---:|---:|
| 0.0 | 0.05 / 0.306 | 0.12 / 0.124 |
| 0.5 | 0.05 / 0.310 | 0.12 / 0.118 |
| 1.0 | 0.05 / 0.279 | 0.12 / 0.105 |

**(b) same script family** (fresh seeds, F1 / false association rate):

| rotation r | D, pre-registered (T=0.75) | D, post-hoc (T=0.80/components) |
|---|---:|---:|
| 0.0 | 0.55 / 0.221 | 0.95 / 0.017 |
| 0.5 | 0.51 / 0.233 | 0.90 / 0.019 |
| 1.0 | 0.51 / 0.207 | 0.86 / 0.016 |
<!-- END:readme-posthoc -->

Under the script-family truth the post-hoc variant is much better (it removes most cross-family links); under the instance truth it still
does not beat the text baseline (about 0.20), and the text baseline keeps a lower false association rate. See
[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) section 10.

**Held-out set (run once, frozen configuration).** 25 scenarios (19 scam, 6 legitimate) **drafted by a different language model (not
Claude), then reviewed, edited and labelled by the owner**. The rule extractor was run on them **once**; no rule, lexicon, threshold or
test was changed afterwards.

<!-- BEGIN:readme-heldout -->
| held-out measure (run once) | result | which |
|---|---:|---:|
| Scam scenarios with a scam tactic detected | 18 of 19 | missed: H21 |
| Legitimate scenarios flagged as scams (false alarms) | 2 of 6 | flagged: H15, H17 |
| Tactic-level scores | not measured | no per-utterance labels in the set |
<!-- END:readme-heldout -->

18 of 19 scam scenarios had a scam tactic detected (the miss is H21, a cut-off call that ends before any demand), but **2 of 6 legitimate
scenarios (H15 and H17) were flagged as scams, a false-alarm rate of 2 of 6.** The likely cause is that the extractor matches **wording,
not intent**: H17 is an awareness notice that quotes scam phrases and H15 is a genuine bank alert with an urgent cue. That explanation is
**unverified**, because the scenarios' tactic events were not examined afterwards to avoid tuning on them. It is a small synthetic set
and **tactic-level scores were not measured** (the set has no per-utterance labels).

Other suites: tactic extraction macro-F1 0.97 / 0.99 / 0.97 (train / dev / test; the test figure is a fresh sample of the same templates,
not independent), prompt-injection 10 of 10 authored attacks neutralised (authored by the same hand as the guard), entity extraction,
latency (descriptive). Full tables, precision/recall, the test slice and threats to validity: [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

</details>

<details>
<summary><b>API at a glance</b> (full specification: <a href="docs/API_SPEC.md">docs/API_SPEC.md</a>)</summary>

Base path `/api/v1`: `GET /health` · `POST/GET /incidents`, `GET /incidents/{id}`, `POST /incidents/{id}/evidence`, `POST /analyze/{id}`,
`GET /incidents/{id}/report?format=json|csv` · `GET /graph` · `GET /associations/{id}`, `POST /associations/{id}/review` ·
`GET /campaigns`, `GET /campaigns/{id}`, `POST /campaigns/{id}/review` · `GET /scenarios`, `POST /scenarios/{name}/run` ·
`GET /simulations`, `POST /simulations/live-call/analyze` · `DELETE /data?confirm=true`. JSON everywhere; one error body shape;
no authentication (a local single-user tool).

</details>

<details>
<summary><b>Privacy and safety notes</b> (full text: <a href="docs/PRIVACY.md">docs/PRIVACY.md</a>)</summary>

* Synthetic data only; no accounts, analytics or third-party calls; the hosted demo stores nothing you do.
* Secrets (OTP, PIN, CVV, password, card, Aadhaar) are redacted before anything is stored, best effort and fail-closed; only counts are kept.
* Evidence is rendered as plain text, never HTML; URLs in evidence are never fetched; a regex guard flags instruction-like text and the
  UI shows a safety badge; reports export masked identifiers and neutralise spreadsheet formulas.
* The risk score is an experimental heuristic, not a probability. Simulated call analysis replays scripted text; VIGIL does not listen to calls.

</details>

<details>
<summary><b>Documents, reproduction and repository rules</b></summary>

[Architecture](ARCHITECTURE.md) · [API](docs/API_SPEC.md) · [Privacy](docs/PRIVACY.md) · [Experiments](docs/EXPERIMENTS.md) ·
[Pre-registration](docs/PREREGISTRATION.md) · [Dataset card](docs/DATASET_CARD.md) · [Model card](docs/MODEL_CARD.md) ·
[Demo video script](docs/DEMO_SCRIPT.md) · [Final checklist](docs/FINAL_CHECKLIST.md) · [Task tracker](TASK_TRACKER.md) ·
[Development log](DEVELOPMENT_LOG.md) · [Original blueprint](PROJECT_BLUEPRINT.md).

Reproduce: regenerate the static demo data with `python scripts/export_static_demo.py`; re-run the experiments with the commands in
[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md); drive a build in a real browser with
`node scripts/qa_browser.mjs --dist frontend/dist --edge <browser> --profile <empty dir>`. Single branch `main`; the size budget and a
secret scan are enforced by `scripts/preflight.py` (`--history` audits all of git history).

Possible next steps (not built): a hosted backend, verifying the held-out false-alarm cause and using speaker role and intent,
instance-level behavioural features, access control and audit trails, privacy-preserving sharing of indicator playbooks between
institutions, and an assessment under India's DPDP Act 2023 before any real data.

</details>

## Licence

MIT, copyright 2026 Shriya Patil. See [LICENSE](LICENSE). The data in this repository is synthetic.
