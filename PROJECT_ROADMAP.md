# LeakLens — Master Project Roadmap

**Version:** 1.0 | **Deployment:** last step only

## Locked decisions
- React + Vite + TypeScript frontend; Python + FastAPI backend.
- Palette: Midnight Black #0B0B0C, Pure White #FFFFFF, Electric Lime #C6F432. Functional accents: Graphite #202124, Muted Sage #8B8F82, Amber #FFB84D.
- Interactive hover, focus, pressed, loading, disabled and success states.
- No sign-up, login, password or email collection in v1.
- CSV/XLSX import, local demo data, validated calculations.
- Label evidence carefully: anomaly ≠ fraud; potential exposure ≠ confirmed loss.
- No production deployment until P0–P10 pass.

## P0 — Foundation
- [x] Initialize repository and README.
- [x] Lock architecture and visual direction.
- [ ] React/Vite/TypeScript shell and responsive design system.
- [ ] FastAPI skeleton and test baseline.
- [ ] Verify frontend build and backend tests locally.

## P1 — Data foundation
- [ ] Canonical transaction schema and validation.
- [ ] CSV/XLSX import, mapping, preview and error reporting.
- [ ] Date, currency, debit/credit normalization.
- [ ] Duplicate matching and data-quality report.
- [ ] Reproducible demo dataset.
**Acceptance:** deterministic imports; malformed rows explained; source records traceable.

## P2 — Financial analytics
- [ ] Revenue, expenses, net cash movement, operating profit and margin.
- [ ] Date-window comparisons and category/vendor aggregates.
- [ ] Fixed/variable and recurring costs; budget vs actual.
- [ ] Financial trend APIs and P&L summaries.
**Acceptance:** calculations reconcile against hand-verified fixtures.

## P3 — Leak detection
- [ ] Duplicate, spend spike, repeated-small-charge and recurring-charge rules.
- [ ] Baselines, thresholds, minimum sample sizes and evidence links.
- [ ] Severity, estimated exposure and review lifecycle.
**Acceptance:** every signal has evidence; estimated exposure is never called confirmed loss.

## P4 — ML anomaly intelligence
- [ ] Feature engineering and temporal context.
- [ ] Isolation Forest and Local Outlier Factor comparison.
- [ ] Supervised model only with suitable labels.
- [ ] Threshold calibration, precision/recall and explainability.
**Acceptance:** held-out evaluation and limitations disclosed.

## P5 — Predictive intelligence
- [ ] Revenue, expense and cash-flow forecast baselines.
- [ ] 30/60/90-day horizons only when history supports them.
- [ ] Backtesting against naive/seasonal baselines.
- [ ] Prediction intervals, error metrics and scenario cases.
**Acceptance:** insufficient-data state until minimum history criteria are satisfied.

## P6 — Business health and recommendations
- [ ] Transparent multi-dimensional health score.
- [ ] Score history and contributing factors.
- [ ] Evidence-ranked action recommendations and savings ranges.
**Acceptance:** no black-box score; each recommendation links to evidence and assumptions.

## P7 — Advanced intelligence
- [ ] What-if simulator for financial assumptions.
- [ ] Vendor concentration and price-change analysis.
- [ ] Subscription/recurring expense intelligence.
- [ ] Branch and period comparisons where supported.
- [ ] External benchmarks only with credible reference data.
**Acceptance:** assumptions visible; unsupported comparisons withheld.

## P8 — Alerts and explainability
- [ ] In-app alert centre and alert lifecycle.
- [ ] Explainable signal detail and model contribution views.
- [ ] Data-grounded conversational assistant (provider optional, only with approval).
- [ ] Prompt-injection and data-exfiltration safeguards if LLM added.
**Acceptance:** insight responses cite application evidence.

## P9 — Complete React experience
- [ ] All modules implemented, no placeholder pages.
- [ ] Responsive desktop/tablet/mobile and accessibility.
- [ ] Every control/filter/search/chart genuinely functional.
- [ ] Loading, empty, error, offline and success states.
- [ ] No authentication or email collection.
**Acceptance:** all visible controls work; no decorative pretend controls.

## P10 — Quality and release readiness
- [ ] PDF and CSV reporting.
- [ ] Unit, API, component, interaction and end-to-end tests.
- [ ] Upload/security/CORS/secrets/dependency audit.
- [ ] Performance, accessibility and responsive checks.
- [ ] Documentation, screenshots, environment examples and clean repo.
**Acceptance:** all critical tests pass and limitations are documented.

## P11 — Deployment (final step)
- [ ] User approves hosting choices and required accounts.
- [ ] Deploy FastAPI backend to Python-capable host.
- [ ] Configure API URL, CORS and environment variables.
- [ ] Deploy frontend to Netlify only after P0–P10.
- [ ] Live smoke tests and secret/privacy verification.

## External credentials
No external API key is needed for initial local development. Ask only when a future approved capability truly requires it. Never commit secrets.

## Progress log
- 2026-11-23: Repository created; roadmap and initial implementation work started. Local builds/tests must be run before claiming validation.