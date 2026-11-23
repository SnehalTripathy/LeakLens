# LeakLens — Local QA Checklist

This checklist is for the final manual verification on the development machine. The automated backend/frontend checks run in GitHub Actions; this checklist covers the real browser, local persistence and responsive experience.

## 1. Start the app

**PowerShell terminal 1 — backend**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**PowerShell terminal 2 — frontend**
```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The header should say **Local API connected**. The first backend start creates `.data/leaklens.sqlite3` and seeds a six-month Northstar Studio demo ledger. No account or email is requested.

## 2. Transaction workflow
- [ ] Open **Transactions**; check that the demo rows load.
- [ ] Search for a vendor and a description.
- [ ] Filter by income/expense, category and date range; clear filters.
- [ ] Add a small test transaction, edit it, then delete it.
- [ ] Refresh the page and confirm the edited/deleted state persists.

## 3. Import workflow
- [ ] In **Transactions**, choose **Import CSV / Excel** and select `samples/sample-transactions.csv`.
- [ ] Check that preview shows 10 valid rows, the mapped date/amount/type columns, and a 10-row preview.
- [ ] Cancel once and confirm the transaction count has not changed.
- [ ] Preview the same file again and confirm import.
- [ ] Upload the same file a second time; it should report duplicates and insert zero additional rows.
- [ ] Check **Leak detection**. The sample data is intentionally synthetic and should surface possible duplicate payment and elevated-spend review signals for Sample Cloud Vendor.
- [ ] Create a tiny CSV with positive amounts but no `type` or debit/credit columns; confirm the preview refuses to guess whether rows are income or expenses.
- [ ] Check **Data quality** for currency/source counts and validation findings.

## 4. Intelligence workflow
- [ ] Open **Expense intelligence**; save a monthly category budget and check actual/projection status.
- [ ] Open **Revenue intelligence**; inspect revenue sources, counterparties and period comparison.
- [ ] Open **Anomaly intelligence**; inspect model scores and read the non-fraud disclaimer.
- [ ] Open **Forecasting**; compare trend MAE with the naive baseline and inspect the forecast bands.
- [ ] Open **Business health**; verify the dimensions and score explanation. Visit again on a later day to grow the history chart.
- [ ] Open **Recommendations**; confirm higher-priority recommendations appear first.
- [ ] Open **What-if simulator**; adjust revenue, expense and one-off cost assumptions.
- [ ] Open **Vendor intelligence** and **Subscription intelligence**; inspect vendor share and inferred recurrence caveats.

## 5. Alerts and reports
- [ ] In **Alerts centre**, mark a signal reviewed, dismiss it, resolve it and reopen it.
- [ ] Open its status history and confirm the actions appear oldest-to-newest.
- [ ] Ask the **AI assistant** a question about vendors, revenue or unusual expenses and inspect supporting evidence.
- [ ] Download the CSV transaction report and PDF summary; open both files and verify totals/content.

## 6. Accounting, branch and governance checks
- [ ] In **Settings**, select cash or accrual view and configure a non-calendar fiscal-year start.
- [ ] Import a file containing `service_date`, `branch`, `account_code` and `account_name`; verify service-date accrual views and branch totals.
- [ ] Add a category-to-account mapping and verify it applies to matching existing and newly imported rows.
- [ ] In **Subscription intelligence**, enter a known contract amount/cadence and compare it with inferred recurring charges. Treat differences as review prompts, not proof of overbilling.
- [ ] In **Alerts centre**, classify a review as confirmed issue, false positive or needs more evidence; inspect the qualified reviewed-subset metric and note that recall is unavailable without labelled unflagged transactions.

## 7. Persistence, responsive and privacy checks
- [ ] Stop and restart the backend; confirm imported transactions and alert/budget history remain.
- [ ] Use a disposable test workspace if testing deletion of every transaction. After clearing it, restart the backend; the Northstar demo data should not be reseeded.
- [ ] Check the layout at desktop, tablet and mobile widths; verify the sidebar, modals, charts and tables remain usable.
- [ ] Complete a keyboard-only pass through navigation, filters, modals and alert actions.
- [ ] Check reduced-motion behavior and keyboard focus visibility. CI runs axe WCAG checks and a mobile overflow smoke check; manual accessibility review is still required.
- [ ] For a disposable workspace only, set `LEAKLENS_ENABLE_LOCAL_ADMIN=true`, create a backup, restore it, and test confirmed deletion/manual retention. Return the setting to `false` afterward.
- [ ] Keep the API bound to localhost for local use. Do not expose this unauthenticated single-workspace backend to the public internet.

## Important
The sample CSV contains fabricated company/vendor names and figures. It exists only to exercise the import, duplicate-payment and spend-spike rules. Signals are candidates for human review, not confirmed fraud or loss.

Deployment remains deferred until the pending P10 checks and the no-login production privacy model are resolved.
