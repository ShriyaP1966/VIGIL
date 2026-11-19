# Privacy and ethical safeguards (as built)

VIGIL is a research and demonstration tool for **synthetic** scam evidence. It is not certified for personal data,
makes no compliance claim (for example under India's DPDP Act 2023), and must not be used with real victims' data.

## What the project contains and collects

* **All data is synthetic.** The generator, the seed incidents, the scenarios, the scripted call simulations and the
  held-out set use invented names, invented numbers, the example phone range `+91 98765 xxxxx`, `.example` domains and
  invented UPI handles. Every incident is marked `is_synthetic`.
* **No accounts, no analytics, no tracking, no cookies, no third-party calls.** The hosted demo
  (https://vigil-demo-eta.vercel.app) is a static site that reads precomputed synthetic JSON. It stores nothing you do
  and sends nothing anywhere except the normal web requests for its own files (the host's access logs apply).
* **Offline by default.** The analysis engine is rule-based Python with no network access and no API key. A
  `GEMINI_API_KEY` setting exists but nothing reads it; no cloud service is called.

## What the local backend stores (when you run it yourself)

In a local SQLite file (`vigil.db`, never committed): the evidence text **after redaction**, its normalised form and
SHA-256, extracted identifiers in **normalised form** (phones, UPI handles, emails, domains, URLs, bank account numbers,
organisation names) so exact matches can be found, tactic events, risk contributions, associations, counter-evidence,
analyst reviews and **counts** of redactions (the redacted values themselves are never kept). `Settings → Clear all
local data` (`DELETE /api/v1/data?confirm=true`) erases all of it.

## Redaction of secrets (best effort)

Before anything is hashed, stored, logged or analysed, OTPs, passwords, PINs, CVVs, card numbers and Aadhaar numbers are
replaced by placeholders such as `[REDACTED:OTP]`. It runs at the request boundary and again in the service layer, and it
fails closed: if redaction errors, nothing is stored. Phones, UPI handles, emails, domains and bank account numbers are
**kept on purpose**, because matching them is the point of the tool; on screen they are masked.

**Known limits (tested and documented):** spelled-out digits ("four eight two…"), secrets with no cue word nearby ("the
number from the sms is 482913"), non-Luhn card numbers with no "card" cue, and unusual formats are not caught. A 4-6 digit
value after "PIN" is redacted even if it was a postal code. Plain text reaches the server before it is redacted, so use
HTTPS and synthetic data. A leak test checks the database, API responses and logs for known secret patterns.

## Handling of untrusted text

* Evidence is **never rendered as HTML**; it is shown as plain text. URLs in evidence are parsed, **never fetched**.
* A regex **prompt-injection guard** flags text that tries to instruct the analyser. Flagged spans are masked before
  extraction, no risk mitigation is applied to flagged text, and the UI shows a safety badge. It does not catch
  obfuscated or paraphrased attacks.
* Exported **reports** contain masked identifiers and counts, never raw evidence text. The CSV writer neutralises
  spreadsheet formulas (a leading `= + - @` gets a `'`).

## Ethical safeguards in the product

* **No attribution.** The playbook fingerprint recognises a script family, never a specific group, person or
  organisation. Campaigns are hypotheses until an analyst accepts them, and are labelled so everywhere. An exact
  identifier match is an observation, not proof of a common origin.
* **Counter-evidence is shown next to the evidence**, not hidden: benign shared identifiers (for example the national
  helpline 1930), incompatible chronology, different payment destinations.
* **The risk score is an experimental heuristic**, not a probability, with its contributions listed and summing exactly to
  the score. Decisions stay with a human analyst; VIGIL blocks nothing and accuses no one.
* **Simulated Live Call Analysis is a simulation** of scripted text. VIGIL does not intercept, listen to or record calls,
  and the product does not claim real-time call protection.
* **Honest reporting.** Every metric comes from a script; experiments were pre-registered; a post-hoc analysis is labelled
  as such; the held-out result is reported as it came out, including its false alarms (`docs/EXPERIMENTS.md`).

## If you want to use it beyond the demo

You would need a data-protection assessment, access control and audit logging, encryption at rest, retention rules and a
lawful basis for processing, none of which this prototype provides.
