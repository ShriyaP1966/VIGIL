# Dataset card: VIGIL synthetic scenarios (`gen@2.0`)

**Everything here is synthetic.** No real call, message, person, organisation, phone number, account or
identifier is used. Phones sit in the example range `+91 98765 xxxxx`, domains end in the reserved `.example`
TLD, UPI handles are invented, and every text passes through the secret redactor, so no OTP, card or Aadhaar-like
value can be present. The validator in `scripts/generate_dataset.py` re-checks all of this on every run.

## What it is for

Measuring whether VIGIL's pipeline links incidents that belong together and leaves unrelated ones alone, and how
that changes when scammers rotate the identifiers they use (the rotation experiment, `docs/EXPERIMENTS.md`). It is a
test bench for the logic, **not** a sample of real scam traffic and not a training corpus for a model.

## Composition of the committed sample (`data/scenarios.jsonl`, `--seed 1 --rotation 0.5`)

150 incidents, 737 utterances, 240 KB (budget 1 MB).

| Part | Count | Notes |
|---|---|---|
| Campaign incidents | 90 | six templates x 15, in instances of 3 incidents each (five instances per template) |
| Legitimate negatives | 40 | genuine bank alerts, one-time-password warnings, delivery notices, card and statement notices, a police verification call, family calls |
| Decoys | 20 | four types, five each (below) |

Templates: **T1** digital arrest (central agency, UPI), **T2** digital arrest (courier/customs officer, bank
transfer), **T3** digital arrest (telecom/police, UPI), **T4** bank KYC phishing (link), **T5** payment-link bill
scam (link), **T6** courier/customs parcel (UPI, asks for credentials). Stage order differs (T2 puts the demand before the urgency; T4
and T5 have no isolation stage; T6 has no threat stage).

Decoys (blueprint section 7.1; each should not form a confident campaign):

| Type | What it is |
|---|---|
| D1 similar wording, different origin | public-awareness notices that quote scam scripts ("fraudsters pretend to be officers...") |
| D2 shared identifier, benign context | genuine notices citing the official helpline 1930 or the cybercrime portal |
| D3 same tactics, incompatible chronology | scam-like calls whose stages come in a mostly reversed order |
| D4 ambiguous extraction | vague notes with no clear stage; some mention a number only in words, which cannot be extracted |

Languages: 130 English, 16 romanised Hindi (Hinglish), 2 Devanagari Hindi (T2), 2 Marathi (T3). Channels: 82
calls, 68 SMS. The Devanagari and Marathi samples are a handful, enough to exercise the code path, **not** to
measure performance in those languages.

## Two ground truths

* **(a) campaign instance:** a true pair shares `campaign_instance_id`.
* **(b) script family:** a true pair shares `script_family`: digital arrest = T1+T2+T3, bank KYC = T4, payment
  link = T5, courier/customs = T6. The map is by scam type and was fixed on 17 Nov 2026, before the test split or
  any experiment was used. T4 and T5 are deliberately kept apart.

Negatives and decoys are non-pairs under both. Different instances of one template run an identical script in this
generator, so a script-based method is expected to link them; under (a) that counts as wrong, under (b) as right.
Both are reported.

## Fields

`incident_id, conversation_id, scenario_type, campaign_template_id, campaign_instance_id, script_family,
decoy_type, source_channel, language, timestamp, rotated_fields, identifiers, entity_mentions,
expected_stage_sequence, credential_requested, institution_class, payment_channel, utterances[speaker, text,
tactic_labels, t_start_sec, idx, utterance_id], expected_associations, is_synthetic, provenance,
generator_version, seed, rotation, split`.

## Rotation parameter

For each instance, between successive incidents every identifier (phone, UPI handle, domain, bank account) is
replaced by a fresh synthetic one with probability `r`. `r = 0` keeps them, `r = 1` changes all of them. Every
identifier is unique across the dataset, so a shared identifier is always one the generator shared on purpose
(v1 could collide by chance; v2 retries until unique).

## Splits

By campaign template, never by paraphrase: **train** T1, T4, N1, N2, D1; **dev** T2, T5, N3, N4, D2; **test** T3,
T6, N5, N6, D3, D4. No template appears in two splits. (Train 49, dev 49, test 52 incidents.) The lexicon is
hand-written, so "train" is only a label for what the author looked at while writing and tuning; nothing is fitted
to a split.

## Known limitations (please read before quoting any number)

* **Same author, same templates.** The generator, the lexicon and the rules were written by the same author, from
  the same mental model of these scams. Scores are optimistic and say nothing about unseen real traffic.
* **Instances of one template are the same script.** This is what makes the fingerprint look weak under (a); a
  real campaign's variation is richer, and real campaigns drift.
* **Few templates (six) and few decoys (20).** Standard deviations over seeds show the generator's randomness, not
  uncertainty about the real world.
* **The decoys were written by the author too** and are one reasonable reading of the blueprint's four types, not
  an adversarial set. They were fixed before any experiment and are not adjusted after results.
* **Held-out set.** A separate set of 25 scenarios (19 scam, 6 legitimate) was drafted by a different language model
  (not Claude), then reviewed, edited and labelled by the owner, Shriya Patil. It is kept out of this repository's
  generator and evaluated once (`data/heldout/README.md`). It is the only check not written by the author of the
  rules, but it is small, has no per-utterance tactic labels (so **tactic-level scores are not measured on it**), and a
  language-model draft is not the same as real traffic.
* **Languages other than English are thin**, and romanised Hindi varies widely in real life.

## Reproduce

```
python scripts/generate_dataset.py --seed 1 --rotation 0.5          # the committed sample
python scripts/generate_dataset.py --validate-only                  # schema, labels, secrets, synthetic ranges
```
The test `test_committed_dataset_is_exactly_what_the_command_produces` fails if the file is stale. The generator's
LF-normalised sha256 and the sample's are recorded in `docs/PREREGISTRATION.md`.
