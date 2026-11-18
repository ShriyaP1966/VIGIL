# Pre-registration of the Phase 5 experiments (E3, E4)

Written and committed **before any E3 or E4 experiment was run**. It fixes what is measured, how, and on
what, so that a result can not shape its own definition. Anything changed after this commit is listed in
"Amendments" at the end with the reason and the date; the original text is never edited.

All data is synthetic. Results describe behaviour on this generator's data and do not imply real-world
performance. The playbook fingerprint recognises a **script family / playbook**, never a specific group,
person or organisation.

## 1. Frozen artefacts

| Artefact | Identifier |
|---|---|
| Generator `scripts/generate_dataset.py` (`gen@2.0`) | commit `7d0929f9324a8830455e49de191769caad43709f`, sha256 (line endings normalised to LF) `bab541ce6a7a24f911a3f00a1aba5402526a0fdef1b54ba995afb0b48edebe3a` |
| Committed sample `data/scenarios.jsonl` (`--seed 1 --rotation 0.5`, 150 incidents) | sha256 (LF) `58d67bb2e15d62ad206a43553b6c65ce13092fd81c996bbc689678e089f4c82d` |
| Rule lexicon `data/lexicon.json` (`lexicon@1.0`, hand-written, not trained) | sha256 (LF) `5621851d011fce7ac8cfb6200fc306b74351eb13ffa2f02e2711c5b6e08d8149` |
| Fingerprint `ai_engine/fingerprint/similarity.py` (`fingerprint@3.1.0`) | sha256 (LF) `3def23745250c30a796b0660c601f92e019037b5930cd297abdc34b390f7edf7` |
| Counter-evidence rules `config/counter_evidence_rules.json` | sha256 (LF) `aad96090f92f02be0314be0381051232b2816aa8c0d9b7c0cf0f09a62ec3348b` |
| Public identifiers `data/public_identifiers.json` | sha256 (LF) `9586e31758131564f923434c316e56c9564849148ac861ce6a98731c0da42d61` |
| `T_candidate` | **0.75** for every headline number (the Phase 3 default, never tuned on any result) |

The generator, its templates, phrase pools, decoys and the family map are frozen. No behavioural habit,
instance-specific phrasing or stage-order quirk is added after results exist.

## 2. Data per run

One run = `generate(seed, r)` with the frozen generator: 90 campaign incidents (6 templates x 15, instances of
3), 40 legitimate negatives, 20 decoys (D1-D4, five each), 150 incidents in all. Identifiers are unique across
the dataset, so a shared identifier is always one the generator shared on purpose.

* Rotation levels **r in {0, 0.25, 0.5, 0.75, 1.0}**.
* Evaluation seeds **1001-1010** (10 seeds). Seed 900 is reserved for dev-only calibration and debugging, seed 1
  for the committed sample. No evaluation seed is used for any calibration.
* Incidents are ingested one at a time in the order (timestamp, incident id) through the real services
  (`create_incident`, `run_incident_analysis`), in an isolated in-memory database, with speaker turns, channel,
  language and timestamp from the record. No analyst review is simulated.

## 3. Ground truths (always reported side by side)

* **(a) campaign instance:** a pair is true iff both incidents share a `campaign_instance_id`.
* **(b) script family:** a pair is true iff both are campaign incidents of the same family. Family map, fixed
  on 17 Nov 2026 and defined by scam type: **digital arrest = T1, T2, T3; bank KYC = T4; payment link = T5;
  courier/customs = T6.** T4 and T5 are deliberately *not* merged, so a T4-T5 link counts as false and is
  reported as such.
* Negatives (N1-N6) and decoys (D1-D4) are non-pairs under both.

Under (a) the fingerprint is expected to have low precision, because different instances of one template run
an identical script. This is stated in every table and is not a defect to be fixed in the data.

## 4. Arms

Predicted campaigns are connected components over the listed edges of one run (singletons for incidents with
no edge). Edges are read from the associations table after the whole run.

* **A, text baseline.** Gate: the incident has at least one non-`LEGITIMATE` tactic label from the rule
  extractor (the "incident-level classification"). Gated incidents are compared by cosine similarity of
  TF-IDF vectors (scikit-learn `TfidfVectorizer`, lowercase, word 1-2-grams, `sublinear_tf=True`, fitted on
  the gated incidents of that run, text = the incident's utterance texts joined by a space). An edge exists
  when cosine >= tau_A. No entity graph, no temporal reasoning.
  *tau_A is chosen on dev only:* generate seed 900 at r = 0.5, keep the `dev` split (T2, T5, N3, N4, D2), and
  pick the tau_A in {0.10, 0.15, ..., 0.90} that maximises pairwise F1 under ground truth (a); ties go to the
  larger tau_A. The chosen value is recorded in the results JSON and fixed before any evaluation seed runs.
  This gives the baseline a tuned threshold while arm D keeps its a-priori one.
* **B, identifier graph.** Edges: exact normalised identifier equality, i.e. associations with
  `match_type` in {EXACT_IDENTIFIER, COMBINED} and status OBSERVED_MATCH **or** DISPUTED_ASSOCIATION (the
  counter-evidence engine is not applied).
* **C, B + counter-evidence.** Edges: associations with status OBSERVED_MATCH after the counter-evidence engine
  ran (rules CE-1 chronology, CE-2, CE-3 benign identifier, CE-4 minimal, CE-5, CE-7; CE-6 and CE-8 are not
  implemented, so C is not exactly the blueprint's "recurrence window" arm and is described as implemented).
  A HIGH finding moves a link to DISPUTED, which removes it.
* **D, C + playbook fingerprint.** Edges: OBSERVED_MATCH plus CANDIDATE_ASSOCIATION (fingerprint
  `playbook_sim >= 0.75` and the gate), neither DISPUTED nor REJECTED. D "observed-only" is identical to C by
  construction and is not listed separately.

B, C and D are read from the **same** pipeline run per (seed, r); a test checks that this gives the same edge
sets as running the pipeline with counter-evidence switched off (B) and with candidates switched off (C).

## 5. Metrics (per seed, then mean and sample standard deviation over the 10 seeds)

For ground truth G in {(a), (b)}, over all unordered incident pairs of the scored incident set:

* **Pairwise precision / recall / F1:** "same predicted component" against "true pair under G". Undefined
  values (no predicted pair, or no true pair) are reported as `null`, never as 0 or 1, and the mean uses the
  defined seeds only with their count shown.
* **False association rate (FAR):** share of non-pairs under G that are in the same predicted component.
* **FAR, benign:** the same share restricted to non-pairs that involve at least one negative or decoy
  (independent of G).
* **Candidate precision:** share of CANDIDATE_ASSOCIATION edges that are true pairs under G.
* **Candidate recall:** among true pairs under G that arm C does not connect, the share arm D connects.

**Scored sets:** *primary* = all 150 incidents; *secondary* = the `test`-split incidents only (T3, T6, N5, N6,
D3, D4), pairs among them, with predictions from the same full run. Both are always shown.

## 6. E3, association integrity (on `data/scenarios.jsonl`, and summed over all E4 runs)

* **I1 violations:** OBSERVED_MATCH edges that do not share an exactly equal normalised identifier. Required: **0**.
* **Observed links touching a negative or decoy**, before (arm B level) and after (arm C level) counter-evidence.
  The blueprint's goal is 0 after counter-evidence; the number is reported whatever it is.
* **Candidate links touching a negative or decoy** (arm D).
* **Legitimate-negative false-positive rate:** share of negatives with at least one OBSERVED or CANDIDATE edge.
* **Decoy outcome by type (D1-D4):** share with any edge, and the campaign hypotheses that contain a decoy
  or negative.

## 7. Other suites

* E1, E5: re-run on the frozen sample with the unchanged lexicon (decoys excluded from E1 and reported on the
  side). The E1 `test` numbers are a fresh sample of the same templates, not an independent test.
* E6 (held-out set; see amendment 2 for its provenance and scope): evaluated once at the end, never read before the owner says
  it is ready. The harness refuses to run on an empty file or to run twice.
* E8 is cut. E2 (entities) and E7 (latency) are descriptive and have no pre-registered threshold.

## 8. Reporting rules

A low result is reported as a low result. If D does not beat B or C at some rotation level, that is shown. No
metric is rounded up, re-defined, or dropped after seeing it; per-seed values are kept in `docs/experiments/`.
Standard deviations are sample standard deviations (n - 1). With 10 seeds from one generator the intervals say
how much the generator's randomness moves a number, not how the system would behave on real traffic.

## Amendments

1. **17 Nov 2026, before any E3 or E4 run (clarification, nothing was run yet).** The F1 convention is the one
   already used by `evaluate_model.prf`: F1 is `0.0` when at least one pair is predicted or true but there is no
   true positive, and `null` only when there is no predicted and no true pair. Precision is `null` when nothing
   was predicted and recall is `null` when there is no true pair (section 5 says "undefined values are null"; this
   spells out which values those are). Arm B includes `COMBINED` links (an identifier link that the fingerprint
   also matched). The harness is `scripts/evaluate_model.py` with `scripts/eval_metrics.py` and
   `backend/app/services/replay_service.py`; the arm definitions in section 4 are implemented exactly as written
   and `backend/tests/test_eval_experiments.py` checks them (including B and C read from one run versus separate
   ablated runs).

2. **18 Nov 2026, before the held-out set was evaluated (E6 provenance and scope).** The held-out set was drafted by a
   different language model (not Claude), then reviewed, edited and labelled by the owner, Shriya Patil; section 7's
   "written by the project owner" is superseded by this. The owner's file has no per-utterance tactic labels, so E6
   reports **scenario-level scam detection and the false-alarm rate on the legitimate scenarios only**; tactic-level
   scores are **not measured** on it. The harness was changed accordingly before any E6 run (the run-once guard is
   unchanged). Nothing in the generator, lexicon, fingerprint, counter-evidence rules or any threshold changed, and the
   set's content was not used to change any of them.
