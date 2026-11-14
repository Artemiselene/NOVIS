from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import CORS_ORIGINS, API_PREFIX
from .db import Base, engine
from .routers import router
from .seed import seed

app = FastAPI(title="ASTRA MIND Health Extension", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(bind=engine)
seed()
app.include_router(router, prefix=API_PREFIX)

@app.get("/api/health")
def health():
    return {"status":"ok","service":"astra-mind-extension"}

@app.get(f"{API_PREFIX}/health")
def extension_health():
    return {"status":"ok","extension":"health-monitoring"}
