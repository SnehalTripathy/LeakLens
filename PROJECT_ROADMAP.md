# LeakLens — Master Project Roadmap

**Product:** Financial intelligence and hidden-loss detection  
**Version:** 1.0  
**Development policy:** Complete implementation and validation before any deployment. Netlify is reserved for the final frontend deployment step.

## Locked product decisions
- React + Vite + TypeScript frontend; Python + FastAPI backend.
- Brand system: Midnight Black `#0B0B0C`, Pure White `#FFFFFF`, Electric Lime `#C6F432`; functional accents Graphite `#202124`, Muted Sage `#8B8F82`, Amber `#FFB84D`.
- No sign-up, login, password, or email collection in v1.0.
- Local demo business and CSV/XLSX imports; SQLite is the current local persistence adapter.
- Multiple currencies are not converted or summed together. Analytics use the workspace's most common currency and the data-quality view reports currency counts.
- An anomaly is not automatically fraud; estimated exposure is not confirmed loss or guaranteed savings.
- The assistant is currently deterministic and ledger-grounded; no external LLM or API key is used.
- No deployment until P0–P10 acceptance criteria pass.

## Status key
- **Implemented:** code is in the repository.
- **CI checked:** latest GitHub Actions run for that commit passed.
- **Pending validation:** requires manual browser testing, real-world data, expanded tests, or a production decision.

## P0 — Foundation
- [x] GitHub repository, README, roadmap and ignore rules.
- [x] React + Vite + TypeScript application shell and responsive layouts.
- [x] Black/white/lime design system, hover/active/focus states and motion.
- [x] FastAPI service, versioned endpoints and local CORS configuration.
- [x] Local SQLite store, six-month deterministic demo ledger and alert/budget state.
- [x] GitHub Actions CI for backend tests, frontend tests and TypeScript/Vite build.
- [x] CI has reported green backend and frontend test/build jobs on commit `856d936`; later changes are being checked in subsequent runs.
- [ ] Local manual browser run on the user's machine.

## P1 — Data foundation
- [x] Canonical transaction schema and API validation.
- [x] CSV/XLS/XLSX ingestion with column auto-mapping.
- [x] Date, currency and debit/credit normalization.
- [x] Row-level validation errors, within-file duplicate checks and workspace deduplication.
- [x] 10 MB upload read limit and import row/error summary.
- [x] Data-quality report and reproducible six-month demo dataset.
- [x] Transaction create, edit, delete, search and filtering by type/category/date.
- [ ] Import preview/column mapping confirmation UI before committing rows.
- [ ] Real bank-export compatibility testing across several sample formats.

## P2 — Financial analytics
- [x] Revenue, expenses, net movement and profit-margin calculations.
- [x] Monthly revenue/expense aggregation and latest-period comparison.
- [x] Category and vendor spend analysis.
- [x] Recurring/fixed-cost heuristics and subscription pattern view.
- [x] Category budgets, month-to-date actuals, projected month-end and budget-overrun recommendations.
- [x] CSV ledger export and PDF financial summary.
- [ ] Accounting-grade P&L classification and configurable financial periods.
- [ ] Manual reconciliation against varied real-world business ledgers.

## P3 — Leak detection
- [x] Rule-based vendor payment spikes.
- [x] Category spend increases against recent monthly baselines.
- [x] Recurring vendor charge increases.
- [x] Vendor concentration and repeated small-charge signals.
- [x] Severity, evidence records, estimated exposure and alert review lifecycle.
- [x] Duplicate prevention and import duplicate reporting.
- [ ] Tune rule thresholds against labelled real business examples and measure false positives.

## P4 — ML anomaly intelligence
- [x] Feature engineering for amount, timing, vendor frequency and category frequency.
- [x] Isolation Forest and Local Outlier Factor comparison.
- [x] Relative percentile score breakdown and contextual explanations.
- [x] Minimum-sample guard and explicit non-fraud disclaimer.
- [ ] Train/evaluate a supervised classifier only after an adequately labelled dataset exists.
- [ ] Measure precision/recall and calibrate thresholds with reviewed outcomes.

## P5 — Predictive intelligence
- [x] Revenue and expense trend forecasts.
- [x] Up to three monthly forecast steps (approximately 30/60/90 days depending on calendar boundaries).
- [x] Held-out backtest MAE when enough history exists.
- [x] Indicative residual bands and insufficient-history state.
- [x] What-if revenue/expense/one-off-cost scenario calculator.
- [ ] Compare additional seasonal/naive forecasting baselines and publish per-metric backtest results.
- [ ] Validate forecast quality on multiple real business datasets.

## P6 — Business health and recommendations
- [x] Transparent weighted health score with six dimensions and explanations.
- [x] Signal-linked recommendations with evidence and estimated potential exposure.
- [x] Budget-aware cost-control recommendations.
- [x] Vendor dependency review recommendation.
- [ ] Persist and display historical health-score trends.
- [ ] Validate score weights with business domain examples; score is not an audit, credit or investment rating.

## P7 — Advanced intelligence
- [x] What-if financial simulator.
- [x] Vendor concentration and cost analysis.
- [x] Recurring payment/subscription inference.
- [x] Month-to-month financial comparison.
- [ ] Branch comparisons (requires branch identifiers in source data).
- [ ] External industry benchmarking (only after sourcing a credible benchmark dataset).
- [ ] Subscription usage/contract verification (requires usage or contract evidence).

## P8 — Alerts and explainability
- [x] In-app alert centre with open/reviewed/dismissed/resolved states.
- [x] Evidence inspection and contextual anomaly factors.
- [x] Deterministic assistant answers grounded in current ledger metrics.
- [x] Assistant displays evidence payloads and uses no external AI provider.
- [ ] Reopen alert action and alert history timeline.
- [ ] Optional LLM-based assistant only after explicit provider/key approval and data privacy review.

## P9 — React product experience
- [x] Navigation screens for overview, transactions, revenue, expenses, leak detection, ML anomalies, forecasting, health, recommendations, simulator, vendors, subscriptions, alerts, assistant, reports, data quality and settings.
- [x] Responsive sidebar/layouts for desktop and smaller screens.
- [x] Interactive chart tooltips, search, filters, import/export, transaction CRUD, budgets, alert actions and simulator.
- [x] Loading, empty, error/offline, success and notification states.
- [x] No sign-up, login or email workflow.
- [ ] Manual accessibility review, keyboard-only pass and contrast audit.
- [ ] Cross-browser and mobile-device visual QA.

## P10 — Quality and release readiness
- [x] Backend API tests for core endpoints, imports, deduplication, budgets, transaction CRUD, simulator, assistant and CSV/PDF reports.
- [x] Frontend component/navigation tests.
- [x] GitHub Actions backend/frontend CI pipeline.
- [x] Input limits, Pydantic validation, CORS allowlist setting, local secret examples, SQLite ignore rules and CSV formula-injection mitigation.
- [ ] Confirm green CI after the latest frontend/ML refinements.
- [ ] Review npm dependency audit results and remediate all high/critical advisories.
- [ ] Add full end-to-end tests for import → detect → review → report.
- [ ] Add automated security, accessibility and performance checks.
- [ ] Choose/implement production persistence (managed PostgreSQL or an approved alternative); current SQLite adapter is local-development focused.
- [ ] Complete final docs, screenshots, release notes and regression checklist.
- **Release gate:** Do not mark the project complete until the pending P10 checks are resolved.

## P11 — Deployment (last step only)
- [ ] User approves deployment architecture, including the unauthenticated data-access/privacy model.
- [ ] Decide whether the public instance is a read-only demo or a private single-workspace app. A public no-login API with persistent financial uploads would expose one shared workspace and is not safe to launch as-is.
- [ ] Deploy FastAPI backend to a Python-capable host with persistent database storage.
- [ ] Configure API URL, CORS, environment variables and backups.
- [ ] Deploy React frontend to Netlify only after P0–P10 are complete.
- [ ] Verify live workflows, data persistence, upload handling and secret/privacy boundaries.

## Credentials and permissions
No external API key is required for local v1 development. A database connection string/hosting access will only be needed when the production infrastructure is deliberately selected. Never commit secrets.

## Progress log
- 2026-11-23: Initialized the empty GitHub repository and implemented the first full v1 feature pass. CI passed on intermediate commits; final checks after the most recent changes are pending.
