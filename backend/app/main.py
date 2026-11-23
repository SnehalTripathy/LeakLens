from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LeakLens API", version="0.1.0", description="Financial intelligence and anomaly analysis API.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["*"])

@app.get("/health", tags=["system"])
def health():
    return {"status":"ok","service":"leaklens-api","version":"0.1.0"}

@app.get("/api/v1", tags=["system"])
def api_root():
    return {"name":"LeakLens","available":["health"],"note":"Feature endpoints will be added as modules are implemented."}
