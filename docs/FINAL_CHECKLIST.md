# Final checklist: making the repository public and checking the deployed link

Written for the repository owner. Items marked **(owner)** need your accounts or a real device; the rest were run by the
assistant and the results are recorded in `DEVELOPMENT_LOG.md` (Session 9).

## A. Before you flip the repository to public

1. **(owner) Decide the licence.** The repository has **no LICENSE file** and the README no longer claims one. A public repo
   with no licence means "all rights reserved". Choose one (for example MIT) and add `LICENSE`, then mention it in the README.
2. **History audit.** `python scripts/preflight.py --history` must pass: size measures M1, M2, M3 within limits, no blob over
   1 MB, only `main`, **no secrets in any commit**. (Run on the final commit; result in the log.)
3. **Local secrets are not in git.** `frontend/.env.local` (written by the Vercel CLI, contains a deployment token) and
   `vigil.db` exist only on your machine and are git-ignored. **(owner)** Delete `frontend/.env.local` and `.vercel/` if you no
   longer need them, and consider revoking the token in Vercel (Account Settings → Tokens) after publishing.
4. **(owner) Scan once more by eye:** open the repository on GitHub while still private and search for `token`, `secret`,
   `api_key`, `password`; check Settings → Secrets and variables is empty and no deploy keys exist.
5. **Only `main` exists.** `git ls-remote --heads origin` lists one branch. No tags or releases you do not want public.
6. **(owner) Repository metadata:** description ("Cross-channel scam intelligence: explainable, offline-first, synthetic data"),
   topics (`scam-detection`, `fraud`, `fastapi`, `react`, `explainable-ai`), the live URL as the website.
7. **(owner) Demo video:** upload (unlisted), then put the link under "Demo video" in `README.md`, run
   `python scripts/render_experiment_tables.py --check`, the tests and preflight, commit as ShriyaP1966 (no AI attribution),
   push.
8. **(owner) Vercel:** the project's Root Directory must stay `frontend` (without it a push does not deploy). After the flip,
   check that the Git integration still builds the latest commit and the Deployments tab shows **Ready**.

## B. The flip

9. **(owner)** GitHub → Settings → General → Danger Zone → Change visibility → Public. Type the repository name to confirm.

## C. After it is public (5 minutes)

10. Open the repository in a private window: README renders, the Mermaid diagram draws, the eight screenshots and the rotation
    chart show, the links to `docs/` work.
11. Clone it fresh into an empty folder and run the README quick start (no API key): backend tests, frontend tests, build,
    preflight. (The assistant did this on the final commit; do it once yourself if you want independent proof.)
12. **(owner) Submission dashboard (Hack2skill):** live URL, repository URL, video link, a one-paragraph description; check the
    required fields on the dashboard itself.

## D. Final check of the deployed link

Run by the assistant (headless browser, against https://vigil-demo-eta.vercel.app):

```
node scripts/check_deployed.mjs --edge "<msedge.exe>" --profile <empty temp dir>
```

It checks, on 12 routes at 1280 px and 390 px: loads with no console error and no sideways scroll; **deep links and refresh**
(`/campaigns/1`, `/incidents/1`, `/scenarios`, `/simulated-call`, `/reports`, `/graph?assoc=1`); **mobile layout** (drawer closed
by default, the hamburger opens it, tapping a link closes it); the **synthetic-data labelling** (top-bar badge on desktop and
phone, the Overview notice, the call-simulation notice); and that the site works with **no backend** (`/api/v1/health` is not
served, precomputed data files are).

**(owner)** What a script cannot show: open the link on **your phone on mobile data in a private window** and check that (a)
it loads with no blank screen, (b) the menu button opens and closes the drawer, (c) refreshing `/scenarios` stays on the
Scenario Lab, (d) the "Synthetic demo" label is visible in the top bar, (e) the simulated call plays to the end.

## E. Honest status to state if asked

* The public site is **static** (precomputed synthetic data); a hosted backend was **not** set up, so paste-your-own-evidence,
  analyst reviews and "Clear all local data" work only when the app is run locally.
* The held-out set is small and synthetic; tactic-level scores were not measured; 2 of 6 legitimate held-out scenarios were
  flagged as scams (README section 5.3 and 7).
* The tuned threshold is a post-hoc, separately reported result; the pre-registered 0.75 is the headline and the default.
