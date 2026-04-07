# HealthEcho

HealthEcho is a medical-assistant web app with a static frontend and an optional FastAPI backend.

## Project Structure

- `index.html` - deployment-friendly frontend entry page
- `healthecho_v5_improved (1).html` - main frontend page
- `assets/css/styles.css` - extracted app styles
- `assets/js/env.js` - frontend runtime config bridge
- `assets/js/firebase.js` - Firebase initialization and auth bootstrapping
- `assets/js/app.js` - main frontend logic
- `api/index.py` - Vercel Python entrypoint
- `backend/main.py` - optional FastAPI backend
- `backend/__init__.py` - backend package marker
- `backend/requirements.txt` - backend Python dependencies
- `requirements.txt` - root Python dependencies for Vercel
- `Procfile` - backend start command for Procfile-based hosts
- `render.yaml` - optional Render blueprint for frontend + backend
- `vercel.json` - Vercel routing for static frontend + Python API
- `.env.example` - frontend config template
- `backend/.env.example` - backend config template

## Frontend Setup

1. Open `.env.example` and copy the values you want into `.env`.
2. Update `assets/js/env.js` with the runtime values you want exposed to the browser.
3. Open `index.html` in a browser, or serve the folder with a simple static server.

## Backend Setup

1. Copy `backend/.env.example` to `backend/.env` if needed.
2. Install Python dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Start the backend:

```bash
uvicorn backend.main:app --reload
```

The backend reads configuration from `backend/.env`.

## Deployment

### Static Frontend

- Deploy the repo root as a static site.
- Use `index.html` as the entry file.
- `assets/js/env.js` now defaults to the same origin on `http` or `https`, which works for single-host deployments.
- If your frontend and backend are on different domains, set `apiBase` in `assets/js/env.js` to your deployed backend URL.
- If your frontend and backend are on different domains, set `HEALTHECHO_ALLOW_ORIGINS` in the backend to your frontend origin.

Example:

```js
window.HEALTHECHO_ENV = Object.assign(
  {
    apiBase: 'https://your-backend-domain.onrender.com',
    groqApiKey: '',
    firebase: {
      apiKey: 'YOUR_FIREBASE_API_KEY',
      authDomain: 'YOUR_PROJECT.firebaseapp.com',
      projectId: 'YOUR_PROJECT_ID',
      storageBucket: 'YOUR_PROJECT.firebasestorage.app',
      messagingSenderId: 'YOUR_SENDER_ID',
      appId: 'YOUR_APP_ID',
      measurementId: 'YOUR_MEASUREMENT_ID'
    }
  },
  window.HEALTHECHO_ENV || {}
);
```

### Backend

- The backend is ready to deploy to Render, Railway, Heroku-style Procfile hosts, or any VM/container that can run `uvicorn`.
- Install from `backend/requirements.txt`.
- Start with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

- Health check endpoint: `GET /health`
- Report extraction endpoint preserved for deployment compatibility: `POST /reports/extract-simple`
- Legacy upload endpoint also remains available: `POST /upload`

### Render

- `render.yaml` is included for a two-service setup:
- one Python web service for the backend
- one static site for the frontend

After deploy, update `assets/js/env.js` so `apiBase` matches the actual backend URL if your platform does not inject it automatically.

### Vercel

- `vercel.json` and `api/index.py` are included so Vercel can serve the static frontend and route API requests into FastAPI.
- The frontend now uses the same deployed domain by default, so `/health`, `/predict`, `/upload`, `/history`, and `/reports/extract-simple` can work from one Vercel project.
- On Vercel, SQLite and temporary upload files now use the runtime temp directory instead of the read-only repo folder.
- SQLite on Vercel serverless is still temporary, so use it only for testing unless you move to an external database.

## Environment Files

- `.env` is for local project configuration notes and values.
- `backend/.env` is read by the FastAPI backend directly.
- Because this frontend is plain HTML/JS, the browser does not load `.env` files by itself.
- Any frontend values that must exist at runtime should also be reflected in `assets/js/env.js`.

## Notes

- `.env` files are ignored by git.
- The hardcoded Groq default key was removed from the frontend logic.
- Firebase config is loaded through the external frontend config/bootstrap files now.
- `pytesseract` and `pdf2image` may require system packages on your backend host for full OCR/PDF extraction support.
