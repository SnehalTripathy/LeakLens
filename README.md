# LeakLens

**Find the leaks. Understand the losses. Protect your profits.**

LeakLens is a financial intelligence platform designed to help businesses understand financial performance, detect unusual spending, forecast financial risk, and act on explainable insights.

## Product principles

- No sign-up, login, or email collection in v1.0.
- Local-first development with a realistic demo dataset.
- Financial evidence must be traceable; suspected leaks are not presented as confirmed fraud or losses.
- Develop and test the complete product before any deployment.
- Frontend deployment is planned for Netlify only after final validation; the Python API will require separate hosting.

## Planned stack

- Frontend: React, Vite, TypeScript, Tailwind CSS, Framer Motion, Recharts, Lucide React, React Router
- Backend: Python, FastAPI, Pandas, NumPy, scikit-learn
- Data: CSV/XLSX import, validated demo data, PostgreSQL integration planned
- Quality: Pytest, Vitest, React Testing Library, Playwright

## Development status

The repository is being initialized. See [PROJECT_ROADMAP.md](./PROJECT_ROADMAP.md) for the complete delivery plan and acceptance criteria.

## Local development

Setup instructions will be added with the frontend and backend foundations. No API keys are required for the initial local version.

## Deployment policy

**Deployment is intentionally deferred.** Do not configure Netlify or production hosting until all planned modules, integrations, documentation, security checks, and end-to-end tests are complete.
