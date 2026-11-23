# LeakLens — Master Project Roadmap

**Product:** Financial intelligence and hidden-loss detection platform  
**Version:** 1.0  
**Development policy:** Complete implementation and validation before deployment. Netlify is reserved for the final frontend deployment step.

## Locked product decisions
- React + Vite + TypeScript frontend; Python + FastAPI backend.
- Brand system: Midnight Black `#0B0B0C`, Pure White `#FFFFFF`, Electric Lime `#C6F432`; functional accents Graphite `#202124`, Muted Sage `#8B8F82`, Amber `#FFB84D`.
- No sign-up, login, password, or email collection in v1.0.
- Local demo business and CSV/XLS/XLSX imports; SQLite is the current local persistence adapter.
- Multiple currencies are not converted or summed together. Analytics use the workspace's most common currency and the UI warns when more than one currency is present.
- An anomaly is not automatically fraud; estimated exposure is not confirmed loss or guaranteed savings.
- The assistant is deterministic and ledger-grounded; no external LLM or API key is used.
- No deployment until P0–P10 acceptance criteria pass.

## Status key
- **Implemented:** code is committed.
- **CI checked:** GitHub Actions passed for the referenced dependency/feature baseline.
- **Pending validation:** needs manual browser QA, varied real-world data, additional evaluation, production architecture or explicit user approval.

## P0 — Foundation
- [x] Initialize repository, README, roadmap and ignore rules.
- [x] React + Vite + TypeScript frontend and responsive application shell.
- [x] Black/white/lime design system, typography, hover/active/focus states, motion and mobile navigation.
- [x] FastAPI service, versioned API, configurable CORS and OpenAPI documentation.
- [x] SQLite local store, reproducible six-month demo ledger, budget storage and alert/health history.
- [x] GitHub Actions workflow for backend tests, frontend tests, build and dependency audits.
- [x] CI passed on dependency baseline `71c0b065`: Python tests, Python dependency audit, frontend tests, TypeScript/Vite production build and npm audit.
- [x] Current backend suite has 35 passing tests in the isolated development verification run; the latest GitHub Actions run after the new release job is the CI gate for the final integrated commit.
- [ ] Run the app locally in a browser and complete manual visual QA.

## P1 — Data foundation
- [x] Canonical transaction schema and API validation.
- [x] CSV/XLS/XLSX ingestion with automatic column mapping.
- [x] Date, currency, debit/credit and transaction-direction normalization.
- [x] Reject ambiguous positive-only amount files when income/expense direction cannot be determined.
- [x] Row-level validation errors, within-file duplicate detection and workspace fingerprint deduplication.
- [x] Non-destructive import preview with mapped columns, first-row sample, invalid rows and duplicate counts; explicit confirmation before insert.
- [x] 10 MB import limit and six-month reproducible demo ledger.
- [x] Data-quality view and source/currency counts.
- [x] Transaction create, edit, delete, search, type/category/date filters.
- [ ] Test compatibility against a broader set of real bank/accounting exports (headers, date formats, debit/credit conventions and encodings).

## P2 — Financial analytics
- [x] Revenue, expenses, net movement and profit-margin calculations.
- [x] Monthly revenue/expense aggregation and latest-month comparison.
- [x] Category, vendor and revenue-source analysis.
- [x] Recurring/fixed-cost heuristics and subscription pattern view.
- [x] Category budgets, month-to-date actuals, projected month-end and budget-overrun recommendations.
- [x] CSV transaction export and PDF financial summary/monthly trend report.
- [x] Configurable category-to-chart-of-accounts mappings; imported account codes/names are retained, unmapped rows stay visible, and mappings apply to existing and future transactions.
- [x] Cash-basis or service-date accrual-view selection, plus configurable fiscal-year start month and fiscal-year summary endpoint. Accrual view falls back to transaction date when no service date is supplied.
- [ ] Accountant review and reconciliation against varied real-world ledgers; the app does not certify accounting classifications or audited statements.
- [ ] Manual reconciliation against varied business ledgers and accountant-reviewed expected outputs.

## P3 — Leak detection
- [x] Vendor payment spikes against historical baseline.
- [x] Category spend increases against prior-month baselines.
- [x] Recurring vendor charge price increases.
- [x] Vendor concentration and repeated small-charge signals.
- [x] Possible duplicate vendor payments based on near-identical amounts within a three-day window.
- [x] Severity, evidence records, estimated exposure, alert workflow and duplicate import detection.
- [x] Capture human classifications for alert candidates (confirmed issue, false positive, needs more evidence), persist review notes, and report a clearly qualified reviewed-subset positive rate.
- [ ] Tune thresholds using representative labelled business examples and measure system-wide false positives/negatives. Reviewed-subset positive rate is selection-biased; UCI Online Retail II has no fraud labels and is not used to claim fraud-detection performance.

## P4 — ML anomaly intelligence
- [x] Features for transaction amount, timing, vendor frequency and category frequency.
- [x] Isolation Forest and Local Outlier Factor comparison.
- [x] Relative percentile scores from both models and contextual explanations.
- [x] Minimum-sample guard and explicit non-fraud disclaimer.
- [ ] Supervised classification only after an adequately labelled dataset exists.
- [x] Add persisted human review outcomes and a reviewed-subset precision proxy; recall is explicitly unavailable without independently labelled unflagged transactions.
- [ ] Measure representative precision/recall and calibrate alert thresholds with independently human-reviewed flagged and unflagged outcomes.

## P5 — Predictive intelligence
- [x] Revenue and expense trend forecast baseline.
- [x] Up to three future monthly steps (roughly 30/60/90 days depending on calendar boundaries).
- [x] Held-out backtest MAE when enough months exist.
- [x] Indicative residual bands and insufficient-history state.
- [x] What-if revenue/expense/one-off-cost scenario simulator.
- [x] Compare linear trend, last-value, trailing-three-month and 12-month seasonal-naive models on a real public retail dataset using expanding-window rolling-origin backtests.
- [x] Add conditional seasonal-naive eligibility to LeakLens forecasts (requires at least 24 contiguous months); select revenue and expense methods separately by held-out WAPE and use selected-model residuals for indicative bands.
- [x] Validate pipeline against full UCI Online Retail II workbook (1,067,371 source lines; 1,061,164 retained; 25 calendar months); seasonal naive achieved 16.95% WAPE versus 39.86% last-value, 41.57% moving average and 42.97% linear trend.
- [ ] Validate forecast stability across multiple real businesses and seasonal periods; this public benchmark is one retailer only.

## P6 — Business health and recommendations
- [x] Transparent weighted health score with six explained dimensions.
- [x] Daily score snapshots and history chart (history starts when the first snapshot is recorded; no historical scores are fabricated).
- [x] Signal-linked and budget-aware recommendations with evidence and estimated impact.
- [x] Vendor dependency review recommendation.
- [ ] Validate score weights and category thresholds with real business examples. The score is not an audit, credit or investment rating.

## P7 — Advanced intelligence
- [x] What-if financial simulator.
- [x] Vendor concentration and cost analysis.
- [x] Recurring payment/subscription inference.
- [x] Month-to-month financial comparison.
- [x] Add customer-country revenue aggregation on UCI Online Retail II as a geography benchmark; explicitly not presented as branch comparisons.
- [x] Add branch/location fields to import and transaction schema, branch/currency comparison API and Settings UI; only explicitly assigned branches are included.
- [ ] Validate branch comparison with genuine multi-branch business ledgers.
- [ ] External industry benchmarking (only after a credible, licensed benchmark dataset is selected).
- [x] Add user-entered subscription contract records and compare expected billing cadence/amount with ledger-inferred recurring charges, with explicit evidence caveats.
- [ ] Verify actual usage, invoice authenticity and contract entitlement only when those source records are supplied.

## P8 — Alerts and explainability
- [x] In-app alert centre with open/reviewed/dismissed/resolved states.
- [x] Mark reviewed, dismiss, resolve and reopen actions.
- [x] Persistent status history/audit trail for alert changes.
- [x] Evidence inspection and contextual anomaly factors.
- [x] Deterministic assistant answers grounded in current ledger metrics with evidence payloads.
- [ ] Optional LLM assistant only after explicit provider/key approval, data-retention review and safeguards; not required for the current v1 implementation.

## P9 — React product experience
- [x] Navigation screens for overview, transactions, revenue, expenses, leak detection, ML anomalies, forecasting, health, recommendations, simulator, vendors, subscriptions, alerts, assistant, reports, data quality and settings.
- [x] Responsive desktop/tablet/mobile layouts and compact navigation.
- [x] Interactive charts, search, date/category/type filters, import preview/confirmation, transaction CRUD, budgets, alert actions, simulator and downloads.
- [x] Loading, empty, API-offline, error, success, confirmation and notification states.
- [x] No sign-up, login or email workflow.
- [x] Add reduced-motion CSS support, visible keyboard focus styles, and automated axe WCAG checks in the browser-release workflow.
- [ ] Complete manual accessibility review, full keyboard-only pass and human contrast review.
- [ ] Cross-browser and real mobile-device visual QA.

## P10 — Quality and release readiness
- [x] Backend suite: 35 passing tests in the latest isolated verification run, covering service endpoints, imports, financial calculations, duplicate/spike signals, budgets, transaction CRUD, simulator, assistant, health/alert history, import → detect → review → export, public dataset processing, seasonal forecasting, account mappings, branch/fiscal settings, review feedback, contract comparison, privacy and backup/restore.
- [x] Frontend render/navigation tests.
- [x] GitHub Actions CI for frontend tests/build and backend tests.
- [x] npm audit clean on upgraded Vite/Vitest toolchain.
- [x] pip-audit clean after upgrading FastAPI, Starlette, python-multipart and the Starlette test client dependency.
- [x] Input limits, Pydantic validation, CORS allowlist, secret examples, SQLite ignore rules and CSV formula-injection mitigation.
- [x] Backend end-to-end integration test for import → detect → review → report.
- [x] Deterministic financial-engine unit tests and frontend navigation coverage for all workspace modules.
- [x] Local QA checklist and sample import ledger are documented.
- [x] Add unit coverage for public-dataset cleaning, cancellation/refund arithmetic, country/month/invoice aggregation and rolling-origin forecast evaluation.
- [x] Run full UCI dataset pipeline and preserve aggregated benchmark result artifacts; raw workbook and customer/invoice-level records are excluded from Git.
- [x] Add automated tests for public-dataset processing and seasonal model eligibility/selection (15 focused engine + dataset tests passed in the isolated research environment).
- [x] Add Playwright browser workflow for import preview/confirmation → leak detection → alert review → CSV report download.
- [x] Add automated axe WCAG scan, keyboard-focus check, mobile overflow check and page-load performance budget to the browser-release CI job.
- [x] Add privacy summary endpoint, API security headers, local-only backup/restore, explicit-confirmation data deletion and manually applied retention policy. Local admin routes are disabled by default and loopback-gated.
- [ ] Complete human privacy review and approve a real retention schedule; the retention setting is not automatically scheduled.
- [ ] Select production persistence (managed PostgreSQL or an approved alternative); SQLite currently targets local development.
- [ ] Complete manual regression, screenshots, release notes and final technical documentation.
- **Release gate:** Do not mark v1.0 production-ready until the pending P10 checks are complete.

## Public dataset research reference
- UCI Online Retail II (Chen, 2012), DOI 10.24432/C5CG6D, CC BY 4.0. Full workbook processed: 1,067,371 source invoice lines; 1,061,164 retained; 25 months; 43 countries; 48,369 invoices. See `docs/PUBLIC_DATASET_STUDY.md` and `docs/UCI_ONLINE_RETAIL_II_RESULTS.md`.
- Scope boundary: sales, refunds, invoice/customer/country data only; no expenses, supplier costs, branch identifiers or fraud labels.

## P11 — Deployment (last step only)
- [ ] User approves deployment architecture and the no-login data-access model.
- [ ] Choose between a read-only public demo or a private/isolated workspace model. A public unauthenticated API with persistent financial uploads would expose one shared workspace and is unsafe to launch as-is.
- [ ] Deploy FastAPI backend to Python-capable hosting with persistent database storage.
- [ ] Configure API URL, CORS, environment variables, backups and monitoring.
- [ ] Deploy React frontend to Netlify only after P0–P10 are complete.
- [ ] Verify live workflows, persistence, uploads and privacy boundaries.

## Credentials and permissions
No third-party API key is required for the current local feature set. A production database URL and hosting access will be needed only after the infrastructure/privacy model is approved. Never commit credentials.

## Progress log
- 2026-11-23: Implemented the core v1 feature set, import preview, sample data, duplicate-payment signals, alert/health histories, naive forecast benchmark and local seed persistence guard. Backend suite reached 20 passing tests; frontend tests/build and strict npm/Python audits passed. Manual browser/accessibility QA, real-world model tuning, production persistence and the no-login deployment decision remain.

- 2026-11-23: Downloaded and processed the full UCI Online Retail II workbook; committed aggregated outputs only. Seasonal naive achieved 16.95% WAPE on a 13-origin/36-prediction rolling-origin backtest. Added rolling-origin model selection to the app, independently for revenue and expenses.
- 2026-11-23: Added chart-of-accounts mapping, cash/accrual view, fiscal-year settings, branch comparison, subscription contract comparison, alert feedback capture, reviewed-subset calibration metric, local backup/restore, confirmed deletion, manual retention execution, security headers, reduced-motion support and a Playwright/axe/performance browser-release job. Backend verification reached 35 passing tests. The final integrated GitHub Actions run is the remaining automated CI gate; manual browser/accessibility review and production database/privacy architecture remain user review items. Raw UCI workbook and customer/invoice-level rows were not committed.
