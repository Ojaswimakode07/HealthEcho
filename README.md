# HealthEcho Repository

This repository now contains two related application tracks:

- `HealthEcho`: the original medical-assistant web app and deployment setup already present on `main`
- `HealthNova`: the newer frontend and backend application added in this push

## HealthEcho

HealthEcho is a medical-assistant web app with a static frontend and an optional FastAPI backend.

Main existing files include:

- `index.html`
- `assets/css/styles.css`
- `assets/js/env.js`
- `assets/js/firebase.js`
- `assets/js/app.js`
- `api/index.py`
- `backend/main.py`
- `backend/requirements.txt`
- `vercel.json`
- `render.yaml`

## HealthNova

HealthNova is a full-stack medical report analysis and chat workspace.

### Included directories

- `healthnova-frontend/` - Vite + React frontend
- `healthnova-backend/` - FastAPI backend
- `medical_docs/` - local medical knowledge sources
- `vectorstore/` - generated retrieval index data

### HealthNova frontend

Key files:

- `healthnova-frontend/src/App.jsx`
- `healthnova-frontend/src/pages/WorkspacePage.jsx`
- `healthnova-frontend/src/pages/LandingPage.jsx`
- `healthnova-frontend/src/services/api.js`

Setup:

```bash
cd healthnova-frontend
npm install
copy .env.example .env
npm run dev
```

### HealthNova backend

Key files:

- `healthnova-backend/app/main.py`
- `healthnova-backend/app/routes/analyze.py`
- `healthnova-backend/app/routes/chat.py`
- `healthnova-backend/app/modules/extract_values.py`
- `healthnova-backend/app/modules/ocr.py`

Setup:

```bash
cd healthnova-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Helper scripts

Repository root helper scripts for HealthNova include:

- `start-healthnova.ps1`
- `run-backend.ps1`
- `backend-watchdog.ps1`
- `backend-supervisor.ps1`
- `smoke-test.ps1`

## Notes

- Local `.env` files, virtual environments, logs, and build output are gitignored.
- The HealthNova backend includes Groq-assisted analysis and chat routes.
- The HealthNova frontend includes the workspace chat, report analysis UI, and local persistence helpers.
