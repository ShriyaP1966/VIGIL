# VIGIL v3.1 — Master Technical Blueprint
**Cross-Channel Scam Intelligence Network · PromptWars × AI Vibeathon 2026 · revised 17 Nov 2026**

> **How to use this file.** Save it in the repo root as `PROJECT_BLUEPRINT.md`. It is the single source of truth. The coding agent (Google Antigravity) must read it fully once, then work **one phase at a time** (§15), proving each phase's **Done means** before starting the next. Section 20 contains the exact prompts to paste. Terms: **MUST** = mandatory requirement; **SHOULD** = recommendation; **LATER** = future idea.

---

## 0. Non-negotiable constraints

| # | Constraint | Consequence |
|---|---|---|
| C1 | Only **Google Antigravity** may cost money. Every other tool, API, dataset and host must be **free**, with an offline fallback. | No paid LLM APIs, databases, hosting, datasets or templates. |
| C2 | Submission = **public GitHub repo**, **one branch (`main`)**, **< 10 MB**, **max 2 submission attempts**. | Size budget (§11), pre-push check script, no stray branches. |
| C3 | Target deadline **25 Nov 2026**. *Verify the official cut-off on the Hack2skill dashboard.* Plan to submit the evening of **24 Nov**. | Phase 8 (25 Nov) is buffer only. |
| C4 | Solo developer + Antigravity (weekly-limited free quota unless upgraded). | Large scoped prompts, short rules, no scope creep (§17). |
| C5 | All data in the repo is **synthetic and labelled synthetic**. No real victim data, no scraped private messages. | Dataset card + `is_synthetic` field everywhere. |
| C6 | The app must run **fully offline with no API keys** (deterministic mode). Gemini is an optional enhancement. | Offline mode is the default and the judge-safe path. |
| C7 | Never state a performance number that a script did not produce. | All metrics come from `scripts/evaluate_model.py` output. |
| C8 | A **free, public deployed link** is also submitted (alongside the GitHub repo). | Static-first deployment (§14): the link always works, even if the free backend is asleep. No card, no paid host. |

### 0.1 Changes from v3.0 (and why)

| # | Change | Reason |
|---|---|---|
| 1 | Association states replace "verified/candidate/disputed": `OBSERVED_MATCH`, `CANDIDATE_ASSOCIATION`, `ANALYST_VERIFIED_ASSOCIATION`, `DISPUTED_ASSOCIATION`, `REJECTED_ASSOCIATION` | An exact identifier match proves only that the same identifier appeared in two evidence records. It does not prove one criminal campaign. v3.0 overclaimed. |
| 2 | Fingerprint redesigned: order-consistency and partial-call tolerance added; **language and channel differences removed as contradictions** | VIGIL is cross-channel and campaigns target many languages. Different language/channel is context, not contradiction. |
| 3 | **Counter-evidence engine** is a first-class component with its own table, rules, API and UI panel | Explain why incidents might *not* be related; never hide contradictions inside a score. |
| 4 | **Evidence inspector** promoted to a core feature with a defined payload | Every claim must trace to its evidence. |
| 5 | "Live Call Mode" renamed **Simulated Live Call Analysis** | It is scripted transcript playback, not call interception. |
| 6 | Risk is an **experimental heuristic**, with a full contribution record per factor | Not a probability; no calibration claimed. |
| 7 | Evaluation tightened: precise arm and rotation definitions, text-similarity baseline, multi-seed runs, false-association rate, candidate precision/recall | Scientific validity. |
| 8 | Preflight redesigned: three distinct size measures, no false failures on `origin/HEAD`, history and secret scanning, lockfiles, fresh-clone test | v3.0 checks could fail falsely and conflated size definitions. |
| 9 | Priority tiers P0–P3 with a protected list; schedule re-timed (counter-evidence → Phase 4, evaluation → Phase 5, UI completion → Phase 6) | Keeps the intelligence engine protected and the plan achievable solo. |
| 10 | Startup section adds what carries over vs. what must be redesigned; risk register added | Realism. |
| 11 | Deployed link made **P0**; static-first deployment design (§14), `deployment/` folder, deploy early (Phase 1) and verify (Phase 7) | The submission requires a deployed link. |

**Kept from v3.0:** offline-first design, playbook-fingerprint differentiator, identifier-rotation experiment, temporal engine, injection guard, synthetic-only data, 10 MB discipline, vertical-slice schedule, dark enterprise UI.

### 0.2 Open items to verify (not assumed)
1. **Official deadline** (assumed 25 Nov; plan submits 24 Nov) — confirm on the Hack2skill dashboard.
2. **Problem statement:** whether participants choose their own or one is assigned at the start.
3. **How the competition measures "under 10 MB"** (working tree, clone/pack size, or GitHub-reported size). The plan keeps a safety margin on all three; confirm with promptwarssupport@hack2skill.com.
4. **Pre-prepared material:** whether planning documents and a pre-written blueprint prepared before the build window are allowed, and whether commit timestamps matter.
5. **Allowed tooling:** Antigravity is required; confirm that using the Gemini API (free key) and a Python/FastAPI stack inside the project is permitted.
6. **Gemini free-tier availability, limits and data-use terms** on the day (may change).
7. **Antigravity free quota** actually remaining (Settings → Models).
8. **Deployed link:** confirm the exact field/format on the dashboard and that the link must stay reachable during judging; confirm free-tier terms of the chosen host on the day.
If any of these conflicts with an official rule, the rule wins; flag it here rather than assuming permission.


---

## 1. Product

### 1.1 One-liner
VIGIL turns scattered scam evidence (call transcripts, messages, links, payment requests) into an **explainable campaign investigation**: what happened, who/what is involved, which incidents are connected, how strong the evidence is, what contradicts it, and what to do next.

### 1.2 The problem
- Digital-arrest and impersonation scams in India follow a **script** (fake authority → false allegation → threat → isolation → urgency → payment demand) delivered over calls, messages and links.
- Existing tools judge **one message at a time** or rely on **known-bad identifiers**. Scammers rotate phone numbers, UPI IDs and domains constantly, so repeat campaigns look like unrelated incidents.
- Fraud teams hold fragmented evidence in spreadsheets, chats and screenshots, and cannot easily see that ten "different" reports are one campaign.

### 1.3 The idea that makes VIGIL different: the Playbook Fingerprint
Identifiers change; the **script** does not. Each incident gets a *behavioural fingerprint*: the ordered tactic-stage sequence, time spent in each stage, impersonated-institution class and payment-channel type. VIGIL then creates **associations** between incidents, each in one of five explicit states:

| State | Meaning | Created by | Edge style |
|---|---|---|---|
| `OBSERVED_MATCH` | The **same normalised identifier** appears in evidence of both incidents. This proves an *observation*, not a common criminal origin. | Exact normalised match only | Solid thin line, label "observed match" |
| `CANDIDATE_ASSOCIATION` | Potentially meaningful link (playbook similarity, fuzzy identifier, or observed match plus supporting behaviour) that **requires investigation** | System | Dashed line with similarity % |
| `ANALYST_VERIFIED_ASSOCIATION` | A human reviewed the evidence and accepted the link | Analyst action only | Solid thick line with check badge |
| `DISPUTED_ASSOCIATION` | High-severity counter-evidence exists | Rule (counter-evidence engine) or analyst | Dashed red line with warning marker |
| `REJECTED_ASSOCIATION` | An analyst rejected the hypothesis | Analyst only | Faded grey; hidden by default |

> **A solid edge means "this identifier was observed in both places", never "confirmed same criminals".** A *campaign hypothesis* is built from associations and stays unconfirmed until an analyst accepts it.

**Research question:** *When identifiers rotate, does behavioural and temporal reasoning improve campaign detection without creating an unacceptable increase in false associations?* It is tested by a four-arm experiment (§8) and is the headline result. If the fingerprint does not beat simpler methods, VIGIL reports that honestly.


### 1.4 Users and value

| User | Value |
|---|---|
| Fraud-operations analysts (fintech, UPI apps, small banks) | See campaigns, not isolated reports; explainable evidence for escalation. |
| Cybersecurity / incident-response teams | Inspect indicators, relationships and timeline; export a report. |
| Telecom and digital-safety teams (later) | Behavioural signatures that survive number rotation. |
| Consumers / families (much later) | Real-time call protection would need telco/OS-level partnerships; the prototype only demonstrates **simulated** transcript analysis and plain-language guidance. |

### 1.5 What VIGIL is **not**
- Not a guaranteed fraud detector or legal-attribution system.
- Not a tool that labels any real person or account as criminal from a graph link.
- Not an automatic bank blocker or call interceptor.
- Not a generic chatbot producing unsupported summaries.
- Not a production enterprise platform in the competition MVP.

---

## 2. Scope and priorities

| Priority | Features | Rule |
|---|---|---|
| **P0 – essential** | Ingest text/transcript/URL; normalisation + provenance; entity extraction; tactic classification (rules + sklearn); exact-match associations (`OBSERVED_MATCH`); candidate associations; temporal engine; playbook fingerprint; counter-evidence engine; campaign hypotheses; risk heuristic with contributions; evidence inspector; scenario lab; evaluation scripts (incl. rotation experiment); preflight + fresh-clone test; README, dataset and model cards | Protected (see below). | **Free deployed link (static-first, §14).**
| **P1 – important** | Simulated Live Call Analysis; Gemini extractor (only if it demonstrably helps); Hinglish/Hindi/Marathi samples; JSON/CSV report export; Settings (mode, clear data); fingerprint ablation E8; Playwright happy-path test | After the P0 slice works end to end. |
| **P2 – optional demo enhancements** | Evidence Library page; faster-whisper local transcription; browser mic input; screenshot OCR; PDF export; WhatsApp-link family-alert demo | Cut first if behind. |
| **P3 – post-hackathon startup** | Accounts/RBAC/workspaces; audit trails; authorised bank/telco integrations; licensed threat feeds; graph database; cross-organisation privacy-preserving sharing; real call-protection partnerships | Not in the MVP. |

**Protected (never cut):** evidence provenance · entity extraction · exact observed matches · candidate-association logic · temporal reasoning · playbook fingerprints · explainable campaign hypotheses · counter-evidence · false-link and decoy testing · reproducible evaluation · offline demonstration · reliable fresh-clone execution.
**Cut order:** P2 → P1 → UI polish and screens → (never the protected list).


---

## 3. Approved tool stack (all free)

> Verify each tool's current free-tier terms on the day you use it. If anything requires a card, trial or upgrade for the core workflow, choose another implementation.

### 3.1 Development

| Tool | Why | Link |
|---|---|---|
| Google Antigravity (**the only paid item**) | Required event tool; agent for planning, code, tests, browser checks | https://antigravity.google |
| Python 3.11+ | Backend + AI engine | https://www.python.org |
| Node.js LTS | Frontend tooling | https://nodejs.org |
| Git | Version control, rollback, single-branch discipline | https://git-scm.com |
| GitHub | Public repo = the submission | https://github.com |
| VS Code (optional) | Manual inspection and small edits | https://code.visualstudio.com |

### 3.2 Backend and data

| Tool | Why | Link |
|---|---|---|
| FastAPI + Uvicorn | Fast, typed, auto-generated API docs | https://fastapi.tiangolo.com · https://www.uvicorn.org |
| Pydantic v2 | Strict request/response and AI-output validation (key for injection safety) | https://docs.pydantic.dev |
| SQLAlchemy 2 | Portable ORM | https://docs.sqlalchemy.org |
| SQLite | Zero-setup local DB; no hosted DB needed | https://www.sqlite.org |
| NetworkX | Graph structures, connected components, no paid graph DB | https://networkx.org |
| RapidFuzz | Fast edit distance for tactic-sequence similarity and fuzzy candidates | https://github.com/rapidfuzz/RapidFuzz |
| python-phonenumbers | Correct Indian phone normalisation | https://github.com/daviddrysdale/python-phonenumbers |
| Faker (optional) | Synthetic names/identifiers for the dataset generator | https://faker.readthedocs.io |

### 3.3 AI / NLP

| Tool | Why | Link |
|---|---|---|
| scikit-learn | TF-IDF + logistic regression baseline, honest evaluation metrics | https://scikit-learn.org |
| spaCy | Rule-based matching, tokenisation, entity utilities (use blank/small models only; keep repo small) | https://spacy.io |
| Gemini API via Google AI Studio (**free key, optional**) | Structured extraction for Hindi/Marathi/Hinglish; schema-constrained JSON output | https://aistudio.google.com · https://ai.google.dev/gemini-api/docs |
| google-genai Python SDK | Official client | https://github.com/googleapis/python-genai |
| faster-whisper (P2) | Local speech-to-text on the laptop GPU; audio never leaves the machine | https://github.com/SYSTRAN/faster-whisper |

> Use a **current Gemini Flash-class model** and read its name from the `GEMINI_MODEL` env var (model names and free-tier limits change; check the docs on the day). **Never commit the key.** Send **synthetic data only** to Gemini and disclose that free-tier API content may be used by the provider.

### 3.4 Frontend

| Tool | Why | Link |
|---|---|---|
| React + TypeScript + Vite | Fast typed SPA | https://react.dev · https://www.typescriptlang.org · https://vite.dev |
| Tailwind CSS | Consistent dark design system from tokens (§12.2) | https://tailwindcss.com |
| React Flow | Interactive graph (zoom, pan, select, custom nodes/edges) | https://reactflow.dev |
| Recharts | Risk timeline, experiment chart | https://recharts.org |
| Lucide | Consistent icons | https://lucide.dev |
| TanStack Query (optional) | Simple data fetching/caching | https://tanstack.com/query |
| Inter / Geist font | Readable dense UI | https://rsms.me/inter · https://vercel.com/font |

### 3.5 Testing and quality

| Tool | Why | Link |
|---|---|---|
| pytest | Backend + engine tests | https://docs.pytest.org |
| Ruff | Python lint/format | https://docs.astral.sh/ruff |
| Vitest | Frontend unit tests | https://vitest.dev |
| Playwright (optional) | One end-to-end happy-path test | https://playwright.dev |
| GitHub Actions (optional) | Run tests on push | https://docs.github.com/actions |

### 3.6 Reference sources (context only; do not scrape)
I4C https://i4c.mha.gov.in · National Cyber Crime Reporting Portal https://cybercrime.gov.in · CERT-In https://www.cert-in.org.in · AI4Bharat https://ai4bharat.iitm.ac.in · Hugging Face datasets (check licences) https://huggingface.co/datasets.

### 3.7 Explicitly **not** used in the MVP
Supabase, PostgreSQL, Docker, Alembic, Neo4j, paid LLM APIs, paid hosting, hosted vector DBs, large transformer models in the repo. (They add time and risk.)


### 3.8 Deployment (free, no card) — for the required deployed link

| Tool | Link | Use / why |
|---|---|---|
| **Vercel** (pick one frontend host) | https://vercel.com | Frontend (Vite static build); GitHub import; free Hobby plan is non-commercial, which fits a hackathon |
| Netlify (alternative) | https://www.netlify.com | Same role; drag-and-drop or GitHub deploy |
| Cloudflare Pages / GitHub Pages (alternatives) | https://pages.cloudflare.com , https://pages.github.com | Static hosting fallbacks |
| **Render** (optional backend) | https://render.com | Free web service for FastAPI; **sleeps when idle and has an ephemeral disk**, so it is an enhancement, never a dependency |
| UptimeRobot (optional keep-alive) | https://uptimerobot.com | Free pings to reduce cold starts; check its terms first |

Free tiers change often: **verify limits and terms on the day**. Never put secrets in the frontend or repo.

---

## 4. Architecture

```
 Browser (React + TS)                          Local laptop / judge machine
 ┌──────────────────────────────┐   REST    ┌───────────────────────────────────────────┐
 │ Pages: Overview, New         │ ───────▶  │ FastAPI (modular monolith)                │
 │ Investigation, Detail, Graph,│           │  api/ → services/ → ai_engine/            │
 │ Campaigns, Scenario Lab,     │ ◀───────  │                                           │
 │ Simulated Live Call, Reports │   JSON    │  ai_engine/                               │
 └──────────────────────────────┘           │   normalise → extract → classify tactics  │
                                            │   → resolve → associate (5 states)        │
                                            │   → temporal → fingerprint → counter-ev.  │
                                            │   Extractor interface:                    │
                                            │     RuleMLExtractor (offline, default)    │
                                            │     GeminiExtractor (optional, free key)  │
                                            │  SQLite (SQLAlchemy) · NetworkX (in-mem)  │
                                            └───────────────────────────────────────────┘
```

**Architecture rule:** modular monolith, not microservices. Clear module boundaries and interfaces, no operational complexity a solo developer cannot maintain.

### 4.1 Processing modes

| Mode | Behaviour | Disclosure shown in UI |
|---|---|---|
| **Offline scenario (default)** | Seeded deterministic scenarios; rules + scikit-learn; no network | "Demo mode: synthetic data, runs locally" |
| **Static demo (deployed)** | Frontend only, reading precomputed synthetic JSON from `frontend/public/demo-data/`; optionally upgrades to the live backend when it responds | "Hosted demo: precomputed synthetic data" |
| **Local** | Optional local transcription (P2); raw audio stays on device | "Audio processed on this device" |
| **Cloud-assisted** | Text sent to Gemini only if `GEMINI_API_KEY` is set | "Text is sent to the Gemini API (free tier). Use synthetic data only." |

### 4.2 Extractor interface (the key abstraction)
```python
class Extractor(Protocol):
    name: str
    version: str
    def analyze(self, utterances: list[Utterance]) -> ExtractionResult: ...
# ExtractionResult: tactic_labels per utterance (+confidence, +evidence span),
#                   entities (type, raw, span), institution_class, payment_channel, language
```
`RuleMLExtractor` and `GeminiExtractor` return the **same Pydantic schema**. If Gemini errors, times out, or returns invalid JSON, fall back to `RuleMLExtractor` and record `fallback_used=true` in the analysis.

---

## 5. Data model

### 5.1 Tables (SQLite via SQLAlchemy)

| Table | Columns |
|---|---|
| `incidents` | id, title, source_channel (call/sms/email/web), language, status (open/reviewed), scenario_id (nullable), is_synthetic, created_at |
| `evidence` | id, incident_id, type (transcript/message/url/payment_request), original_text, normalised_text, sha256, timestamp, provenance (e.g. "seed:scenario_07", "user_paste") |
| `utterances` | id, evidence_id, idx, speaker, text, t_start_sec (nullable), language |
| `entities` | id, type, canonical_value, display_value (masked), norm_method, first_seen, last_seen |
| `mentions` | id, entity_id, evidence_id, utterance_id, span_start, span_end, extraction_confidence, extractor |
| `relationships` | **structural edges only:** id, source_id, target_id, relation_type (MENTIONS_ENTITY, USES_PHONE, USES_DOMAIN, REQUESTS_PAYMENT_TO, CLAIMS_TO_REPRESENT, EXHIBITS_TACTIC, CONTAINS_EVIDENCE), evidence_id, confidence |
| `associations` | **cross-incident claims:** id, incident_a_id, incident_b_id, match_type (EXACT_IDENTIFIER / PLAYBOOK / FUZZY_IDENTIFIER / COMBINED), status (5 states, §5.4), shared_entity_ids_json, similarity (nullable), base_confidence, adjusted_confidence, component_scores_json, supporting_evidence_json (evidence ids + excerpt spans), explanation, algorithm_version, created_at, updated_at |
| `counter_evidence` | id, association_id (nullable), campaign_id (nullable), rule_id (CE-1…), kind, observation, evidence_refs_json, severity (LOW/MEDIUM/HIGH), confidence_impact, explanation, rule_version, created_at |
| `reviews` | id, target_type (association/campaign), target_id, decision (ACCEPT/REJECT/FLAG), note, previous_status, new_status, created_at (analyst review events; also the status history) |
| `campaigns` | id, hypothesis_title, status (HYPOTHESIS_UNREVIEWED / ACCEPTED_BY_ANALYST / REJECTED_BY_ANALYST / FLAGGED), confidence, weakest_link_association_id, algorithm_version, created_at |
| `campaign_members` | campaign_id, incident_id, membership_basis (OBSERVED / CANDIDATE / ANALYST) |
| `tactic_events` | id, incident_id, utterance_id, label, confidence, extractor, evidence_span |
| `analyses` | id, incident_id, extractor, extractor_version, fallback_used, fingerprint_json, risk_score, risk_band, risk_version, injection_flags_json, created_at |
| `risk_contributions` | id, analysis_id, factor, evidence_ref, rule_version, contribution (signed), effect (SUPPORTING/MITIGATING), explanation |


### 5.2 Entity types
`PHONE, EMAIL, DOMAIN, URL, UPI_HANDLE, ORGANISATION (claimed), INCIDENT, TACTIC, CAMPAIGN`

### 5.3 Relationship types
`CONTAINS_EVIDENCE, MENTIONS_ENTITY, CLAIMS_TO_REPRESENT, REQUESTS_PAYMENT_TO, USES_DOMAIN, USES_PHONE, EXHIBITS_TACTIC, POTENTIALLY_RELATED_TO, BELONGS_TO_CAMPAIGN`

### 5.4 Enums
- **Tactic labels:** `AUTHORITY_IMPERSONATION, FALSE_ALLEGATION, THREAT_INTIMIDATION, ISOLATION, URGENCY, FINANCIAL_DEMAND, CREDENTIAL_REQUEST, LEGITIMATE, OTHER_SUSPICIOUS` (multi-label per utterance)
- **Canonical stages (temporal engine):** `AUTHORITY, ALLEGATION, THREAT, ISOLATION, URGENCY, DEMAND` (+ `CREDENTIAL` as a parallel branch)
- **Institution class:** `CENTRAL_AGENCY, POLICE, BANK, TELECOM, COURIER_CUSTOMS, GOVT_OTHER, UNKNOWN`
- **Payment channel:** `UPI, BANK_TRANSFER, CRYPTO, GIFT_CARD, LINK_PAYMENT, NONE, UNKNOWN`
- **Association status:** `OBSERVED_MATCH, CANDIDATE_ASSOCIATION, ANALYST_VERIFIED_ASSOCIATION, DISPUTED_ASSOCIATION, REJECTED_ASSOCIATION`
- **Campaign status:** `HYPOTHESIS_UNREVIEWED, ACCEPTED_BY_ANALYST, REJECTED_BY_ANALYST, FLAGGED`
- **Counter-evidence severity:** `LOW, MEDIUM, HIGH`
- **Risk bands (heuristic indicator, not a probability):** `LOW 0–29, ELEVATED 30–59, HIGH 60–79, CRITICAL 80–100`


### 5.5 Privacy-aware identifiers
Store `canonical_value` for matching, show `display_value` masked (e.g. `+91 98•••••21`, `ab•••@bank`). Do not store OTPs, passwords, full card numbers or bank credentials; detect and redact them on ingest and flag `CREDENTIAL_REQUEST` without storing the secret.

---

## 6. Intelligence engine (specifications)

### 6.1 Ingestion and normalisation
- Accept pasted text, transcript with speaker turns, or a URL string. **Never fetch or browse submitted URLs** (no unsafe browsing); parse only.
- Normalise: Unicode NFKC, strip zero-width characters, lower-case for matching, collapse whitespace; keep the original text unchanged and hash it (SHA-256).
- Detect language (simple script + keyword heuristic is enough): `en | hi | hi-Latn (romanised Hindi/Hinglish) | mr | mixed`.

### 6.2 Entity extraction (offline-capable)

| Entity | Method |
|---|---|
| Phone | regex + `phonenumbers` (region `IN`) → E.164 |
| UPI handle | regex `[A-Za-z0-9.\-_]{2,256}@[A-Za-z]{2,64}` excluding emails with a dot-TLD domain |
| Email | regex; lower-case |
| URL / domain | regex + `urllib.parse`; punycode/IDN decode; strip tracking params; domain = registered host |
| Organisation (claimed) | gazetteer (CBI, ED, NCB, RBI, TRAI, Customs, Mumbai Police/Cyber Cell, major banks, courier brands) + fuzzy match |

Every extracted entity records `norm_method` and the text span.

### 6.3 Tactic classification (3 tiers, one schema)
1. **Tier 1 – Deterministic rules/lexicon** (Appendix A): high-precision, explainable, always on.
2. **Tier 2 – scikit-learn:** TF-IDF (word + character n-grams, which helps romanised Hindi) + Logistic Regression, one-vs-rest multi-label. Trained in seconds from `data/`; no model file committed.
3. **Tier 3 – optional Gemini** (free key): schema-constrained JSON for labels + spans + entities only; never for decisions. **Enable only if** a free key is available **and** on the dev split it measurably improves macro-F1 over Tier 2 (or demonstrably handles Hindi/Marathi where Tier 2 fails). Otherwise ship without it and say so.
All tiers return the same Pydantic-validated `ExtractionResult`. Final label = rule hit OR classifier probability ≥ threshold (config); store which tier fired. **Split by campaign template** to prevent paraphrase leakage. Avoid extra model complexity.


### 6.4 Prompt-injection guard (transcripts are untrusted input)
1. Wrap text in explicit delimiters; system instruction says the content is **data, not instructions**.
2. Require strict JSON schema; validate with Pydantic; reject/fallback on anything else.
3. Give the model **no tools or actions**; it can only return labels/entities.
4. Regex layer flags instruction-like phrases (e.g. "ignore previous instructions", "mark this call as safe", "you are now", "system prompt") → `injection_flags`, show **"Manipulation attempt detected"** badge, and **never lower the risk because of the flagged text**.
5. Ship 10 attack transcripts in the test set (§7). Report how many are neutralised (badge fires and labels/risk unchanged).

### 6.5 Entity resolution and association policy

| Evidence | Resulting association |
|---|---|
| Exact normalised identifier equality (phone / UPI / domain / email / URL) | `OBSERVED_MATCH`, with evidence references and explanation |
| Fuzzy / semantic identifier similarity | `CANDIDATE_ASSOCIATION` only (needs more evidence or review) |
| Playbook similarity ≥ threshold with no shared identifier | `CANDIDATE_ASSOCIATION` (match_type PLAYBOOK) |
| Partial/ambiguous identifier | Keep separate; never merge entities |
| High-severity counter-evidence (§6.10) | `DISPUTED_ASSOCIATION` |
| Analyst accepts / rejects | `ANALYST_VERIFIED_ASSOCIATION` / `REJECTED_ASSOCIATION` |

**Safety invariants (MUST be unit-tested):**
- **I1:** an `OBSERVED_MATCH` can exist only if the normalised identifiers are exactly equal.
- **I2:** no fingerprint, ML or Gemini output can create `OBSERVED_MATCH` or `ANALYST_VERIFIED_ASSOCIATION`.
- **I3:** `ANALYST_VERIFIED_ASSOCIATION` requires an explicit analyst review recorded in `reviews`.
- **I4:** a campaign is always presented as a *hypothesis* until an analyst accepts it; no UI text or report says "confirmed campaign" or implies criminal attribution.
- **I5:** every association has ≥ 1 evidence reference and a plain-language explanation; counter-evidence is stored separately and always displayed next to it.
Observed matches on well-known public identifiers (official helplines, bank domains) still create `OBSERVED_MATCH` but trigger counter-evidence rule CE-3.


### 6.6 Temporal engine
Per incident build an ordered event list: `(t or index, speaker, text, labels, confidence, evidence_ref)`.
- **Stage mapping:** `AUTHORITY → ALLEGATION → THREAT → ISOLATION → URGENCY → DEMAND` (`CREDENTIAL` is a parallel branch).
- Compute the de-duplicated **stage sequence** (first-occurrence order), **dwell profile** (share of turns or seconds per stage), repetition, gaps, and **completeness** (stages seen ÷ canonical stages). **Partial sequences are valid** (calls get cut off).
- **Cross-incident temporal reasoning** (used in evaluation arm C): (a) *chronology check* — shared stages in conflicting relative order raise counter-evidence CE-1; (b) *recurrence window* — observed matches within a configurable window (default 90 days of synthetic timestamps) are mildly supporting, while reuse beyond the window raises CE-8 (identifier may have been recycled).
- Output: `fingerprint = {sequence, dwell_profile, institution_class, payment_channel, language, channel, completeness}`.


### 6.7 Playbook fingerprint similarity
**Design principles.** Tactic sequence is the strong behavioural signal; stage *ordering* is the main contradiction signal; institution class and payment channel are supporting (scammers rotate them); dwell time is optional; **language and communication channel do not enter the score** (cross-channel, multilingual campaigns are expected) and are shown only as neutral context.

**Inputs per incident:** stage sequence `S`, dwell profile `D`, institution class `I`, payment channel `P`; context: language `L`, channel `C`.

```
lcs          = length of longest common subsequence of S_A and S_B
lcs_sim      = lcs / max(|S_A|, |S_B|)                       strict similarity
containment  = lcs / min(|S_A|, |S_B|)                       tolerates cut-off calls
containment_adj = containment * min(1, min(|S_A|,|S_B|) / 4) a 2-stage fragment cannot match strongly
order_ok     = fraction of stage pairs present in both sequences that appear in the same relative order
seq_sim      = 0.40*lcs_sim + 0.30*containment_adj + 0.30*order_ok
inst_match   = 1 if equal, 0.5 if either is UNKNOWN, else 0
pay_match    = 1 if equal, 0.5 if either is NONE/UNKNOWN, else 0
dwell_sim    = 1 - 0.5 * L1 distance of dwell profiles restricted to shared stages (renormalised); missing => component omitted
playbook_sim = 0.65*seq_sim + 0.15*inst_match + 0.10*pay_match + 0.10*dwell_sim   (omitted components: renormalise remaining weights)
```
**Gate:** an association is created only if both incidents have ≥ 3 distinct stages **and** `lcs ≥ 3`; then `playbook_sim ≥ T_candidate` (default 0.75) → `CANDIDATE_ASSOCIATION` with `base_confidence = playbook_sim` and the component breakdown stored in `component_scores_json`.
**Assumptions (documented in MODEL_CARD):** (A1) scam scripts reuse a recognisable stage order; (A2) institution and payment type support but do not define a campaign; (A3) targeted language varies within one campaign; (A4) stage extraction is imperfect, hence containment and damping; (A5) weights are **a-priori design choices, not learned**.
**Tuning and evaluation:** tune `T_candidate` on the **dev split only** (grid 0.60–0.90; choose the best dev F1 subject to a maximum false-association rate you pre-declare); test weight sensitivity and leave-one-component-out ablations on dev (experiment E8); report final numbers once on test and held-out. **Fingerprint similarity alone can never create `OBSERVED_MATCH` or `ANALYST_VERIFIED_ASSOCIATION` (I2).** Legitimate calls (authority claim only, no threat/isolation/demand) must fail the gate.


### 6.8 Campaign hypotheses
1. Build a graph of incidents and entities; load associations.
2. **Seeds:** connected components over `OBSERVED_MATCH` associations that carry no high-severity counter-evidence → hypothesis with `membership_basis = OBSERVED`.
3. **Extension:** incidents joined only through `CANDIDATE_ASSOCIATION` edges are added as `membership_basis = CANDIDATE` (visibly weaker).
4. `DISPUTED_ASSOCIATION` and `REJECTED_ASSOCIATION` edges do **not** connect components, but are still listed on the hypothesis with their counter-evidence.
5. Hypothesis `confidence` = mean `adjusted_confidence` of its associations, always shown together with the **weakest link**; `status = HYPOTHESIS_UNREVIEWED`.
6. Analyst actions (`POST …/review`) write `reviews` rows: ACCEPT (association → `ANALYST_VERIFIED_ASSOCIATION`; campaign → `ACCEPTED_BY_ANALYST`), REJECT, FLAG. Counter-evidence stays visible after acceptance.
The UI and reports use the words "campaign **hypothesis**" until accepted.


### 6.9 Risk indicator (experimental heuristic)
The **incident risk indicator** (0–100) says how scam-like an incident's own evidence is. It is an **experimental heuristic, not a probability of fraud**, and is **not calibrated** (never claim calibration unless a calibration experiment was actually run, and even then only on synthetic data). It is separate from **association confidence** (§6.10), which says how strong a *link* is; never conflate them.

`risk = clip( Σ supporting − Σ mitigating , 0, 100 )`, weights in `config/risk_weights.json` (initial priors, versioned `risk@3.1.x`):

| Factor | Effect | Default |
|---|---|---|
| F1 tactic presence (per distinct stage: AUTH +6, ALLEG +10, THREAT +14, ISOL +16, URG +8, DEMAND +18, CRED +18) | supporting | capped at +70 |
| F2 canonical order observed (≥ 3 stages in order) | supporting | +10 |
| F3 `OBSERVED_MATCH` to an incident of band ≥ ELEVATED | supporting | +6 each, cap +12 |
| F4 `CANDIDATE_ASSOCIATION` with sim ≥ T | supporting | +5 (uncertain, capped) |
| M1 benign-context cues (no request for money/credentials; directs to official channel) | mitigating | −15 |
| M2 weak evidence (single stage, low confidence) | mitigating | −10 |
| M3 uncertain extraction | mitigating | −5 |

**Every contribution is stored** in `risk_contributions` with: **factor, evidence reference, rule/model version, signed contribution, supporting/mitigating effect, and a plain-language explanation**; the UI lists them ranked and they sum exactly to the displayed score. Contradictory evidence is shown in its own panel (§6.10), not folded into this number. Weights are set a priori and adjusted **only on the dev split**; the held-out test set is never used to tune them. **Injected text can never lower risk:** flagged spans are excluded from mitigating factors and a test asserts that appending injection text never reduces the score. Use cautious wording ("matches a known scam pattern", "requires review").

### 6.10 Counter-evidence engine
VIGIL must say why incidents might **not** be related. Rules run over every association (and, aggregated, every campaign hypothesis). Each finding is stored in `counter_evidence` with: **contradictory observation, source evidence references, severity, impact on association confidence, and an explanation** — it never disappears into an opaque score.

| Rule | Kind | Trigger | Severity | Default impact |
|---|---|---|---|---|
| CE-1 | INCOMPATIBLE_CHRONOLOGY | ≥ 3 shared stages with `order_ok < 0.6` | HIGH | −0.30 |
| CE-2 | DIFFERENT_PAYMENT_DESTINATION | incidents share a phone/domain but their payment handles/accounts differ (both present) | MEDIUM | −0.10 |
| CE-3 | BENIGN_CONTEXT_IDENTIFIER | shared identifier is on the public-identifier allowlist (`data/public_identifiers.json`) or appears in an incident labelled LEGITIMATE | HIGH | −0.40 |
| CE-4 | WEAK_ENTITY_EXTRACTION | any supporting entity has extraction confidence < 0.7 or ambiguous normalisation (partial number, truncated domain) | MEDIUM | −0.15 |
| CE-5 | INCONSISTENT_IMPERSONATION | institution classes differ and neither is UNKNOWN | MEDIUM | −0.10 |
| CE-6 | SINGLE_WEAK_SIGNAL | association rests on exactly one signal whose strength < 0.6 | MEDIUM | −0.15 |
| CE-7 | LANGUAGE_DIFFERENCE | languages differ (context only) | LOW | −0.02 |
| CE-8 | TEMPORAL_GAP | shared identifier reused beyond the recurrence window (possibly recycled) | LOW | −0.10 |

**Mechanism:** `base_confidence` priors — exact UPI 0.75, phone 0.70, URL 0.70, domain 0.65, email 0.65, +0.05 per extra distinct shared identifier (cap +0.15); candidate playbook associations use `playbook_sim`. Then `adjusted_confidence = clip(base_confidence + Σ impacts, 0, 1)`. **Any HIGH finding sets the status to `DISPUTED_ASSOCIATION`** (an analyst decision overrides the status but never hides the finding). Impacts are initial priors, set on dev only, documented in MODEL_CARD, not probabilities. Tests: a positive and a negative case per rule; DISPUTED transition; findings still shown after analyst acceptance.


---

## 7. Dataset (synthetic, small, honest)

### 7.1 Composition (planning targets; adjust to what you can generate well)

| Component | Target | Notes |
|---|---|---|
| Campaign templates | 6 templates × 12–15 variants ≈ 80 | 3 digital-arrest variants, bank KYC, payment link, courier/customs; identifiers rotated per the rotation parameter |
| Legitimate negatives | ≈ 40 | genuine bank alerts, courier updates, real police verification, family calls |
| Decoys | ≈ 20 | (a) similar wording, different origin; (b) **shared identifier in a benign context** (e.g. an official helpline); (c) **same tactics, incompatible chronology**; (d) ambiguous extraction. **Must not form a confident campaign.** |
| Injection attacks | 10 | try to flip labels/risk |
| Hand-written held-out set | ≈ 25 | **written by you, not by the agent**, never used for training or tuning |

Languages: English, romanised Hindi / Hinglish, a few Devanagari Hindi and Marathi samples. Sizes are planning targets, not claims of statistical sufficiency.


### 7.2 Generator (`scripts/generate_dataset.py`)
Slot-based templates (stages × phrasings × speaker turns × timing), seeded RNG (`--seed`), identifier-rotation parameter (`--rotation 0.0–1.0`), Faker for names, writes JSONL. Output must be **< 1 MB total**. Include a validator that checks schema, label vocab, and that no real-looking secrets appear.

### 7.3 Fields
`conversation_id, incident_id, evidence_id, utterance_id, speaker, language, source_channel, text, tactic_labels, t_start_sec, timestamp, scenario_type, campaign_template_id, campaign_instance_id (ground truth, null for negatives/decoys), decoy_type, rotated_fields, entity_mentions, expected_associations, is_synthetic, provenance, generator_version, seed, split (train|dev|test|heldout)`
Ground truth: two incidents are a **true pair** iff they share a non-null `campaign_instance_id`.


### 7.4 Splits
Split **by `campaign_template_id`** (and keep decoys/injection sets separate) so paraphrases of one template never straddle train/test. Document the split in `docs/DATASET_CARD.md`.

---

## 8. Evaluation (all metrics from scripts)

### 8.1 Definitions (fixed before any experiment)
- **Rotation level r:** for each campaign instance, every identifier (phone, UPI, domain) is independently replaced by a fresh synthetic one with probability r between successive incidents. r ∈ {0, 0.25, 0.5, 0.75, 1.0}; r = 1.0 means no shared identifiers.
- **Arm A — text-similarity / classifier-only baseline:** incident-level tactic classification plus grouping of incidents by TF-IDF cosine similarity of their text. No entity graph, no temporal reasoning.
- **Arm B — identifier graph:** campaigns = connected components over `OBSERVED_MATCH` associations.
- **Arm C — B + temporal reasoning:** adds chronology checks and the recurrence window (CE-1, CE-8, stage sequences). We test, not assume, whether this helps precision, recall or neither.
- **Arm D — C + playbook fingerprint:** adds `CANDIDATE_ASSOCIATION` edges (§6.7).
- **Predicted campaigns** for scoring: connected components over associations with status `OBSERVED_MATCH` or `CANDIDATE_ASSOCIATION` (not DISPUTED/REJECTED). Report two variants: *observed-only* and *observed + candidate*. Analyst review is not simulated.
- **Pairwise campaign metrics:** over all incident pairs, precision / recall / F1 of "same predicted component" vs. "same `campaign_instance_id`".
- **Two ground truths, reported side by side (decision recorded 17 Nov 2026, before any experiment was run).** *(a) Campaign-instance ground truth* (the definition above): a true pair shares a `campaign_instance_id`. *(b) Script-family ground truth:* a true pair shares a `campaign_template_id` among campaign incidents (so incidents of different instances that run the same script are true pairs); negatives and decoys are non-pairs under both. Every table and chart in `docs/EXPERIMENTS.md` shows (a) and (b) together for every arm and rotation level, and states plainly that under (a) the fingerprint is expected to have low precision, because in the generator different instances of one template run an identical script (a preliminary train/dev diagnostic gave precision of about 0.2 with no cross-script false links). The fingerprint is described everywhere as recognising a **script family / playbook**, never a specific group, person or organisation. **No behavioural habits, instance-specific phrasing or stage-order quirks are added to the generator after results have been seen.**
- **False association rate:** share of ground-truth *non-pairs* (including negatives and decoys) that end up in the same predicted component.
- **Candidate association precision / recall:** among `CANDIDATE_ASSOCIATION` edges, the share that are true pairs; and the share of true pairs not already covered by observed matches that candidates recover.

### 8.2 Experiments

| ID | Experiment | Metrics | Command |
|---|---|---|---|
| E1 | Tactic classification (campaign-template-held-out) | macro-F1, per-label P/R | `python scripts/evaluate_model.py --suite tactics` |
| E2 | Entity extraction | P/R/F1 per entity type | `--suite entities` |
| E3 | Association integrity and decoys | false association rate; false `OBSERVED_MATCH` count (**must be 0**, invariant I1); legitimate-negative false-positive rate | `--suite associations` |
| E4 | **Identifier-rotation experiment (hero)** | pairwise campaign P/R/F1, false association rate, candidate P/R for arms A–D at r = 0 … 1, **≥ 10 seeds, mean ± std** | `--suite rotation --seeds 10` |
| E5 | Injection robustness | share of attacks neutralised (badge fires, labels and risk unchanged) | `--suite injection` |
| E6 | Hand-written held-out set | tactic macro-F1; false-positive rate on legitimate calls | `--suite heldout` (**run once, at the end**) |
| E7 | Latency | per-stage and end-to-end ms | `--suite latency` |
| E8 (P1) | Fingerprint ablation / weight sensitivity (dev only) | leave-one-component-out, ±weight sweeps, language-penalty 0 / 0.02 / 0.05 | `--suite fingerprint-ablation` |

### 8.3 Rules
**Fixed before running (17 Nov 2026):** both ground truths in §8.1 are reported; the generator and its templates are frozen for the evaluation (any change is made and logged before results exist, never in response to them).
Train, tune and choose thresholds on **train/dev templates only**; final numbers on **unseen test templates**; the hand-written held-out set is evaluated once. All randomness is seeded and recorded. Record dataset version, generator version, split, seeds, extractor/risk/fingerprint versions, `T_candidate`, environment, config hash and exact command in `docs/EXPERIMENTS.md` and `docs/experiments/*.json`. **Never invent or round up results.** If arm D does not beat B or C, report that honestly and show at which rotation levels it helps or hurts. State that all data is synthetic and that results do not imply real-world performance. The README shows the rotation chart (generated from the JSON; PNG < 200 KB).


---

## 9. API contract (`/api/v1`, JSON, Pydantic schemas, request-ID header, consistent error body `{error:{code,message,request_id}}`)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/incidents` | Create incident `{title, source_channel, language, notes?}` |
| POST | `/incidents/{id}/evidence` | Attach evidence `{type, text|url, timestamp?, speaker_turns?}` (size/type-limited) |
| POST | `/analyze/{incident_id}` | Run the full pipeline → analysis, associations, counter-evidence, risk contributions |
| GET | `/incidents` · `/incidents/{id}` | List (paginated, filters) · detail incl. analysis |
| GET | `/graph?types=&status=&min_conf=&include_rejected=false` | Nodes (incidents, entities) + structural edges + associations with status |
| GET | `/associations/{id}` | **Evidence-inspector payload** (below) |
| POST | `/associations/{id}/review` | `{decision: ACCEPT|REJECT|FLAG, note?}` → status change + `reviews` row |
| GET | `/campaigns` · `/campaigns/{id}` | Campaign hypotheses · detail (members, weakest link, counter-evidence) |
| POST | `/campaigns/{id}/review` | `{decision, note?}` |
| POST | `/simulations/live-call/analyze` | **Simulated** progressive transcript window → stage, risk, guidance, flags (no real call involved) |
| GET | `/scenarios` · POST `/scenarios/{name}/run` | List · deterministic replay (optional `rotation`) |
| GET | `/incidents/{id}/report?format=json|csv` | Export: facts / inferences / analyst decisions / limitations |
| GET | `/evidence?q=` | (P2) Evidence Library search |
| DELETE | `/data?confirm=true` | Clear all local data |
| GET | `/health` | App, DB, extractor mode, version |

**Inspector payload (`GET /associations/{id}`):**
```json
{ "id": 14, "status": "CANDIDATE_ASSOCIATION", "match_type": "PLAYBOOK",
  "incidents": [{"id": 3, "title": "..."}, {"id": 9, "title": "..."}],
  "similarity": 0.81, "base_confidence": 0.81, "adjusted_confidence": 0.69,
  "component_scores": {"seq_sim": 0.88, "inst_match": 1.0, "pay_match": 0.5, "dwell_sim": 0.74},
  "shared_entities": [],
  "evidence": [{"evidence_id": 31, "incident_id": 3, "timestamp": "...", "excerpt": "...", "span": [120, 168],
                "entity": null, "normalisation": null, "extractor": "rules@1.0"}],
  "counter_evidence": [{"rule_id": "CE-5", "kind": "INCONSISTENT_IMPERSONATION", "severity": "MEDIUM",
                        "observation": "...", "evidence_refs": [31, 44], "confidence_impact": -0.10, "explanation": "..."}],
  "explanation": "Both incidents follow the same 5-stage sequence ...",
  "versions": {"algorithm": "fingerprint@3.1.0", "extractor": "rules@1.0"},
  "review": {"state": "UNREVIEWED", "history": []} }
```
**Simulated call response:**
```json
{ "simulation": true, "stage": "ISOLATION", "stages_seen": ["AUTHORITY","ALLEGATION","THREAT","ISOLATION"],
  "risk": {"score": 72, "band": "HIGH", "heuristic": true,
           "contributions": [{"factor":"F1 tactic presence","evidence_ref":"u4","contribution":16,"effect":"SUPPORTING","rule_version":"risk@3.1.0","explanation":"..."}]},
  "guidance": {"en": "This transcript matches a known scam pattern. Hang up and call the official number yourself.", "hi": "..."},
  "injection_flags": [], "extractor": "rules@1.0", "fallback_used": false }
```
Validate and limit input; consistent errors; rate-limit `/analyze` and the simulation endpoint.


---

## 10. Security, privacy, responsible use
- Microphone only after an **explicit user action**; no covert recording; **no call interception**; no unnecessary raw-audio storage. Note: Chrome's browser speech recognition may process audio in the cloud, so the **default Simulated Live Call Analysis uses scripted/pasted transcripts (no mic)**; mic input is optional and clearly disclosed.
- Secrets only in gitignored `.env`; commit `.env.example`. Never hardcode keys. Search git history before submitting.
- Validate and cap input size/type; treat all evidence text as untrusted; never render evidence as HTML (escape it).
- Mask identifiers in the UI; do not store OTPs, passwords, card numbers.
- **Trust and safety rules:** never identify a real person/account as criminal from similarity or a graph link; never mark a campaign "confirmed" from a hypothesis; always show uncertainty and contradictions; distinguish **observed fact / model inference / analyst-verified**; keep a human in the loop for consequential conclusions; give protective advice only — VIGIL does not claim to report crimes or block transactions.
- Add basic rate limiting on `/simulations/live-call/analyze` and `/analyze`; document retention (data is local and deletable via a "Clear all data" button).
- Startup-stage compliance (not MVP): India's DPDP Act 2023 obligations, data-retention policy, legal review of data sources — see §18.

---

## 11. Repository layout and the 10 MB discipline

```
vigil/
  PROJECT_BLUEPRINT.md  README.md  ARCHITECTURE.md  TASK_TRACKER.md  DEVELOPMENT_LOG.md
  .gitignore  .env.example
  frontend/            (src/{components,pages,hooks,services,types,styles}, package.json, package-lock.json, vite config)
  backend/             (app/{api,core,models,schemas,services}, tests/, requirements.txt pinned with ==)
  ai_engine/           (extraction/, classification/, resolution/, graph/, temporal/, fingerprint/, counter_evidence/, risk/, evaluation/)
  config/              (risk_weights.json, thresholds.json, counter_evidence_rules.json)
  data/                (scenarios.jsonl, heldout.jsonl, lexicon.json, public_identifiers.json)   # < 1 MB total
  scripts/             (generate_dataset.py, train_classifier.py, evaluate_model.py, run_demo.py, preflight.py, install_hooks.py, plot_results.py, export_static_demo.py) 
  docs/                (API_SPEC.md, DATASET_CARD.md, MODEL_CARD.md, EXPERIMENTS.md, PRIVACY.md, img/, experiments/)
  deployment/          (render.yaml, vercel.json or netlify.toml, DEPLOY.md)
  frontend/public/demo-data/   (static demo export, generated by scripts/export_static_demo.py)
```

### 11.1 Size budget

| Item | Target |
|---|---|
| Backend + AI source | < 1 MB |
| Frontend source (no `node_modules`) | < 1.5 MB |
| Data (JSONL/JSON) | < 1 MB |
| Static demo export (`demo-data/`) | < 0.5 MB |
| Docs + screenshots (≤ 8, each < 200 KB) | < 2 MB |
| **Total tracked** | **aim < 5 MB; hard limit 10 MB** |

### 11.2 `.gitignore` must include
`node_modules/ .venv/ venv/ __pycache__/ *.pyc .env *.db *.sqlite* dist/ build/ .pytest_cache/ .ruff_cache/ *.pt *.onnx *.bin *.safetensors models/ *.mp4 *.mov *.wav *.mp3 .DS_Store`
Trained sklearn models: **do not commit**; `scripts/train_classifier.py` regenerates them in seconds from `data/` (or commit a tiny `.joblib` only if < 200 KB).

### 11.3 `scripts/preflight.py` — three different size measures, no false failures
Modes: `--quick` (default; before every commit/push) and `--history` (before submission; slower). Exit code 0 = pass, 1 = fail; warnings are printed.

**Three measures (never interchangeable):**

| # | Measure | How | Warn / Fail |
|---|---|---|---|
| M1 | **Tracked working-tree size** | sum of sizes of files listed by `git ls-files` that exist on disk | warn > 5 MB, fail > 8 MB; any single file > 500 KB fails (allowlist: lockfile ≤ 700 KB; images in `docs/img` ≤ 200 KB) |
| M2 | **Git repository storage size** | `git gc` then `git count-objects -vH` (`size-pack` + loose `size`) | warn > 6 MB, fail > 9 MB |
| M3 | **Hosted size as reported by GitHub** (after push; informational until the competition defines its own) | `gh api repos/<owner>/<repo> --jq .size` (KB) or the repo's settings page; GitHub updates this lazily, so re-check after a few minutes | fail > 9 MB |
The competition's own definition is unknown (§0.2): keep margin on **all three**.

**Branch checks (must not fail on normal remote-tracking refs):**
- current branch is `main`;
- local branches: `git for-each-ref refs/heads` lists exactly `main`;
- remote branches: `git ls-remote --heads origin` lists only `refs/heads/main` (skipped with a warning if offline);
- **ignore** `refs/remotes/origin/HEAD` (a symbolic ref) and `origin/main`; tags only produce a warning.

**Tracked-content checks:** no `.env`, `*.db`, `*.sqlite*`, `node_modules/`, `.venv/`, model/media/archive files (`*.pt *.onnx *.bin *.safetensors *.mp4 *.mov *.wav *.mp3 *.zip *.parquet`); required `.gitignore` patterns present; **lockfiles present** (`frontend/package-lock.json`; `backend/requirements.txt` with pinned `==` versions).
**Secret scan** over tracked text files: Google API key `AIza[0-9A-Za-z_-]{35}`, GitHub tokens `gh[pousr]_[A-Za-z0-9]{36,}`, private-key headers, and generic `(api[_-]?key|secret|token|password)\s*[:=]\s*['"]?[A-Za-z0-9_-]{16,}`; `.env.example` placeholders with empty values are allowed.
**`--history`:** list the 10 largest blobs ever committed (`git rev-list --objects --all` piped to `git cat-file --batch-check`) and **fail if any historical blob > 1 MB**; run the secret patterns across all revisions (`git grep -I -nE <pattern> $(git rev-list --all)`). Inspect manually if anything is reported.
**Hook:** `scripts/install_hooks.py` writes a local `.git/hooks/pre-push` that runs `preflight.py --quick` (hooks are not tracked or pushed).


### 11.4 Git rules
Work on `main` only; commit at every green milestone; use `git status` and `git diff --cached --stat` before committing; add specific paths rather than `git add -A` when unsure. Run `python scripts/preflight.py` before every push. **Never commit a large file and delete it later as a size-management strategy:** history keeps it and it still counts toward repository storage. Delete any stray branch the agent creates. Commit `frontend/package-lock.json` and a pinned `backend/requirements.txt`.

### 11.5 Fresh-clone test (before submitting)
1. In a **new empty folder outside the project**, `git clone` the public URL (use a private/incognito browser to confirm the repo is public).
2. Confirm only `main` exists (`git branch -a` there, ignoring `origin/HEAD`).
3. Follow **only the README**: create venv, `pip install -r backend/requirements.txt`, `npm ci`, `python scripts/run_demo.py` in offline mode with **no `.env`**.
4. Run `pytest -q`, `npm test`, `python scripts/evaluate_model.py --suite tactics --quick`, and `python scripts/preflight.py --history` inside the clone.
5. Record the time taken and any README gaps in `DEVELOPMENT_LOG.md`; fix and repeat until it passes.


---

## 12. UI / UX design

### 12.1 Principles
Enterprise-grade, calm, **dense but readable**; evidence first; every claim clickable to its source; uncertainty always visible; restrained motion; no decorative gradients, fake activity indicators, oversized headings or dead buttons; every screen has **loading, empty, error and success** states; keyboard accessible (WCAG AA contrast, visible focus rings, `aria-label`s); a table view alternative to the graph for accessibility and screen readers.

### 12.2 Design tokens

| Token | Value |
|---|---|
| bg-main / sidebar / card / elevated | `#0B1020` / `#0F172A` / `#111827` / `#1E293B` |
| border | `#263248` |
| accent primary / secondary | `#38BDF8` / `#2DD4BF` |
| risk low / elevated / high / critical | `#22C55E` / `#EAB308` / `#F59E0B` / `#EF4444` |
| text primary / secondary / muted | `#F8FAFC` / `#94A3B8` / `#64748B` |
| Font | Inter (UI), JetBrains Mono (ids/hashes/code) |
| Radius / spacing | 10 px cards, 6 px inputs; 4-pt spacing scale |
Implement as Tailwind theme extensions + CSS variables so a light theme can be added later.

### 12.3 Layout
Persistent **left sidebar**: Overview, Investigations, Intelligence Graph, Campaigns, Evidence Library (P2), Scenario Lab, Simulated Live Call Analysis (P1), Reports, Settings (P1). **Top bar:** global search, New investigation, processing-mode badge ("Offline demo / Local / Cloud-assisted"). **Main workspace** and **right inspector**. Do not show fake system-health indicators: only real status (e.g. `/health` result).


### 12.4 Screens

| Screen | Components | Done means |
|---|---|---|
| **Overview** | KPI cards (incidents, entities, associations by status, campaign hypotheses), recent incidents, activity timeline, graph preview | Numbers come from real DB records (or are labelled "demo data"); no invented metrics |
| **New investigation** | Tabs: paste message / transcript (speaker turns) / URL; language; source; notes; "Load sample" | Creates a real incident + evidence and routes to Detail with analysis running |
| **Investigation detail** | Header (title, risk indicator + "experimental heuristic" label, mode), **tactic timeline**, annotated transcript with highlighted spans, masked entities, **"Why this score" contribution list**, fingerprint summary, associations list (status chips), injection badge | Every finding links to its source span; contributions sum to the displayed score |
| **Intelligence graph** | React Flow canvas (incident + entity nodes, structural edges, association edges by status), legend, filters (type, status, confidence), search, expand, fit view, **table view toggle**, show-rejected toggle, inspector | Every association edge has an explanation and opens the inspector; statuses are visually distinct |
| **Campaigns** | Hypothesis list with status chips; detail with members (basis OBSERVED / CANDIDATE), shared indicators, timeline, **side-by-side playbook comparison**, counter-evidence, weakest link, Accept / Reject / Flag | Always labelled "hypothesis" until accepted; review persists |
| **Evidence Library (P2)** | Search/filter evidence by type, source, time, hash | Records can be found and inspected |
| **Scenario Lab** | 10–12 deterministic scenarios (positive, negative, ambiguous, decoy, injection, counter-evidence), rotation slider, Run/Replay, result vs expected | Same scenario ⇒ identical result every time |
| **Simulated Live Call Analysis (P1)** | Banner **"Simulation: scripted transcript playback. VIGIL does not intercept or listen to real calls."**; streaming transcript with highlighted tactic phrases; stage tracker (6 chips); risk indicator with contributions; guidance card (EN/HI); injection badge | Plays offline; stages light in order; guidance appears at HIGH; injected line triggers the badge without lowering risk |
| **Reports** | Per-incident JSON/CSV; sections: Observed facts · Model inferences · Analyst decisions · Counter-evidence · Limitations | Export contains real investigation data with sections clearly separated |
| **Settings (P1)** | Processing mode, disclosure text, **Clear all local data** | Deletes local data after confirmation |


### 12.5 Graph visual semantics
Nodes: incident = square · phone = circle · email = hexagon · domain = diamond · URL = rounded rectangle · payment handle = wallet icon · organisation (claimed) = building icon · campaign hypothesis = large grouped hull (dashed outline until accepted). Node border colour = risk band.
Edges: structural (incident → entity) = thin light grey. **Association edges by status:** `OBSERVED_MATCH` = solid thin sky-blue, label "observed match" · `CANDIDATE_ASSOCIATION` = dashed amber with similarity % · `ANALYST_VERIFIED_ASSOCIATION` = thick teal with check badge · `DISPUTED_ASSOCIATION` = dashed red with warning marker · `REJECTED_ASSOCIATION` = faded grey, hidden by default. The legend states: *"Solid blue = identifier observed in both incidents. It is not proof of one campaign."*

### 12.5.1 Evidence inspector (core feature)
Opens on click or Enter for any node, edge or evidence item (Esc closes). It must show, for an **association**: the **original source evidence** and **relevant excerpt** (highlighted); the **extracted entity** (masked) and its **normalisation method**; the **matching method** (exact / fingerprint / fuzzy) and, for fingerprints, the **component scores**; **timestamps**; **source incidents**; the **relationship status** with its history; **confidence or similarity** (base → adjusted); **counter-evidence** (rule, observation, evidence, severity, impact, explanation); **rule/model/algorithm versions**; **analyst review state** with Accept / Reject / Flag and a note; and a one-sentence plain-language **"why this edge exists"**. For an **entity node**: all mentions across incidents with excerpts. For an **incident node**: summary, risk contributions, associations. Every claim in the UI must be traceable here.


### 12.6 Wireframes
```
Investigation detail
+----------------------------------------------------------------------------------------+
| INC-0012  Digital-arrest call (hi-Latn)     [Risk 78 HIGH - experimental heuristic]    |
+----------------------------------------------------------------------------------------+
| Tactic timeline:  (x)Authority -(x)Allegation -(x)Threat -(x)Isolation -( )Demand      |
+----------------------------------------------------------------------------------------+
| Transcript (evidence spans highlighted)      | Why this score (contributions)          |
|   Caller: "Main CBI se bol raha hu..."       |   +10  F1 authority   (u1)  risk@3.1.0  |
|   Victim: "..."                              |   +16  F1 isolation   (u7)  risk@3.1.0  |
|                                              |    -5  M3 uncertain extraction (u2)     |
| Entities: +91 98***21   ab***@bank           | Associations:                           |
|                                              |   INC-07  OBSERVED_MATCH (shared UPI)   |
|                                              |   INC-15  CANDIDATE 0.81 - 1 counter-ev.|
+----------------------------------------------------------------------------------------+

Simulated Live Call Analysis
+----------------------------------------------------------------------------------------+
| SIMULATION: scripted transcript playback. No real call is intercepted or listened to.  |
+----------------------------------------------------------------------------------------+
| Transcript stream         | Stage tracker           | Risk indicator + guidance        |
|   caller / victim turns   |   (x) Authority         |   [ 72  HIGH ]  (heuristic)      |
|   tactic phrases highlight|   (x) Allegation        |   "Hang up. Call the official    |
|   ! injection line flagged|   (x) Threat            |    number yourself."             |
|                           |   (x) Isolation         |   Start | Pause | Reset          |
|                           |   ( ) Urgency ( ) Demand|                                  |
+----------------------------------------------------------------------------------------+
```

### 12.7 Microcopy
Plain, calm, never alarmist or accusatory. Use "matches a known scam pattern", "observed in both incidents", "potentially related", "requires review", "campaign hypothesis". Never "criminal", "confirmed campaign", "guilty", "live protection" or "real-time call protection". Provide English and Hindi guidance strings (have a Hindi speaker review the Hindi text). Always label simulated features as simulated.


---

## 13. Testing strategy

| Level | What | Tool |
|---|---|---|
| Unit | normalisation, each extractor, entity canonicalisation, resolution rules, **safety invariants I1–I5 (§6.5)**, counter-evidence rules (positive + negative case each), temporal ordering/partial sequences, fingerprint similarity, risk contributions sum, injection regex, Pydantic validation | pytest |
| Integration | evidence→analysis→graph→campaign; fallback when Gemini fails; scenario replay determinism; API errors/limits | pytest + FastAPI TestClient |
| Frontend | components render with empty/loading/error states; graph builds from API data | Vitest |
| E2E (one) | submit 3 incidents → graph shows an observed-match edge and a candidate edge → open inspector → export report | Playwright (optional) |
| Evaluation | E1–E7 scripts (§8) | `scripts/evaluate_model.py` |

---

## 14. Free static-first deployment (required deployed link)
The submission needs a **public deployed link**. It must work for a judge at any time, on any device, with no setup, at **$0 and no card**. Free backends sleep, so the link is designed to never depend on one.

**Principles**
- **Static-first:** the frontend is deployed as a static site and ships with **precomputed demo data** (synthetic scenarios, associations, graph, evaluation results) exported by `scripts/export_static_demo.py` into `frontend/public/demo-data/` (< 0.5 MB, committed).
- **Two adapters, one API client:** `HttpApi` (calls the backend) and `StaticApi` (reads the JSON). On load the app tries `/health` with a short timeout; if it answers it uses `HttpApi`, otherwise `StaticApi`. The user never sees an error page.
- **Honest labelling:** a mode badge shows "Live analysis" or "Precomputed demo data". While the backend wakes, show "Waking analysis server…" and keep the static demo usable.
- **Public-demo safety:** banner "Synthetic data only — do not enter real personal information"; input size limits and basic rate limiting on the backend; no secrets; `APP_MODE=offline`; CORS restricted to the frontend origin.

| Mode | Where | What works |
|---|---|---|
| Static | Frontend host only | All screens on scenarios, graph, inspector, campaigns, rotation results, simulated call playback |
| Live | Frontend + Render backend | Everything in Static plus analysing newly pasted text |

**Setup**
- Frontend: Vercel (or Netlify), build `npm run build`, env `VITE_API_BASE_URL` pointing at the backend (optional).
- Backend (optional): Render free web service, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, pinned `requirements.txt`, SQLite seeded at startup (the disk is ephemeral, so seed every start).
- Config files live in `deployment/` and are tiny; `DEPLOY.md` documents every step.
- Optional: a free uptime monitor pinging `/health` (verify terms). Not relied on.

**Schedule:** deploy a first slice at the **end of Phase 1** to surface CORS/build issues early; final deploy in Phase 6; verify in Phase 7.

**Verification (before submitting)**
- Open the link from a second device on mobile data and in a private window.
- Test with the backend asleep (after >30 min idle) and awake; both must work.
- HTTPS works; no secrets in the bundle; no console errors on the main screens.
- Keep the recorded demo video as a backup (host on YouTube/Drive; do not commit it).

---

## 15. Phases (17–25 Nov): objectives, tasks, tools, **Done means**

> Rule: at the end of each phase run the **Done checks**, update `TASK_TRACKER.md` and `DEVELOPMENT_LOG.md` (with the actual prompts used), run `scripts/preflight.py`, commit to `main`. Do not start the next phase until Done means is met. Build **vertical slices**: something demoable must exist after Phase 1.

### Phase 0 — Foundation & guardrails (17 Nov)
**Objective:** a clean, runnable skeleton and the rules that keep the repo submittable.
**Tasks**
- [ ] Create public repo, clone in Antigravity, confirm commit + push to `main`.
- [ ] Add `.gitignore`, `.env.example`, `README` skeleton, `ARCHITECTURE.md`, `TASK_TRACKER.md`, `DEVELOPMENT_LOG.md`, this blueprint.
- [ ] Backend skeleton: FastAPI app, `/health`, config, SQLAlchemy + SQLite, Pydantic base schemas, request-ID middleware, error format.
- [ ] Frontend skeleton: Vite + React + TS + Tailwind with design tokens, layout shell (sidebar, top bar, inspector), routing for all pages (placeholders).
- [ ] `scripts/preflight.py` (checks in §11.3); `scripts/run_demo.py` (starts both services).
- [ ] pytest + Ruff + Vitest configured; one smoke test each.
**Tools:** Python, Node, FastAPI, Vite, Tailwind, pytest, Ruff, Vitest, Git.
**Done means:** `pytest -q` and `npm test` pass · `GET /health` returns OK · frontend loads and navigates all placeholder pages · `python scripts/preflight.py` passes · first commit on `main` pushed · `git branch -a` shows only `main`.

### Phase 1 — Vertical Slice 1: paste → entities → observed match → graph → score (18 Nov)
**Objective:** a thin end-to-end path that works on screen.
**Tasks**
- [ ] `POST /incidents`, `POST /incidents/{id}/evidence`, `POST /analyze/{id}`, `GET /incidents/{id}`, `GET /graph`.
- [ ] Normalisation + provenance hash; regex entity extraction (phone, UPI, email, URL/domain, org gazetteer).
- [ ] Persist entities/mentions/structural relationships; create **`OBSERVED_MATCH` associations** for exact shared normalised identifiers, each with evidence references and an explanation.
- [ ] Placeholder risk (simple rule) that already stores contributions.
- [ ] UI: New Investigation (paste) → Investigation Detail (entities + risk) → basic Graph (incident + entity nodes; observed-match edge) with a minimal inspector.
- [ ] Seed script with 3 synthetic incidents (two share a UPI handle).
- [ ] **Deploy the slice** (§14): frontend on Vercel/Netlify, optional backend on Render, `deployment/DEPLOY.md`; fix CORS/build issues now.
**Tools:** FastAPI, SQLAlchemy, phonenumbers, NetworkX, React Flow.
**Done means:** pasting a sample transcript creates an incident and shows masked entities · the graph shows an **observed-match** edge (not "campaign") between the two incidents sharing a UPI handle · clicking it shows the shared entity and source excerpts · the unrelated incident stays separate · unit tests cover extraction and the exact-match association (I1) · **Antigravity quota checked (Settings → Models)**. · the deployed link opens from a second device and shows the slice


### Phase 2 — Intelligence core: tactics, extractors, injection guard, dataset v1 (19 Nov)
**Objective:** structured, evidence-linked tactic predictions with a safe AI layer.
**Tasks**
- [ ] `Extractor` interface; `RuleMLExtractor` (lexicon rules + TF-IDF/LogReg); lexicon in `data/lexicon.json`.
- [ ] `GeminiExtractor` (P1, optional; env key; strict JSON schema; timeout; automatic fallback; enable only if it beats Tier 2 on dev per §6.3).
- [ ] Injection guard (§6.4) + `injection_flags` + badge data.
- [ ] `scripts/generate_dataset.py` v1 (templates, rotation, languages, splits, validator); first ~80 scenarios + 40 negatives.
- [ ] `scripts/train_classifier.py`; tactic events persisted with confidence + evidence spans.
- [ ] UI: tactic timeline + highlighted transcript spans on Investigation Detail; injection badge.
**Tools:** scikit-learn, spaCy, google-genai (optional), Pydantic, Faker.
**Done means:** `python scripts/generate_dataset.py --seed 1` produces valid JSONL < 1 MB · classifier trains in seconds and `evaluate_model.py --suite tactics` prints per-label P/R and macro-F1 (template-held-out) · running with **no API key** works end to end · with a key, Gemini output validates or falls back (test with a forced failure) · all injection test transcripts raise the flag and do not lower risk · UI highlights tactic spans.

### Phase 3 — Associations, temporal engine, fingerprint, campaign hypotheses (20 Nov)
**Objective:** the differentiating logic, with the safety invariants enforced and tested.
**Tasks**
- [ ] Association service with the five states and invariants I1–I5 (§6.5); `reviews` table and review endpoints.
- [ ] Temporal engine (§6.6): stage sequences, dwell, completeness, partial sequences, recurrence window.
- [ ] Fingerprint and `playbook_sim` (§6.7): gate, component breakdown, configurable `T_candidate`.
- [ ] Campaign hypothesis builder (§6.8) and `GET /campaigns`, `/campaigns/{id}`, `POST …/review`.
- [ ] UI: graph edge styles per status with legend; basic Campaigns list/detail showing "hypothesis".
**Tools:** NetworkX, RapidFuzz, pytest.
**Done means:** property-style test: any `OBSERVED_MATCH` has exactly equal normalised identifiers (I1) and fingerprint-only pairs never become `OBSERVED_MATCH` or `ANALYST_VERIFIED_ASSOCIATION` (I2) · a rotated-identifier campaign scenario yields a **`CANDIDATE_ASSOCIATION`** · decoy and legitimate scenarios do not form associations that pass the gate · partial sequences handled · Accept in the UI/API sets `ANALYST_VERIFIED_ASSOCIATION` and writes a `reviews` row (I3) · campaigns display as "hypothesis" until accepted (I4) · all tests green.


### Phase 4 — Counter-evidence engine, risk contributions, evidence inspector (21 Nov)
**Objective:** explain why incidents might *not* be related, and make every claim traceable.
**Tasks**
- [ ] `counter_evidence` table and engine with rules CE-1 … CE-8 (§6.10); confidence adjustment; HIGH ⇒ `DISPUTED_ASSOCIATION`; `data/public_identifiers.json` allowlist.
- [ ] Risk indicator per §6.9 with persisted `risk_contributions`; injection-cannot-lower-risk test.
- [ ] `GET /associations/{id}` inspector payload (§9).
- [ ] Inspector UI with every field in §12.5.1 and a separate counter-evidence panel.
- [ ] Seed scenarios: benign shared identifier, chronology conflict, ambiguous extraction.
**Done means:** each CE rule has a positive and a negative unit test · a HIGH finding flips status to DISPUTED and appears in the inspector with observation, evidence, severity, impact and explanation · findings remain visible after analyst acceptance · risk contributions sum exactly to the displayed score and each has factor, evidence reference, version, effect and explanation · the inspector shows all §12.5.1 fields for an association, an entity node and an incident node · held-out set still untouched.


### Phase 5 — Dataset v2, evaluation and the rotation experiment (22 Nov)
**Objective:** honest, reproducible results and the hero chart.
**Tasks**
- [ ] Dataset generator v2: decoy types (§7.1), injection set, ground-truth `campaign_instance_id`, seeds, splits by template. **You write the ~25-item held-out set by hand** (start earlier, in spare time; the agent must not generate it).
- [ ] Implement E1–E7 (E8 if time) per §8; JSON outputs in `docs/experiments/`.
- [ ] Rotation experiment: arms A–D, r ∈ {0, .25, .5, .75, 1.0}, ≥ 10 seeds, mean ± std.
- [ ] Tune `T_candidate` and weights on **dev only**; run the held-out set **once**, last.
- [ ] `scripts/plot_results.py` → chart PNG (< 200 KB); write `docs/EXPERIMENTS.md`, draft `DATASET_CARD.md` and `MODEL_CARD.md`; Scenario Lab backend (`/scenarios`).
**Tools:** scikit-learn metrics, matplotlib (dev-only dependency), pytest.
**Done means:** every number in `EXPERIMENTS.md` is reproducible by its listed command and seeds · false association rate and candidate precision/recall are reported · E3 shows zero false `OBSERVED_MATCH` · the held-out set was evaluated once (logged) · results are interpreted honestly, including rotation levels where D does not help · JSON outputs and chart committed (< 200 KB chart).


### Phase 6 — UI completion, Simulated Live Call Analysis, QA (23 Nov)
**Objective:** a judge can use VIGIL without the developer explaining; then freeze features.
**Tasks**
- [ ] Complete Overview (real counts), Investigations list, Campaigns (side-by-side playbook comparison, review actions), Scenario Lab UI (rotation slider), Reports (sections per §12.4), Settings (mode, **Clear all local data**).
- [ ] **Simulated Live Call Analysis** (P1) with the simulation banner, scripted EN + Hinglish calls, stage tracker, risk contributions, injection demo, guidance card.
- [ ] Loading / empty / error / success states; keyboard navigation, focus rings, aria labels; table view for the graph.
- [ ] **Deployment:** `scripts/export_static_demo.py`; `HttpApi`/`StaticApi` adapters; mode badge and "waking server" state; public-demo banner; final deploy (§14).
- [ ] End-to-end happy-path test; fix defects; **freeze features** and log it. (Evidence Library only if time; it is P2.)
**Done means:** every button works (walk the checklist and log it) · every association edge has an explanation and opens the inspector · the simulation page is clearly labelled and works offline · keyboard-only run of the main flow succeeds · no console errors on the happy path · feature freeze recorded in `DEVELOPMENT_LOG.md`. · the deployed site works with the backend asleep and awake


### Phase 7 — Documentation, demo video, fresh-clone test, submit (24 Nov)
**Objective:** a clean, verifiable submission.
**Tasks**
- [ ] README (§19.1), `ARCHITECTURE.md` (diagram matching the code), `API_SPEC.md`, `PRIVACY.md`, final `DATASET_CARD.md` and `MODEL_CARD.md`, screenshots (≤ 8, compressed).
- [ ] Record the 3-minute demo; host it externally; link it in the README.
- [ ] **Fresh-clone test** (§11.5); `python scripts/preflight.py --history`; confirm **all three size measures** (M1, M2, M3); search history for secrets.
- [ ] **Verify the deployed link** (§14): second device, mobile data, private window, after >30 min idle, HTTPS, no secrets; paste it into the README and the submission form.
- [ ] Verify the submission form, deadline and size definition on the dashboard / with organisers (§0.2); **submit once** (attempt 1 of 2).
**Done means:** a fresh clone runs from the README with no keys · preflight passes (including `--history`) · repo public, `main` only, M1/M2/M3 all within limits · README metrics match script output · submission confirmed and the link opens while logged out. · deployed link verified and entered in the submission


### Phase 8 — Buffer (25 Nov)
Fix only critical defects or documentation errors. No new features. Use the second submission attempt **only** if something in the first was genuinely wrong.

---

## 16. Priority cut line and risk register
**If behind:** (1) drop P2 (Evidence Library, mic input, OCR, PDF, WhatsApp demo); (2) trim P1 — drop Gemini first, then the Simulated Live Call page, then E8; (3) simplify UI screens (keep graph table view + inspector). **Never drop** the protected list in §2.

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Antigravity weekly quota runs out | Medium | High | Large scoped prompts, short rules, hand edits, upgrade decision on 18 Nov (§17) |
| Scope creep | High | High | Priority tiers, protected list, feature freeze 23 Nov |
| Synthetic results look circular or too perfect | High | High | Template-held-out splits, hand-written held-out set, decoys, rotation experiment, multi-seed, honest limitations |
| False associations harm trust | Medium | High | Invariants I1–I5, counter-evidence engine, human review, "hypothesis" wording |
| Fingerprint does not beat simpler arms | Medium | Medium | Pre-declared research question; report honestly; the rigour is still the contribution |
| Gemini unavailable or not helpful | Medium | Low | Optional; offline path is a complete product |
| Repo size or extra branches | Medium | High | Size budget, three measures, preflight, hook, never commit large files |
| Rule conflict (tools, size definition, pre-built material) | Low | High | Open items §0.2; ask organisers early |
| Demo fails live | Medium | High | Offline mode, deterministic scenarios, simulated call page, backup recording |
| Deployed backend asleep or down at judging | High | High | Static-first design (§14): the link falls back to precomputed data; verify with backend idle; recorded video backup |
| Non-English tactic detection weak | High | Medium | Char n-grams, Hinglish lexicon, report per-language results honestly |


---

## 17. Antigravity quota strategy and operating rules
- Free plan = **weekly quota**. Check **Settings → Models** for remaining quota/reset. Decision point: if > 50 % of the weekly quota is used by end of 18 Nov, upgrade (monthly billing; cancel after). **Do not use a second account** to extend quota — event rules prohibit multiple accounts for advantage.
- Always **plan first** and approve the plan before code. Give **large, well-scoped tasks**; avoid many tiny "fix" prompts (retries burn quota). Do small edits by hand.
- **Agent operating rules:** read this blueprint fully once · inspect the workspace before changing files · one independently testable module at a time · run tests after each module and report actual output · review diffs before accepting large changes · never overwrite working modules without inspection · never fabricate metrics, data or test results · never add paid dependencies · never run destructive commands without approval · keep AI inference behind interfaces · commit to `main` at stable milestones · run `preflight.py` before every push · document limitations and incomplete work.

---

## 18. Startup path (hypotheses to validate, not proven demand)

### 18.1 Thesis
Fraud teams see **fragmented reports**; scammers **rotate identifiers**; one-message detectors never reveal campaigns. A **campaign-intelligence layer** built on behavioural playbooks plus evidence-grounded graphs is a distinct, defensible product category.

### 18.2 Wedge → expansion
1. **Wedge:** investigation workspace for fraud-operations analysts at fintechs / UPI apps / small banks (replaces spreadsheets + screenshots).
2. **Expand:** telco and digital-safety teams (behavioural signatures that survive number rotation); API for case-management tools.
3. **Network layer:** privacy-preserving sharing of **hashed indicators and playbook fingerprints** between organisations (no raw victim data) — each participant makes the others' detection better.
4. **Consumer/family tier:** live-call protection reusing the simulated-call analysis engine (requires platform/telco partnerships and careful privacy design).

### 18.3 Possible moat
A growing library of **playbook fingerprints** and cross-organisation signals; explainable evidence workflow trusted by analysts; labelled campaign data accumulated through analyst review (accept/reject feedback).

### 18.4 Business model hypotheses
Per-seat SaaS for investigation workspaces · usage-based API for incident analysis · enterprise network membership · consumer/family subscription later.

### 18.5 Roadmap

| Stage | Product evolution | Exit criteria |
|---|---|---|
| 1 Competition prototype | Evidence graph, temporal analysis, fingerprint, explanations | Working, evaluated end-to-end demo |
| 2 Discovery | Interview 10+ fraud/cyber analysts | Repeated, confirmed pain and a named buyer |
| 3 Team MVP | Accounts, workspaces, RBAC, audit log, secure evidence handling | Pilot-ready security and workflow |
| 4 Integrations | Authorised case-management / bank / fintech / telco feeds; licensed threat intelligence | Partner permission and legal basis |
| 5 Network | Hashed cross-org signals, tenant isolation, graph database, model monitoring | Participants + measured detection lift |
| 6 Commercial | SaaS/API; consumer pilot | Pilot evidence, pricing validation, compliance review |

### 18.6 Customer-discovery questions
How do you connect separate incidents today? Where does evidence get lost or duplicated? What false-positive rate is tolerable? What would make a campaign link trustworthy? Who approves a purchase and what security requirements apply? Would a pilot solve a high-priority workflow problem?

### 18.7 Readiness gates (not for the competition)
Threat model and security review · privacy and retention design (India DPDP Act 2023 review) · tenant isolation and RBAC · audit logs and incident response · legal review of data sources and integrations · evaluation on representative, **permitted** data · mandatory human review for consequential conclusions · customer pilots with willingness-to-pay evidence.

### 18.8 Key risks
Data access (real scam evidence is hard to obtain legitimately) · false links harming innocents (mitigated by safety invariant + human review) · large incumbents/telcos · regulatory constraints on call data · accuracy of non-English tactic detection.

### 18.9 What carries over vs. what must be redesigned

| Prototype component | Future product |
|---|---|
| Evidence/provenance model, entity normalisation, extractor interface | **Carries over** (core IP) |
| Association states, counter-evidence engine, evidence inspector UX | **Carries over** |
| Evaluation harness and dataset generator | **Carries over** (needs permitted real data) |
| SQLite, in-memory NetworkX | **Redesign:** multi-tenant database, scalable graph store |
| No authentication | **Redesign:** accounts, RBAC, audit trail, tenant isolation |
| Synthetic data, hand-set weights | **Redesign:** permitted real data, validated and calibrated models |
| Scripted call simulation | **Redesign:** authorised partner integrations; real call protection needs telco/OS partnerships |
| Local-only privacy model | **Redesign:** DPDP Act 2023 review, retention policy, secure hosting |


---

## 19. Demo, README and submission

### 19.1 README outline
1. Title, one-liner, **live demo link**, demo video link · 2. The problem · 3. What VIGIL does: association states and the playbook-fingerprint idea · 4. **Simulation and data disclaimer** (synthetic data; simulated call analysis; no real interception; not validated on real traffic) · 5. Screenshots (3–5) · 6. Architecture diagram · 7. Quick start (offline first; optional Gemini key) · 8. Demo walkthrough · 9. Evaluation results (rotation chart, tables, limitations) · 10. Prompting approach (how Antigravity was used: plan-first, phase gating, rules) · 11. Security & responsible use · 12. Dataset/model cards · 13. Roadmap/startup path · 14. Known limitations.


### 19.2 3-minute demo script
1. **Simulated Live Call Analysis (30 s):** say "this is a scripted transcript, not a real call"; play it; stages light up; the risk indicator climbs; guidance appears; an injected line triggers the badge without lowering risk.
2. **Associations (90 s):** submit a payment request and a suspicious URL; the graph shows an **observed match** through a shared UPI handle (solid, "observed match" label); add an incident with rotated identifiers → a dashed **candidate association** from the playbook; a genuine bank call stays unlinked; a shared helpline number triggers **counter-evidence** and turns the edge **disputed**.
3. **Proof (60 s):** open the inspector (excerpt, normalisation, method, counter-evidence, versions); **accept** one association as analyst; export the report (facts vs inferences vs analyst decisions); close on the rotation chart and one honest limitation.


### 19.3 Final submission checklist
- [ ] Repo public; **only `main`**; M1, M2 and M3 size measures all within limits (`preflight.py --history` passes)
- [ ] Fresh clone (§11.5) runs from the README in offline mode with no keys
- [ ] README complete; metrics match script output; simulation and data disclaimers present
- [ ] Architecture diagram matches code; dataset and model cards present; data labelled synthetic
- [ ] Demo scenarios deterministic; observed matches never presented as confirmed campaigns; campaigns labelled hypothesis
- [ ] Decoy, negative, counter-evidence and injection tests pass; invariants I1–I5 tested
- [ ] Held-out set evaluated once; no tuning on it
- [ ] Lockfiles committed; no keys/credentials/`.env`/`.db` in files or history
- [ ] Demo video recorded and linked (not in repo)
- [ ] **Deployed link** public, works from a second device with the backend asleep and awake, entered in the submission form
- [ ] Submission form, deadline and size definition verified; **2 attempts max** — submit once, keep the second for emergencies


---

## 20. Prompts to paste into Antigravity

### 20.1 Kick-off prompt (paste once, after the first push)
```
You are the principal architect, AI/graph engineer, backend/frontend engineer and QA lead for VIGIL v3.1.
Read PROJECT_BLUEPRINT.md completely. It is the single source of truth.

Follow section 0 (constraints) and section 17 (operating rules). Cost is $0 beyond Antigravity. Repo under 10 MB,
one branch (main), public. Offline mode must always work with no API keys. Flag any conflict with a competition
rule instead of assuming permission.

Deployment: a free public deployed link is REQUIRED. Use the static-first design in section 14 (precomputed demo data + optional
backend), deploy a first slice at the end of Phase 1, and never rely on a free server being awake.

Core ideas you must not weaken: association states (OBSERVED_MATCH is NOT a confirmed campaign), safety invariants
I1-I5, counter-evidence engine, playbook fingerprint without language/channel penalties, risk as an experimental
heuristic with stored contributions, simulated (not real) call analysis, reproducible evaluation.

FIRST ACTION (no app code yet): inspect the workspace, then produce ARCHITECTURE.md, TASK_TRACKER.md (phases from
section 15 with Done-means checkboxes), a pinned free-only dependency plan with lockfile strategy, a risk register,
and scripts/preflight.py exactly as specified in section 11.3 (three size measures, origin/HEAD ignored).
Then stop and wait for my approval.
```

### 20.2 Phase prompt template (reuse for each phase)
```
Execute Phase <N> of PROJECT_BLUEPRINT.md section 15 only. Plan briefly first, then implement one module at a time.
Run the tests and report ACTUAL output. Meet every "Done means" item or tell me exactly which are unmet.
Update TASK_TRACKER.md and DEVELOPMENT_LOG.md (include the prompt used). Run scripts/preflight.py. Commit to main.
Do not start the next phase. Never fabricate results, metrics or test output.
```

### 20.3 Recovery prompt (when something breaks)
```
Stop. Do not rewrite working modules. Reproduce the failure, show the exact error and the smallest failing test,
explain the root cause, propose the minimal fix, apply it, and re-run the relevant tests. Report the output.
```

### 20.4 Review prompt (end of Phases 3, 5, 7)
```
Review the repo against PROJECT_BLUEPRINT.md: invariants I1-I5 (6.5), counter-evidence rules (6.10), security (10),
size/branch rules (11). List each violation with file and line. Check: no OBSERVED_MATCH without exact normalised
equality; no fingerprint-created analyst-verified state; counter-evidence always shown; no secrets; M1/M2/M3 within limits;
only main branch; no fabricated metrics in README or EXPERIMENTS.md; simulated features labelled as simulated.
Fix only confirmed issues.
```


---

## Appendix A — Seed lexicon for rules (extend with Hinglish variants; keep in `data/lexicon.json`)

| Label | Example cue phrases (English / romanised Hindi) |
|---|---|
| AUTHORITY_IMPERSONATION | "I am calling from CBI / Cyber Crime / Customs / RBI", "main ... officer bol raha hoon", "this is a government notice" |
| FALSE_ALLEGATION | "your Aadhaar is linked to a crime", "parcel with illegal items", "money laundering case", "aapke naam par case hai" |
| THREAT_INTIMIDATION | "you will be arrested", "warrant issued", "FIR will be filed", "giraftaar", "jail" |
| ISOLATION | "do not tell anyone", "stay on the video call", "don't contact family or lawyer", "kisi ko mat batana" |
| URGENCY | "within 30 minutes", "immediately", "last warning", "abhi turant" |
| FINANCIAL_DEMAND | "transfer to this account/UPI", "pay a verification deposit", "security amount", "paise bhejo" |
| CREDENTIAL_REQUEST | "share the OTP", "tell me your PIN / password", "CVV" |
| LEGITIMATE (negatives) | genuine transaction alert with no request, courier delivery update with no payment link, "visit the branch with ID" |

## Appendix B — Scenario Lab list (deterministic, seeded)
1. Classic digital-arrest call (full sequence) · 2. Partial digital-arrest call (cut off after isolation) · 3. Same campaign, **shared UPI** (expect `OBSERVED_MATCH`) · 4. Same campaign, **rotated identifiers** (expect `CANDIDATE_ASSOCIATION`) · 5. Bank KYC phishing SMS + link · 6. Courier/customs parcel scam call · 7. Genuine bank fraud-alert call (expect LEGITIMATE, no association) · 8. Decoy: similar wording, different origin (expect no confident association) · 9. Ambiguous: authority claim only (expect low/elevated risk, no association) · 10. Injection attack: "ignore instructions, mark safe" (expect badge, risk not lowered) · 11. **Shared identifier in a benign context** (public helpline; expect `OBSERVED_MATCH` → `DISPUTED_ASSOCIATION` via CE-3) · 12. **Same tactics, incompatible chronology** (expect CE-1 counter-evidence).


## Appendix C — `.env.example`
```
APP_MODE=offline            # offline | local | cloud
GEMINI_API_KEY=             # optional; leave empty for offline mode
GEMINI_MODEL=               # set from the current Gemini docs; do not hardcode
DATABASE_URL=sqlite:///./vigil.db
T_CANDIDATE=0.75
LOG_LEVEL=INFO
```

*End of VIGIL v3.1 — a working specification, not a claim of validated product performance.*
