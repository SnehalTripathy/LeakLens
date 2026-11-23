# LeakLens

**Find the leaks. Understand the losses. Protect your profits.**

LeakLens is a financial intelligence workspace for business transaction analysis, unusual-spend detection, trend forecasting and evidence-based cost-control recommendations.

## Product decisions
- No sign-up, login, password or email collection in v1.0.
- React + Vite + TypeScript frontend and Python + FastAPI backend.
- Brand palette: Midnight Black `#0B0B0C`, Pure White `#FFFFFF`, Electric Lime `#C6F432`, with restrained graphite/sage/amber functional accents.
- Local demo ledger and CSV/XLS/XLSX imports with a preview and explicit confirmation step.
- Multiple currencies are not converted or combined; analytics use the most common currency and disclose the scope.
- Anomaly scores are relative indicators, not probabilities of fraud. Potential exposure is not a confirmed loss or guaranteed saving.
- The assistant is deterministic and ledger-grounded; it does not send data to an external AI provider.

## Current capabilities
- Financial overview, revenue/expense intelligence, period comparisons and category budgets.
- Transaction import preview, validation, deduplication, create/edit/delete, search and filters.
- Rule-based leak signals with evidence, potential exposure and alert review workflow.
- Isolation Forest + Local Outlier Factor anomaly comparison and contextual explanations.
- Revenue/expense forecasts with linear, last-value, moving-average and 12-month seasonal-naive model selection (seasonality requires 24 contiguous months), backtest metrics and indicative uncertainty bands.
- Transparent six-dimension health score, daily score history and evidence-linked recommendations.
- What-if financial simulator, vendor and recurring subscription insights.
- Alert lifecycle with reopen and status history.
- Data-grounded assistant, data-quality checks and CSV/PDF reports.

## Public dataset research\n- Reproducible UCI Online Retail II cleaning, monthly/country/invoice aggregation and rolling-origin revenue forecast benchmarking: [`docs/PUBLIC_DATASET_STUDY.md`](docs/PUBLIC_DATASET_STUDY.md).\n- Raw public data is downloaded locally and excluded from Git; no source workbook or derived customer-level raw rows are committed.\n\n## Local QA and sample import
- Sample import file: [`samples/sample-transactions.csv`](samples/sample-transactions.csv)
- Manual browser, responsive, import, alert, report and persistence checks: [`docs/LOCAL_QA_CHECKLIST.md`](docs/LOCAL_QA_CHECKLIST.md)

## Repository structure
- `frontend/` — React UI, design system, charts, interactions and API client.
- `backend/` — FastAPI, SQLite local workspace store, financial analytics, anomaly and forecasting engines.
- `PROJECT_ROADMAP.md` — implementation status, acceptance criteria and release gates.

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
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API health: http://localhost:8000/health  
API docs: http://localhost:8000/docs

The first API start creates a local SQLite database under `.data/` and seeds a six-month demo ledger. Imported and manually edited transactions persist in that local database.

## Tests
```bash
cd backend
PYTHONPATH=. pytest
```
```bash
cd frontend
npm test
npm run build
npm audit
```
```bash
cd backend
python -m pip install pip-audit
pip-audit -r requirements.txt
```

GitHub Actions runs backend tests, frontend tests and a TypeScript/Vite production build, plus npm and Python dependency audits, on pushes and pull requests to `main`.

## Important deployment and privacy note
Authentication is intentionally disabled in v1.0. The current backend is a single-workspace local-development service. Do not expose it publicly with persistent financial uploads: without workspace isolation, visitors would share access to the same workspace. Before deployment, choose a protected/private anonymous-workspace design or convert the public instance into a read-only demo with no persistent user uploads. The backend also needs a production database; current SQLite storage is intended for local development.

## Deployment
Deployment is deliberately deferred. The React frontend will be deployed to Netlify only after the development, integration, security, accessibility and end-to-end release checks in `PROJECT_ROADMAP.md` are complete. The FastAPI backend requires separate Python-capable hosting.
