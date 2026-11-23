# LeakLens

**Find the leaks. Understand the losses. Protect your profits.**

LeakLens helps businesses make sense of their financial activity. Import transaction records, review unusual spending, track revenue and expenses, and identify areas that may need attention.

It brings everyday financial analysis into one workspace, with clear explanations behind its findings.

## What you can do with LeakLens

- **Review your finances:** See income, expenses, balances, category breakdowns and changes across reporting periods.
- **Import transaction data:** Upload CSV, XLS or XLSX files. Review the detected columns and records before confirming an import.
- **Find unusual activity:** Surface possible duplicate payments, sudden vendor increases, recurring charges and other spending patterns.
- **Understand trends:** Compare revenue and expenses, view forecasts and check how the selected forecasting method performed against historical data.
- **Keep budgets in view:** Set category budgets and compare them with actual and projected spending.
- **Explore vendors and subscriptions:** Review vendor concentration, recurring payments and differences between observed charges and contract details you enter.
- **Plan ahead:** Use recommendations and the what-if simulator to explore possible changes to revenue, expenses and one-off costs.
- **Work with your own accounting structure:** Configure cash or accrual reporting, fiscal-year settings, branches and category-to-account mappings.
- **Review and export:** Track alert decisions, inspect data-quality information, and export transaction data or financial summaries.

## How the analysis works

LeakLens combines transaction rules, statistical methods and financial summaries to highlight activity worth reviewing.

Findings are intended to support investigation, not replace it. An anomaly score is not a probability of fraud. A flagged transaction is not proof of wrongdoing, and estimated exposure should not be treated as a confirmed loss or guaranteed saving.

Forecasts are estimates based on the available transaction history. Their usefulness depends on the quality and coverage of the data provided.

The built-in assistant answers questions using the current workspace's financial data. It does not send transaction information to an external AI service.

## Getting started

### Requirements

- Node.js 20 or later
- Python 3.11 or later

### 1. Start the backend

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the dependencies and start the API:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API will be available at:

- Health check: http://localhost:8000/health
- API documentation: http://localhost:8000/docs

### 2. Start the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite, usually http://localhost:5173.

### 3. Explore the sample workspace

On its first start, the backend creates a local SQLite database in `.data/` and loads a six-month sample ledger. The sample company, vendors and transactions are fictional and are included to demonstrate the analysis and import workflows.

You can also try importing [the sample transaction file](samples/sample-transactions.csv). The import screen provides a preview before records are added.

## Data and privacy

LeakLens v1.0 is designed as a local development workspace:

- It does not require an account, email address or password.
- Financial records are stored in a local SQLite database.
- The built-in assistant processes workspace data locally and does not call an external AI provider.
- Multiple currencies are not converted into a common currency. Reports keep currency context rather than adding unlike amounts together.

**Do not expose the current backend to the public internet.** It is a single-workspace service without user authentication or workspace isolation. Anyone who can reach an exposed instance could access the same workspace. Before using it with real financial information or deploying it for multiple users, a secure access model, workspace separation and production database must be implemented.

Local backup, restore, retention and financial-data deletion endpoints are disabled by default. They can be enabled for trusted local administration with `LEAKLENS_ENABLE_LOCAL_ADMIN=true`. Keep this setting disabled in normal use and never enable these endpoints on a publicly reachable service.

## Technology

- **Frontend:** React, Vite, TypeScript
- **Backend:** Python, FastAPI
- **Storage:** SQLite for local development
- **Analysis:** Financial rules, statistical anomaly detection and forecasting methods
- **Charts and reporting:** Interactive financial visualisations, CSV exports and PDF summaries

## Running the tests

Backend tests:

```bash
cd backend
PYTHONPATH=. pytest
```

Frontend tests and production build:

```bash
cd frontend
npm test
npm run build
```

Dependency audits:

```bash
cd frontend
npm audit
```

```bash
cd backend
python -m pip install pip-audit
pip-audit -r requirements.txt
```

The GitHub Actions workflow runs the backend and frontend checks, dependency audits and a browser-based release smoke test. The browser test covers the main import, detection, review and export flow, along with accessibility and responsive-layout checks.

## Project structure

```text
LeakLens/
├── backend/       FastAPI application, data store and analysis engines
├── frontend/      React application and user interface
├── docs/          Research notes and testing guidance
├── samples/       Example transaction files
└── scripts/       Development and release checks
```

## Current status

LeakLens is under active development. The local application and automated test suite are available to explore, but the project is not yet ready for public deployment or for storing real customer financial data. Production hosting and a secure multi-user data model are still to be addressed.
