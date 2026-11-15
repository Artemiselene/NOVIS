import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./astra_extension.db")
DEFAULT_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8001,http://127.0.0.1:8001"
)
CORS_ORIGINS = [orig.strip() for orig in os.getenv("CORS_ORIGINS", DEFAULT_ORIGINS).split(",") if orig.strip()]
API_PREFIX = "/api/extension"
