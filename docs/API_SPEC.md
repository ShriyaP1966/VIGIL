# VIGIL API specification (as built)

Base path `/api/v1` (a bare `GET /health` also exists). JSON in and out unless noted. FastAPI also serves the live
OpenAPI document at `/openapi.json` and interactive docs at `/docs` when the backend runs; this file is the written
summary and matches the code at the feature freeze. **All data is synthetic.** The hosted demo has no backend: the
same responses are precomputed into `frontend/public/demo-data/` by `scripts/export_static_demo.py`.

**Conventions.** Every response carries an `X-Request-ID` header (the request's own if it sent one). Errors use one
body: `{"error": {"code", "message", "request_id"}}` with codes `BAD_REQUEST`, `NOT_FOUND`, `METHOD_NOT_ALLOWED`,
`VALIDATION_ERROR` (422), `REDACTION_FAILED` (500) or `HTTP_ERROR`. CORS allows `FRONTEND_ORIGIN` (default `*`). There is
no authentication: the app is a local, single-user analysis tool, not a multi-user service.

## Health

| Method | Path | Returns |
|---|---|---|
| GET | `/api/v1/health` (and `/health`) | `{"status": "ok", "mode": "offline", "version", "timestamp"}`. The frontend treats the backend as live only when it answers JSON with `status: "ok"`. |

## Incidents and evidence

| Method | Path | Purpose |
|---|---|---|
| POST | `/incidents` | Create an incident: `{title (1-255), source_channel: call\|sms\|email\|web, language: en\|hi\|hi-Latn\|mr\|mixed, notes?, scenario_id?, evidence?: [{type: transcript\|message\|url\|payment_request, text (1-20000), timestamp?, provenance?, speaker_turns? (max 200)}] (max 20)}`. Secrets are redacted before anything is stored. Returns the incident detail. |
| POST | `/incidents/{id}/evidence` | Attach one evidence item (same fields as above). |
| POST | `/analyze/{id}` | Run the full pipeline again for an incident: extraction, risk, observed matches, behavioural candidates, counter-evidence, campaign hypotheses. |
| GET | `/incidents?skip=0&limit=50` | Newest first (`limit` 1-100): `id, title, source_channel, language, status, risk_score, risk_band, created_at`. |
| GET | `/incidents/{id}` | Detail: evidence (original text after redaction, normalised text, `sha256`, provenance), entities with masked display values and spans, utterances with tactic spans and injection spans, analysis (extractor and versions, fingerprint, risk score and band, risk contributions, injection flags) and redaction counts. |
| GET | `/incidents/{id}/report?format=json\|csv` | Structured report (below). CSV is a download (`vigil_report_incident_<id>.csv`). |

**Report** (`report@1.0`, deterministic): `incident`; `observed_facts` (evidence hashes, masked identifiers, exact matches);
`model_inferences` (stage order, tactics with excerpts, risk with contributions and its "not a probability" note,
behaviour-only candidates, campaign hypotheses); `analyst_actions` (recorded reviews); `counter_evidence` (findings and
disputed or rejected links); `limitations`. It never contains raw evidence text or unmasked identifiers. CSV is long
format `section,record,field,value`; values that start with `= + - @` are prefixed with `'` so spreadsheets do not run them.

## Graph, associations, campaigns

| Method | Path | Purpose |
|---|---|---|
| GET | `/graph?min_confidence=0&include_rejected=false&status=` | Nodes (incidents, indicators) and edges (structural links plus associations with status). |
| GET | `/associations/{id}` | Evidence Inspector payload: status, match type, base and adjusted confidence, component scores, supporting evidence excerpts, counter-evidence findings, algorithm and rule versions, review history, a plain-language explanation. |
| POST | `/associations/{id}/review` | `{decision: ACCEPT\|REJECT\|FLAG, note?}`. The only route that can set an analyst status (invariant I3); writes a `reviews` row, then rebuilds hypotheses. |
| GET | `/campaigns` | Campaign hypotheses: title, status, confidence, member count, weakest link. |
| GET | `/campaigns/{id}` | Members (basis, risk, stage sequence, institution, payment channel), links with counter-evidence, excluded links, aggregated findings. |
| POST | `/campaigns/{id}/review` | `{decision, note?}`; a hypothesis is always a hypothesis until accepted by an analyst (I4). |

Association statuses: `OBSERVED_MATCH` (exactly equal normalised identifier), `CANDIDATE_ASSOCIATION` (similar script, no shared
identifier), `ANALYST_VERIFIED_ASSOCIATION`, `DISPUTED_ASSOCIATION`, `REJECTED_ASSOCIATION`. Safety invariants I1-I5 are enforced in
the data layer and by tests (see `ARCHITECTURE.md`).

## Scenario Lab

| Method | Path | Purpose |
|---|---|---|
| GET | `/scenarios` | The 11 deterministic scenarios: `name, title, category, description, rotation_adjustable, default_rotation`. |
| POST | `/scenarios/{name}/run` | Body `{rotation?: 0..1}` (422 outside the range; ignored and reported as `null` for scenarios that do not rotate). Replays the scenario through the real pipeline in an **isolated in-memory database** and returns incidents, links, hypotheses, a summary and `checks` (`expected`, `actual`, `passed: true\|false\|null`), plus `matches_expected`. The same name and rotation always give the same result; the application database is never touched. 404 for an unknown name. |

## Simulated Live Call Analysis

A **simulation**: scripted synthetic transcripts, text only. VIGIL does not intercept or listen to calls.

| Method | Path | Purpose |
|---|---|---|
| GET | `/simulations` | The four scripted calls with their turns. |
| POST | `/simulations/live-call/analyze` | `{utterances: [{speaker, text (1-1000)}] (1-40), language?}`. Analyses the transcript so far in an isolated database and returns one frame: `stages` (six, with the turn each first appeared), `risk` (score, band, contributions that sum to the score), `utterances` with tactic and injection spans, `injection_flags`, `guidance` (English and Hindi), `disclaimer`. Stores nothing. 422 for empty, too many or too long turns. Secrets in the text are redacted first. |

## Settings

| Method | Path | Purpose |
|---|---|---|
| DELETE | `/data?confirm=true` | Erase every incident, evidence record, identifier, association, hypothesis and review from the local database. 400 without `confirm=true`. |

## Not implemented

No evidence search, no per-association export, no cloud extractor (a `GEMINI_API_KEY` setting exists in `config.py`
but nothing reads it and no network call is made), no authentication, no rate limiting.
