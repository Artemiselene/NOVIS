# ASTRA MIND – Health Monitoring Extension

A standalone, runnable extension scaffold for the ASTRA MIND prototype. It adds:
- Mission environment metadata (spacecraft, station, rover, planetary base)
- Clickable human-body health map with honest `grey` status when no source measurements exist
- Health routines and completion tracking
- Participation-based challenges and achievements
- Health education content

This package is deliberately isolated. It does **not** create duplicate Astronaut or Mission tables. `astronaut_id` and `mission_id` are external identifiers supplied by the host ASTRA MIND application.

## Requirements
- Python 3.11+
- Node.js 18+

## Run standalone

### Backend (PowerShell)
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

API docs: http://localhost:8001/docs

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

Set `VITE_API_BASE_URL=http://localhost:8001/api/extension` in `frontend/.env` if needed.

The standalone backend uses SQLite and demo identifiers. In the host application, configure a shared database/session and replace the standalone `get_db` dependency with the host's database dependency. See `docs/INTEGRATION.md`.

## Tests
```powershell
cd backend
pytest -q
```

## Data integrity
- The extension never fabricates live measurements.
- Body-system status is `grey` and measurements are empty unless telemetry is connected.
- All routine/challenge activity is participation-based; low stress scores are never rewarded.
- This is a research/demo tool, not a diagnostic or medical protocol.
