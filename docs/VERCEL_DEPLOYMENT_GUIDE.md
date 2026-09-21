# Vercel Deployment Guide — Crescendo Defense Lab

This guide explains how to deploy the **Crescendo PRD Defense Lab** web testbench, interactive telemetry dashboard, and master research dossiers to **Vercel** with zero server management.

---

## 1. Architecture on Vercel

```text
                                  User / Reviewer Browser
                                             │
                                             ▼
                          ┌─────────────────────────────────────┐
                          │     Vercel Global Edge Network      │
                          └──────────────────┬──────────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
        Static Assets (Edge CDN)                     Serverless Function (Python 3.10)
        ------------------------                     ---------------------------------
        • / (Dashboard Testbench)                    • POST /api/turn  (Evaluate prompt)
        • /results_dossier.html                      • GET  /api/scenarios (Preset demos)
        • /master_architecture_report.html           • GET  /api/status (System config)
        • /style.css & /app.js                       • POST /api/reset (Reset memory)
        • /plots/* (Empirical curves)                • Zero-Torch CPU-optimized pipeline
```

- **Frontend & Static Dossiers**: Hosted on Vercel's global CDN in the `public/` directory for sub-millisecond static page delivery.
- **Backend API (`/api/*`)**: Handled by a serverless Python function in `api/index.py` using `BaseHTTPRequestHandler`.
- **Lightweight Dependencies**: Uses `requirements.txt` containing only `numpy>=1.22.0`, allowing Vercel to build and bundle in **< 10 seconds** without hitting Vercel's 250 MB serverless size ceiling.
- **Offline/Local Research Dependencies**: Stored separately in `requirements-full.txt` (for PyTorch/GPU model fine-tuning).

---

## 2. Deploying via Vercel Web Dashboard (Recommended — 2 Clicks)

Because your code is already synchronized with GitHub (`https://github.com/suryakshar1205/crescendo_jail_break`):

1. Go to [vercel.com](https://vercel.com) and log in with your GitHub account.
2. Click **"Add New..."** $\to$ **"Project"**.
3. Under **Import Git Repository**, find `crescendo_jail_break` and click **"Import"**.
4. In the **Configure Project** window:
   - **Project Name**: `crescendo-defense-lab` (or leave default)
   - **Framework Preset**: Leave as **"Other"**
   - **Root Directory**: `./` (leave default)
   - **Build and Output Settings**: Leave default (Vercel automatically reads `vercel.json` and `public/`).
5. Click **"Deploy"**.
6. Vercel will install dependencies, package the serverless function, and give you a live HTTPS URL (e.g., `https://crescendo-defense-lab.vercel.app`) in approximately 30 to 45 seconds!

---

## 3. Configuration Files Reference

The following files enable native Vercel deployment:

| File | Purpose |
|:---|:---|
| [`vercel.json`](file:///c:/Users/surya/Desktop/crescendo_jail_break/vercel.json) | Routes `/api/*` to `api/index.py`, enables CORS headers, and configures cache headers for plots. |
| [`api/index.py`](file:///c:/Users/surya/Desktop/crescendo_jail_break/api/index.py) | Python serverless handler supporting `/api/turn`, `/api/scenarios`, `/api/status`, and `/api/reset`. |
| [`api/requirements.txt`](file:///c:/Users/surya/Desktop/crescendo_jail_break/api/requirements.txt) | Minimal serverless dependencies (`numpy>=1.22.0`). |
| [`requirements.txt`](file:///c:/Users/surya/Desktop/crescendo_jail_break/requirements.txt) | Root serverless production requirements. |
| [`requirements-full.txt`](file:///c:/Users/surya/Desktop/crescendo_jail_break/requirements-full.txt) | Offline GPU benchmarking & PyTorch dependencies. |
| [`public/`](file:///c:/Users/surya/Desktop/crescendo_jail_break/public) | Static frontend folder containing `index.html`, `style.css`, `app.js`, `results_dossier.html`, `master_architecture_report.html`, and `plots/`. |

---

## 4. Verification Checklist on Live Vercel URL

Once deployed, you can verify every feature directly:

1. **Dashboard Home (`/`)**:
   - Verify the telemetry gauges (`H`, `E`, `S`, `B`), state machine nodes, and chat area load.
2. **Preset Scenario Auto-Play**:
   - Select `"Live Demo 1: In-Memory DLL Injection"` from the dropdown.
   - Click `"Auto-Play Scenario"` and watch turns 1 $\to$ 4 evaluate with live telemetry and trigger terminal `BLOCK`.
3. **Master Results Dossier (`/results_dossier.html`)**:
   - Click the top navigation button `"📊 Results Dossier"`.
   - Verify that analytical figures and KaTeX equations render cleanly.
4. **Master Architecture Blueprint (`/master_architecture_report.html`)**:
   - Click the top navigation button `"🏛️ Architecture Blueprint"`.
   - Verify that the Mermaid architecture flowchart and mathematical formulas render interactively.
