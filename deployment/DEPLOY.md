# VIGIL v3.1 — Deployment Guide (blueprint §14)

> **Zero-cost, static-first public deployment.** A free public link is required for submission.
> The link must work on any device at any time, even when the free backend container is asleep.

```
                  Browser (judge / evaluator)
                              │
         ┌────────────────────┴─────────────────────┐
         ▼                                          ▼
 Frontend (Vercel / Netlify)               Backend (Render free web service, OPTIONAL)
 - static Vite + React build               - FastAPI, run from the repo root
 - precomputed demo JSON (StaticApi)       - sleeps after ~15 min idle, ephemeral disk
 - probes <backend>/api/v1/health          - reseeds synthetic data on every cold start
```

**Static-first guarantee.** `scripts/export_static_demo.py` runs the real pipeline on the synthetic seed
incidents and writes the API responses to `frontend/public/demo-data/`. The client probes the backend's
`/api/v1/health` (2 s timeout, must return JSON `{"status": "ok"}`). If it answers, the app uses the live
`HttpApi`; otherwise it uses the precomputed data (`StaticApi`) and says so in the mode badge.
Regenerate the demo data after any pipeline change: `python scripts/export_static_demo.py`.

> Free-tier limits and terms change. Verify them on the day. No card should be needed; if a host asks for one, choose another host.

---

## Step 1 — Frontend (Vercel, free Hobby plan)  *(requires your sign-in)*

1. Sign in at https://vercel.com and choose **Add New → Project**; import `ShriyaP1966/VIGIL`.
2. Project settings. The authoritative file is **`frontend/vercel.json`** (Vite build, `npm ci`, output `dist`, and
   the single-page-app rewrite so that `/campaigns`, `/incidents/<id>` and other deep links survive a refresh;
   `/api/`, `/demo-data/` and `/assets/` are never rewritten). It is only read when the Root Directory is `frontend`:
   - Framework preset: **Vite**
   - Root Directory: **`frontend`** (set in the Vercel dashboard)
   - Install / Build / Output: taken from `frontend/vercel.json` (`npm ci`, `npm run build`, `dist`)
   - Git integration stays on: a push to `main` redeploys the site. The CLI is not needed.
   - `deployment/vercel.json` is the older repository-root variant (no rewrite). Do not use it with the `frontend` root.
3. Environment variable (add only after the backend exists): `VITE_API_BASE_URL` = the Render URL, no trailing slash.
4. Deploy and record the URL in the table at the bottom of this file.

Netlify alternative: base directory `frontend`, build `npm run build`, publish `frontend/dist`.

## Step 2 — Backend (Render free web service, optional)  *(requires your sign-in)*

Use `deployment/render.yaml` as a Blueprint (**New → Blueprint**), or create a Web Service manually:

- Runtime: Python 3 (`PYTHON_VERSION=3.11.9`), Root Directory: **repository root** (not `backend/`, because the code imports `backend.*` and `ai_engine.*`)
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`
- Environment: `APP_MODE=offline`, `DATABASE_URL=sqlite:///./vigil.db`, `SEED_ON_START=true`,
  `FRONTEND_ORIGIN=<your Vercel origin, no trailing slash>`. Never add secrets; none are needed.

`SEED_ON_START=true` loads the three synthetic incidents when the database is empty, because the free disk is ephemeral.

## Step 3 — Verification checklist (blueprint §14)

- [ ] Open the frontend URL from a second device on mobile data and in a private window.
- [ ] No blank screen, console errors or broken layout; the mode badge shows precomputed or live mode truthfully.
- [ ] With the backend asleep (idle > 30 min) the graph, inspector and incident pages still work from precomputed data.
- [ ] With the backend awake, pasting a synthetic transcript creates an incident via the live API.
- [ ] HTTPS works and no secrets are present in the bundle or repo.

## Deployed URLs

The frontend is deployed on Vercel (static-first: it serves precomputed synthetic data while no backend is
reachable). The backend on Render has not been set up; it needs a Render sign-in from the repository owner.

| Component | URL | Verified (date, device) |
|---|---|---|
| Frontend | https://vigil-demo-eta.vercel.app | Public access confirmed over HTTPS on 2026-11-17. The deep-link and phone-layout fixes were verified on a local build in headless Edge; not yet verified on a real phone. |
| Backend (optional) | _pending_ | _pending_ |
