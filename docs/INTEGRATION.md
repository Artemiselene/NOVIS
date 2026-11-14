# Integrating with an existing ASTRA MIND backend

This package runs standalone on port 8001 for demonstration. For host integration:

1. Copy `backend/app/models.py` extension models into the host's extension model package.
2. Use the host SQLAlchemy `Base` and session dependency rather than this package's standalone `Base` and `get_db`.
3. Keep `astronaut_id` and `mission_id` as references to the host-owned records; do not create duplicate core tables.
4. Include the extension router in the host FastAPI app:

```python
from extension.routers import router as extension_router
app.include_router(extension_router, prefix="/api/extension", tags=["ASTRA MIND extension"])
```

5. Add the extension models to host migrations and run migrations. Do not call `create_all()` against a production database.
6. Implement a telemetry adapter in `body_status` that queries the host's real reading and baseline services. Return `grey`, empty measurements and a clear explanation when no source data exists.
7. Point the React extension's `VITE_API_BASE_URL` to the host API.

The standalone app is intentionally separate so it can be tested without assumptions about the host application's ORM models or database schema.
