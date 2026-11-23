# LeakLens

**Find the leaks. Understand the losses. Protect your profits.**

LeakLens is a financial intelligence platform for business financial analytics, unusual-spend detection, cash-flow forecasting and explainable recommendations.

## Product decisions
- No sign-up, login, password or email collection in v1.0.
- React frontend + FastAPI backend.
- Black / white / electric-lime visual identity.
- Local demo data and user-uploaded files during development.
- An anomaly is not automatically fraud; potential exposure is not confirmed loss.
- Complete and test the product before production deployment.

## Repository structure
- `frontend/` — React, Vite, TypeScript, Tailwind, Recharts and Framer Motion.
- `backend/` — FastAPI service and Python analytics dependencies.
- `PROJECT_ROADMAP.md` — master scope, acceptance criteria and release gate.

## Run the frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

## Run the backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API health: http://localhost:8000/health  
OpenAPI docs: http://localhost:8000/docs

## Quality checks
```bash
cd frontend
npm test
npm run build
```
```bash
cd backend
pytest
```

## Current stage
Foundation and first dashboard shell are committed. The dashboard includes session-only CSV import/export and seeded illustrative demo records. Forecasting, anomaly ML, health scoring, recommendations, simulator and other roadmap modules remain under development.

## Deployment
Deployment is intentionally deferred until all development, integration, security, accessibility and end-to-end testing gates in `PROJECT_ROADMAP.md` are complete. Netlify is the final frontend deployment step; the Python API will need separate hosting.
