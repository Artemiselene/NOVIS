import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./astra_extension.db")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
API_PREFIX = "/api/extension"
