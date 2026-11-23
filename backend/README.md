# LeakLens API

## Local setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health  
OpenAPI: http://localhost:8000/docs

Run tests with `pytest`. No API keys are needed for the initial local API.
