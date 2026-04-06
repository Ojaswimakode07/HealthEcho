# HealthEcho

HealthEcho is a medical-assistant web app with a static frontend and an optional FastAPI backend.

## Project Structure

- `healthecho_v5_improved (1).html` - main frontend entry page
- `assets/css/styles.css` - extracted app styles
- `assets/js/env.js` - frontend runtime config bridge
- `assets/js/firebase.js` - Firebase initialization and auth bootstrapping
- `assets/js/app.js` - main frontend logic
- `backend/main.py` - optional FastAPI backend
- `.env.example` - frontend config template
- `backend/.env.example` - backend config template

## Frontend Setup

1. Open `.env.example` and copy the values you want into `.env`.
2. Update `assets/js/env.js` with the runtime values you want exposed to the browser.
3. Open `healthecho_v5_improved (1).html` in a browser, or serve the folder with a simple static server.

## Backend Setup

1. Copy `backend/.env.example` to `backend/.env` if needed.
2. Install Python dependencies used by `backend/main.py`:

```bash
pip install fastapi uvicorn requests pillow pytesseract pydantic
```

3. Start the backend:

```bash
uvicorn backend.main:app --reload
```

The backend reads configuration from `backend/.env`.

## Environment Files

- `.env` is for local project configuration notes and values.
- `backend/.env` is read by the FastAPI backend directly.
- Because this frontend is plain HTML/JS, the browser does not load `.env` files by itself.
- Any frontend values that must exist at runtime should also be reflected in `assets/js/env.js`.

## Notes

- `.env` files are ignored by git.
- The hardcoded Groq default key was removed from the frontend logic.
- Firebase config is loaded through the external frontend config/bootstrap files now.
