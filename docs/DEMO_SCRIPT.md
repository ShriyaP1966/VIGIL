# 3-minute demo video: script and shot list

**Rules for the recording.** Use **only the live site** (https://vigil-demo-eta.vercel.app) and its **synthetic** data. Do not
open the Vercel dashboard, GitHub settings, `.env` files, terminals with tokens, or any real message, number or person. Say
"hypothesis", never "confirmed campaign". Say "simulation" whenever the call page is on screen. Keep the browser at about
1280 × 800, dark theme, zoom 100%. Speak at roughly 150 words a minute; the narration below is about 430 words.

Before recording: open the site once so the data is cached, close other tabs, hide bookmarks, turn off notifications.

| Time | On screen (exact URL and action) | Narration |
|---|---|---|
| **0:00-0:15** | `/` (Overview). Pause on the green "Hosted demo: precomputed synthetic data" badge and the "Synthetic data" notice. | "Scammers rotate phone numbers, UPI handles and domains, so ten reports of the same script can look like ten unrelated cases. VIGIL helps an analyst see across them. Everything you will see is synthetic." |
| **0:15-0:40** | Click **Investigations** → open the first case (`/incidents/1`). Scroll the tactic timeline, then the risk ledger. | "Each case gets a tactic timeline: authority, allegation, threat, isolation, urgency, demand. The risk indicator is a heuristic, not a probability, and every contribution is listed and sums exactly to the score." |
| **0:40-1:10** | **Intelligence Graph** (`/graph`). Point at the legend. Click the solid blue link → **Evidence Inspector** opens (`/graph?assoc=1`). Scroll to the source excerpts and the counter-evidence area. | "A solid line is an exact shared identifier: an observation, not proof of one origin. A dashed amber line is only a similar script. Every link opens an inspector with the source text, how the match was made, and counter-evidence shown right beside it." |
| **1:10-1:40** | **Scenario Lab** (`/scenarios`) → "Digital arrest: central-agency impersonation". Drag the rotation slider from 0 to 1. Click **Replay**. | "Here is the problem the project tests. With no rotation, identifiers link these three incidents. Slide to full rotation and the exact links disappear, while the behavioural script still connects them as a candidate. Replay gives an identical result: it is deterministic." |
| **1:40-2:10** | **Simulated Call Analysis** (`/simulated-call`) → script "Scam call with an injected instruction" → **Play**. Pause on the injection badge and the Hindi guidance. | "This is a simulation of scripted text. VIGIL does not listen to calls. Each turn is analysed as it arrives: stages light up, risk climbs. When the caller tries to instruct the analyser to mark the call safe, a safety badge fires and the risk cannot go down. Guidance appears in English and Hindi." |
| **2:10-2:30** | **Reports** (`/reports`). Scroll the five sections; click **Download CSV**. | "Each case exports a report that keeps observed facts, model inferences, analyst decisions and counter-evidence apart, with the limitations attached." |
| **2:30-2:55** | Open the repository README on GitHub, scroll to **5. Results, honestly** (chart, then the held-out table). | "We pre-registered the rotation experiment. Identifier linking collapses under rotation. The fingerprint recovers links but over-merges, and a tuned threshold, chosen after seeing results, is reported separately. On a small held-out set, 18 of 19 scams were detected, but 2 of 6 legitimate messages were flagged, likely because the rules match wording, not intent. We did not change the rules afterwards." |
| **2:55-3:00** | Back to the live site, `/`. | "VIGIL: explainable, offline-first, honest about its limits. Link below." |

**Optional 5-second insert** (only if time allows): resize to a phone width or open the live site on a phone to show the menu
drawer on `/incidents`.

**Do not show:** the Settings "Clear all local data" button in the hosted demo (it is disabled there), any terminal, the Vercel
or GitHub admin pages, or the development log. **Do not claim:** real-time protection, attribution to any group, real data,
tactic-level scores on the held-out set (they were not measured), or that the tuned threshold is the product default (it is not).

**After recording:** upload to YouTube (unlisted) or Drive, add the link under "Demo video" at the top of `README.md`, and
re-run `python scripts/render_experiment_tables.py --check` and the tests before committing the README.
