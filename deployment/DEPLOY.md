# VIGIL v3.1 — Deployment Guide (§14)

> **Zero-Cost, Static-First Public Deployment**
> Required for submission. Guaranteed to work on any device at any time, even if the free backend container is asleep.

---

## Architecture Overview

```
                      Browser (Judge / Evaluator)
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   Frontend (Vercel / Netlify)               Backend (Render Free Web Service)
   - Static Vite React SPA                   - FastAPI / Uvicorn Python 3.11+
   - Precomputed Demo JSON                   - Sleeps after 15 min of inactivity
   - Dual-adapter: HttpApi + StaticApi       - Ephemeral disk (SQLite reseeded)
```

1. **Static-First Guarantee:**
   All benchmark scenarios, entity graphs, campaign hypotheses, and evaluation charts are precomputed by `scripts/export_static_demo.py` into `frontend/public/demo-data/`.
   When a judge opens the public link, the client probes `GET /health`:
   - If the backend is active, the app uses `HttpApi` (Live Mode).
   - If the backend is sleeping, the app transparently serves precomputed data via `StaticApi` and displays *"Hosted demo: precomputed synthetic data (waking live backend...)"*.

---

## Step 1: Deploy Frontend (Vercel)

1. Log in to [Vercel](https://vercel.com) (free Hobby tier, no card required).
2. Click **Add New...** → **Project**.
3. Import the GitHub repository: `ShriyaP1966/VIGIL`.
4. Configure Project Settings:
   - **Framework Preset:** Vite
   - **Root Directory:** `./` (or `frontend` if deploying frontend alone)
   - **Build Command:** `cd frontend && npm run build` (or default if root is `frontend`)
   - **Output Directory:** `frontend/dist`
5. Environment Variables:
   - `VITE_API_BASE_URL`: (Optional) URL of the Render backend once deployed (e.g., `https://vigil-backend.onrender.com`).
6. Click **Deploy**.
7. Note down the public frontend URL (e.g., `https://vigil-demo.vercel.app`).

---

## Step 2: Deploy Backend (Render - Optional Live Enhancement)

1. Log in to [Render](https://render.com) (free tier, no card required).
2. Click **New +** → **Web Service**.
3. Connect the GitHub repository `ShriyaP1966/VIGIL`.
4. Configure Web Service:
   - **Name:** `vigil-backend`
   - **Region:** Any free region (e.g., Oregon)
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free (0.1 CPU, 512 MB RAM)
5. Environment Variables:
   - `APP_MODE`: `offline`
   - `DATABASE_URL`: `sqlite:///./vigil.db`
   - `T_CANDIDATE`: `0.75`
   - `LOG_LEVEL`: `INFO`
   - `FRONTEND_ORIGIN`: Your Vercel frontend URL (e.g., `https://vigil-demo.vercel.app`)
6. Click **Create Web Service**.

---

## Step 3: Verification Checklist

- [ ] Open the frontend URL on mobile data / external device in an incognito window.
- [ ] Confirm no blank screen, console errors, or broken layouts.
- [ ] Verify that graph navigation, scenario playback, and inspector panels work instantly in Static mode.
- [ ] Paste a custom transcript when backend is awake and verify live analysis.
