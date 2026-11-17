# Hand-written held-out set (E6)

**Written by the project owner, by hand.** It is not generated, not written by an AI assistant, and not used
for training, lexicon building, threshold choice or tuning. It is evaluated **once**, at the very end, with
`python scripts/evaluate_model.py --suite heldout`. Until the owner says it is ready, nothing in this repository
reads or edits `heldout.jsonl`, and the file below is intentionally empty.

Target size: about 25 scenarios. All content must be **synthetic**: invented names, invented numbers, no real
person, organisation or identifier (use the example ranges below).

## File

`data/heldout/heldout.jsonl`: one JSON object per line (UTF-8). Lines that are blank or start with `#` are
ignored. The file is currently empty.

## One scenario (one line)

```json
{
  "id": "H01",
  "source_channel": "call",
  "language": "en",
  "is_legitimate": false,
  "utterances": [
    {"speaker": "caller", "text": "…", "tactic_labels": ["AUTHORITY_IMPERSONATION"]},
    {"speaker": "victim", "text": "…", "tactic_labels": []}
  ],
  "notes": "optional free text for you, never used by the evaluation"
}
```

| field | type | rule |
|---|---|---|
| `id` | string | unique, e.g. `H01` … `H25` |
| `source_channel` | string | `call`, `sms`, `email` or `web` |
| `language` | string | `en`, `hi-Latn` (romanised Hindi), `hi` (Devanagari), `mr` (Marathi) or `mixed` |
| `is_legitimate` | boolean | `true` for a genuine bank alert, real police verification, family call and so on; `false` for a scam |
| `utterances` | list | in order; each has `speaker` (`caller`, `victim`, `sender`), `text`, and `tactic_labels` |
| `tactic_labels` | list of strings | the gold labels **you** assign to that utterance, from the vocabulary below; `[]` if none; victim turns normally `[]`; a legitimate message normally `["LEGITIMATE"]` or `[]` |
| `notes` | string, optional | ignored |

## Tactic label vocabulary

`AUTHORITY_IMPERSONATION`, `FALSE_ALLEGATION`, `THREAT_INTIMIDATION`, `ISOLATION`, `URGENCY`,
`FINANCIAL_DEMAND`, `CREDENTIAL_REQUEST`, `LEGITIMATE` (the authoritative list is `TACTIC_LABELS` in
`ai_engine/extraction/tactics.py`).

## Synthetic identifiers only

Phones in the example range `+91 98765 xxxxx`, domains ending in `.example`, invented UPI handles. Do not
include real OTPs, card numbers, Aadhaar numbers or real contact details.

## What is measured (E6)

Tactic macro-F1 over the labels that have support, and the false-positive rate on legitimate scenarios (a
legitimate scenario counts as a false positive if the extractor labels any scam tactic in it). The harness
refuses to run on an empty file and refuses to run a second time (it writes `docs/experiments/heldout.json`
and then stops; deleting that file to re-run would defeat the point of a held-out set, so the log records it).
