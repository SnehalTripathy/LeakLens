# LeakLens

**Find the leaks. Understand the losses. Protect your profits.**

LeakLens is a financial intelligence workspace for analysing business transactions, surfacing unusual spending patterns, forecasting financial trends and prioritising evidence-based cost reviews.

## Product decisions
- No sign-up, login, password or email collection in v1.0.
- React + Vite + TypeScript frontend and Python + FastAPI backend.
- Brand palette: Midnight Black `#0B0B0C`, Pure White `#FFFFFF`, Electric Lime `#C6F432`, with restrained graphite/sage/amber functional accents.
- Local demo ledger and CSV/XLS/XLSX imports.
- Multiple currencies are not converted; financial analytics use the workspace's most common currency and report currency counts.
- Anomaly scores are relative indicators, not probabilities of fraud. Potential exposure is not a confirmed loss or guaranteed saving.
- The assistant is deterministic and grounded in workspace data; it currently does not call an external LLM.

## Current capabilities
- Financial overview, revenue and expense intelligence, month comparisons and category budgets.
- Transaction search, filters, import, create, edit and delete.
- Rule-based vendor/category/recurring-cost leak signals with evidence.
- Isolation Forest + Local Outlier Factor anomaly comparison.
- Revenue/expense trend forecasting with backtest MAE and indicative uncertainty bands.
- Transparent six-dimension financial health score and evidence-based recommendations.
- What-if revenue/expense scenario calculator.
- Vendor and recurring subscription insights.
- Alert lifecycle, ledger-grounded assistant, data-quality view and CSV/PDF reporting.

## Repository structure
- `frontend/` — React UI, design system, charts, interaction components and API client.
- `backend/` — FastAPI, transaction storage, analytics, anomaly and forecasting engines.
- `PROJECT_ROADMAP.md` — feature status, acceptance criteria, release gates and deployment plan.

## Requirements
- Node.js 20+
- Python 3.11+ (CI currently uses Python 3.12)

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
API docs: http://localhost:8000/docs

The first API start creates a local SQLite database under `.data/` and seeds a six-month demo ledger. Imported and manually edited transactions are stored in that local database.

## Tests
```bash
cd backend
PYTHONPATH=. pytest
```
```bash
cd frontend
npm test
npm run build
```

GitHub Actions runs backend tests, frontend tests and a TypeScript/Vite production build on pushes and pull requests to `main`.

## Important deployment/privacy note
Authentication is intentionally disabled in v1.0. The current backend is a single-workspace local-development service. Do not expose it publicly with persistent financial uploads: without authentication, users would share access to the same workspace. Before deployment, choose a protected/private single-user hosting model or convert the public instance into a read-only demo with no persistent user uploads. The backend also needs a persistent production database; current SQLite storage is intended for local development.

## Deployment policy
Deployment is intentionally deferred. The React frontend will be deployed to Netlify only after all development, integration, security, accessibility and end-to-end release checks in `PROJECT_ROADMAP.md` are complete. The FastAPI backend requires separate Python-capable hosting.
