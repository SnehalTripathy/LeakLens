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
- [x] Current code baseline has 20 backend tests passing; frontend tests and both dependency audits also pass in the verified runs.
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
- [ ] Accounting-grade chart-of-accounts classifications, accrual/cash accounting selection and configurable fiscal periods.
- [ ] Manual reconciliation against varied business ledgers and accountant-reviewed expected outputs.

## P3 — Leak detection
- [x] Vendor payment spikes against historical baseline.
- [x] Category spend increases against prior-month baselines.
- [x] Recurring vendor charge price increases.
- [x] Vendor concentration and repeated small-charge signals.
- [x] Possible duplicate vendor payments based on near-identical amounts within a three-day window.
- [x] Severity, evidence records, estimated exposure, alert workflow and duplicate import detection.
- [ ] Tune thresholds using labelled real business examples; measure false positives and false negatives before treating signals as operational controls.

## P4 — ML anomaly intelligence
- [x] Features for transaction amount, timing, vendor frequency and category frequency.
- [x] Isolation Forest and Local Outlier Factor comparison.
- [x] Relative percentile scores from both models and contextual explanations.
- [x] Minimum-sample guard and explicit non-fraud disclaimer.
- [ ] Supervised classification only after an adequately labelled dataset exists.
- [ ] Measure precision/recall and calibrate alert thresholds with human-reviewed outcomes.

## P5 — Predictive intelligence
- [x] Revenue and expense trend forecast baseline.
- [x] Up to three future monthly steps (roughly 30/60/90 days depending on calendar boundaries).
- [x] Held-out backtest MAE when enough months exist.
- [x] Indicative residual bands and insufficient-history state.
- [x] What-if revenue/expense/one-off-cost scenario simulator.
- [x] Linear trend model compared with last-observation naive baseline; revenue/expense MAE and held-out month counts are returned separately.
- [ ] Compare seasonal and additional forecasting methods; validate performance across multiple real business datasets.
- [ ] Validate forecast stability across multiple real businesses and seasonal periods.

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
- [ ] Branch comparisons (requires branch/location identifiers in uploaded data).
- [ ] External industry benchmarking (only after a credible, licensed benchmark dataset is selected).
- [ ] Subscription usage/contract verification (requires usage, invoice or contract evidence).

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
- [ ] Manual accessibility review, keyboard-only pass, contrast audit and reduced-motion review.
- [ ] Cross-browser and real mobile-device visual QA.

## P10 — Quality and release readiness
- [x] Backend suite: 21 passing tests covering service endpoints, imports, financial calculations, duplicate/spike signals, budgets, transaction CRUD, simulator, assistant, health/alert history, import → detect → review → export and CSV/PDF reports.
- [x] Frontend render/navigation tests.
- [x] GitHub Actions CI for frontend tests/build and backend tests.
- [x] npm audit clean on upgraded Vite/Vitest toolchain.
- [x] pip-audit clean after upgrading FastAPI, Starlette, python-multipart and the Starlette test client dependency.
- [x] Input limits, Pydantic validation, CORS allowlist, secret examples, SQLite ignore rules and CSV formula-injection mitigation.
- [x] Backend end-to-end integration test for import → detect → review → report.
- [x] Deterministic financial-engine unit tests and frontend navigation coverage for all workspace modules.
- [x] Local QA checklist and sample import ledger are documented.
- [ ] Add full browser end-to-end tests for import → detect → review → report.
- [ ] Add automated accessibility and performance checks.
- [ ] Review business-data privacy, backup/restore, retention and deletion policies.
- [ ] Select production persistence (managed PostgreSQL or an approved alternative); SQLite currently targets local development.
- [ ] Complete manual regression, screenshots, release notes and final technical documentation.
- **Release gate:** Do not mark v1.0 production-ready until the pending P10 checks are complete.

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
