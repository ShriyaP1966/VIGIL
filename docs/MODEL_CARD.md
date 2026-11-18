# Model card: VIGIL v3.1 analysis pipeline

VIGIL is a cross-channel scam **intelligence** tool for analysts and researchers. It organises evidence, shows
why two incidents may be related, and shows what argues against it. It does not decide anything. All data used
to build and evaluate it is synthetic. It is **not** real-time call protection, it does not listen to or
intercept calls, and nothing in it is a verdict about a person or organisation.

## What is in the pipeline

There is **no trained machine-learning model** in the shipped pipeline. Every stage is rule-based, written by
hand, versioned and inspectable; the app runs fully offline with no API key.

| Stage | Method | Version / file |
|---|---|---|
| Redaction | pattern rules remove OTPs, passwords, PINs, card numbers, CVVs, Aadhaar numbers before anything is stored | `ai_engine/privacy/redaction.py` |
| Normalisation, entities | NFKC, zero-width removal, regex and `phonenumbers` for phones, UPI handles, domains, URLs, emails | `ai_engine/extraction/` |
| Injection guard | phrase rules flag text that tries to instruct the analyser; flagged spans are masked and no risk mitigation is applied | `ai_engine/guard/injection.py` |
| Tactic extraction | hand-written lexicon of regexes (English, romanised Hindi, a few Devanagari and Marathi patterns) over eight labels | `data/lexicon.json`, `lexicon@1.0` |
| Risk | stage-based heuristic with a ledger whose contributions sum exactly to the shown score | `risk@3.1.1` |
| Exact matches | `OBSERVED_MATCH` only when two incidents share an exactly equal normalised identifier (invariant I1) | `backend/app/services/association_service.py` |
| Playbook fingerprint | order of the scam stages (longest common subsequence, order consistency) plus claimed institution and payment channel; **a-priori weights, not learned**; creates `CANDIDATE_ASSOCIATION` only, threshold `T_candidate = 0.75` (never tuned on results) | `fingerprint@3.1.0` |
| Counter-evidence | rules CE-1 chronology, CE-2 payment destination, CE-3 benign public identifier, CE-4 weak extraction (minimal), CE-5 impersonation, CE-7 language difference; CE-6 and CE-8 are not implemented; a HIGH finding disputes a link | `config/counter_evidence_rules.json` |
| Campaign hypotheses | each connected group of two or more incidents joined by non-disputed links (observed, analyst-verified, or behaviour-only candidates) is one hypothesis, always shown as a hypothesis until an analyst accepts it; with many candidate links a hypothesis can become a large group | `campaign@3.1.0` |

The playbook fingerprint recognises a **script family / playbook**. It never identifies a specific group, person
or organisation, and the UI and reports never say "confirmed campaign".

## Safety invariants (unit-tested)

I1 `OBSERVED_MATCH` only for exactly equal normalised identifiers. I2 no fingerprint or ML output can create an
`OBSERVED_MATCH` or an analyst-verified link. I3 an analyst-verified link needs a recorded review. I4 a campaign is a
hypothesis until an analyst accepts it. I5 every link carries evidence references and a plain-language explanation,
and counter-evidence is stored and shown next to it.

## Intended use and out of scope

Intended: exploring synthetic or properly consented, sanitised evidence; teaching how identifier rotation defeats
identifier-only linking; demonstrating an auditable, human-in-the-loop design.
Out of scope: real-time call protection or blocking; deciding guilt, attributing to a group or person; processing
real victims' data; any use that treats a risk score as a probability.

## Evaluation (all from scripts; see `docs/EXPERIMENTS.md` and `docs/experiments/*.json`)

* **E1 tactics** (rule extractor, macro-F1 over labels with support): train 0.9707, dev 0.9908, test 0.9716 on the
  v2 sample (`tactics_*.json`). Synthetic, same author as the rules: optimistic. The test figure is a fresh sample of the
  same templates, not an independent test. The extractor also labels most awareness notices that merely quote a
  scam (decoy D1) as scam tactics: it matches wording, not intent.
* **E5 injection:** 10 of 10 authored attack transcripts neutralised. Written by the same author as the guard; it
  shows the guard recognises these phrasings, nothing about novel or obfuscated attacks.
* **E3, E4** (association integrity and the rotation experiment): `docs/EXPERIMENTS.md`, pre-registered in
  `docs/PREREGISTRATION.md`.
* **E6** held-out set (25 scenarios, drafted by a different language model, not Claude, then reviewed, edited and
  labelled by the owner, Shriya Patil): evaluated once at the end; not yet run. It has no per-utterance tactic labels,
  so **tactic-level scores are not measured on it**; only scenario-level scam detection and the false-alarm rate on the
  legitimate scenarios will be reported.

## Known weaknesses

* The lexicon is keyword-level. "tonight" alone can read as urgency; quoted or reported scam wording can look
  like the scam. There is no semantic model of intent.
* The fingerprint cannot tell two instances of one script apart (they have the same stage order by construction),
  so under an instance-level definition its precision is low. It is a lead generator, not evidence of one actor.
* Identifier matching is exact. It will not link a number written with different digits, spoken in words, or
  replaced, which is what the rotation experiment measures.
* Risk is an experimental heuristic with a-priori weights, uncalibrated, not a probability.
* Dwell-time similarity, CE-6, CE-8 and fuzzy identifier candidates are not implemented.
* Languages: English and romanised Hindi are covered; Devanagari Hindi and Marathi only by a few patterns.

## Ethical notes

Untrusted text is never rendered as HTML and URLs are never fetched. Secrets are redacted before storage and the
redaction is recorded. The tool is built so that a human accepts or rejects each link, and counter-evidence is
shown next to the supporting evidence rather than hidden.
