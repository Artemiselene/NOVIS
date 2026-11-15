# NOVIS — Crew Management Module & Rebranding Report
## Neural Onboard Vitality & Intelligence System (NOVIS v3.2)

**Date:** 2026-11-15  
**Platform:** NOVIS — Neural Onboard Vitality & Intelligence System  
**Tagline:** *Intelligent Crew Health. Adaptive Mission Readiness.*  
**Project Root:** `D:\astra-mind-extension\astra-mind-extension`  
**Frontend Build Status:** **SUCCESS** (`vite build` compiled in 428ms, 0 errors, 0 warnings)  
**Backend Test Status:** **120 passed, 0 failed** (100% pass rate in 1.92s)  
**Deliverable Status:** Production-Ready Interactive Crew Management Dashboard, Modals, Full CRUD, Safe Archival, and Complete Rebranding to NOVIS.

---

## 1. Executive Summary

This release accomplishes two primary mission milestones for the space-grade health intelligence platform:
1. **Global Rebranding to NOVIS (Neural Onboard Vitality & Intelligence System):**
   - Transformed the visible user identity from the prototype label "ASTRA MIND" to **NOVIS**.
   - Embedded the official brand identity, tagline (*"Intelligent Crew Health. Adaptive Mission Readiness."*), SVG brandmark ("N"), favicon, page titles, navigation headers, and metadata across the frontend and backend.
   - Preserved all underlying Python packages, database schemas, and API compatibility without architectural breakage.
2. **Interactive Crew Management Module:**
   - Introduced a dedicated **Crew Management** mission operations console accessible directly from the primary navigation sidebar.
   - Built a responsive 5-metric personnel summary dashboard (Total, Active Duty, Inactive/Archived, Calibrated Baselines, Uncalibrated).
   - Delivered multi-criteria filtering (search by name/callsign/ID, mission assignment, operational status, calibration state) with dual Grid and Table view modes.
   - Built interactive modals for **Registering New Astronauts** and **Editing Profiles** with SQLite persistence.
   - Implemented a **Safe Archival Policy** ensuring that historical PSI stress readings, calibration data, and physiological telemetry are protected against destructive deletion.
   - Synchronized active crew member selectors across Baseline Calibration and Astronaut Telemetry dashboards.

---

## 2. Platform Architecture & Endpoints

### 2.1 Backend Endpoints (`backend/app/routers_astronauts.py`)

All endpoints operate against the persistent SQLite database (`astra_extension.db`) with role-based access control and isolation:

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/extension/astronauts` | List all astronauts with optional mission/status filtering and calibration flags (`include_archived=True`) | Authenticated |
| `POST` | `/api/extension/astronauts` | Register a new astronaut; initializes uncalibrated `AstronautPsiBaseline` | Surgeon / Director |
| `GET` | `/api/extension/astronauts/{id}` | Retrieve individual astronaut profile with baseline parameters | Authenticated / Isolated |
| `PUT` | `/api/extension/astronauts/{id}` | Update astronaut metadata while preserving all historical PSI readings | Surgeon / Director |
| `DELETE` | `/api/extension/astronauts/{id}` | Safe delete or archive: automatically archives if historical records exist (`force=True` for clean removal) | Surgeon / Director |
| `POST` | `/api/extension/astronauts/{id}/archive` | Explicitly deactivates profile (`status="archived"`) | Surgeon / Director |
| `POST` | `/api/extension/astronauts/{id}/restore` | Restores archived astronaut to active duty (`status="active"`) | Surgeon / Director |

### 2.2 Schema Extensions (`backend/app/schemas_phase3.py`)

- **Status Enum Pattern:** Extended to support `"^(active|training|resting|grounded|archived|inactive)$"`.
- **Response Model:** Augmented `AstronautResponse` with:
  - `is_calibrated: bool` — indicates whether personal PSI baseline is set.
  - `baseline_stress: Optional[float]` — calibrated resting emotional load.

---

## 3. Frontend Features & Workflows

### 3.1 Crew Management Dashboard (`frontend/src/App.jsx`)

Located at navigation item `Crew Management` under `MISSION OPERATIONS`:
- **Personnel Metrics Row (5 Cards):**
  1. **Total Personnel:** Total count of registered crew members.
  2. **Active Duty:** Personnel available for flight tasks (`status === 'active'`).
  3. **Inactive / Archived:** Crew members in reserve or archived (`archived`, `inactive`, `grounded`).
  4. **Calibrated Baselines:** Astronauts who have verified 5-sample personal PSI baselines (`is_calibrated === true`).
  5. **Uncalibrated:** Personnel requiring personal baseline calibration before mission assignment.
- **Search & Filter Controls:**
  - Instant text search across astronaut full name, callsign, ID, and designation.
  - Dropdown filter by assigned Mission (e.g., Artemis Base Alpha, Ares Deep Space Transit, or Unassigned).
  - Dropdown filter by Operational Status (`active`, `training`, `resting`, `grounded`, `archived`, `inactive`).
  - Dropdown filter by Calibration Readiness (`Calibrated Baseline`, `Uncalibrated`).
  - View switcher: Toggle between responsive **Card Grid View** and high-density **Table View**.

### 3.2 Add & Edit Astronaut Modals (`AstronautFormModal`)

- **Create Mode (`+ Add Astronaut`):**
  - Interactive modal capturing Full Name, Callsign, Designation/Role, Operational Status, Mission Assignment, and optional baseline biometrics (Age, Resting HR, VO2 Max).
  - Validation ensures required fields are populated and numerical biometrics fall within physiological ranges.
  - Auto-initializes an uncalibrated baseline entry in `AstronautPsiBaseline`.
  - Dispatches `api.createAstronaut()`, updates SQLite, reloads the roster, and auto-selects the newly created astronaut.
- **Edit Mode:**
  - Pre-populates all existing profile attributes.
  - Dispatches `api.updateAstronaut()`.
  - Strictly preserves existing PSI baseline parameters, historical readings, telemetry streams, and mission assignments.

### 3.3 Safe Deletion & Archiving (`DeleteConfirmModal`)

- Displays astronaut details (Name, ID, Callsign) and presents a medical compliance warning:
  > **Flight Medical Data Compliance:**
  > If this crew member has historical PSI stress readings, calibration data, or physiological telemetry, permanent deletion will destroy vital health audit trails. NOVIS recommends **Archiving** instead.
- **Actions Provided:**
  1. **Archive Profile (Safe & Recommended):** Calls `api.archiveAstronaut(id)`, switching status to `"archived"`. Historical data is 100% preserved.
  2. **Permanently Delete:** Calls `api.deleteAstronaut(id, force=true)`. Permitted for test profiles or uncalibrated subjects without records.
  3. **1-Click Quick Archive / Restore:** Available directly on each card and table row for rapid roster management.

### 3.4 Operational Selector Synchronization

- In **Baseline Calibration** and **Astronaut Telemetry**:
  - Dropdown and button selectors are dynamically filtered to active personnel (`status !== 'archived'`).
  - If a Flight Surgeon explicitly navigates to an archived profile, the selector marks them as `[Archived]`.
  - Adding or modifying an astronaut immediately reflects across all navigation tabs and mission selectors.

---

## 4. Verification & Testing

### 4.1 Backend Test Suite (pytest)

Ran full regression and feature test suite:
```powershell
d:\astra-mind-extension\.venv\Scripts\python.exe -m pytest backend/tests -q
```
**Results:**
- `test_phase1_parity.py`: 34 passed
- `test_psi_db.py`: 12 passed
- `test_phase3_endpoints.py`: 41 passed (including `test_archive_and_restore_astronaut` and `test_safe_delete_or_archive_behavior`)
- `test_security_hardening.py`: 26 passed
- Existing backend tests: 7 passed
- **Total: 120 passed in 1.92s (100% pass rate)**

### 4.2 Frontend Compilation (Vite)

Ran full production build:
```powershell
npm run build
```
**Results:**
- `dist/index.html`: 0.72 kB
- `dist/assets/index-BOirOJK7.css`: 18.05 kB
- `dist/assets/index-B_DBW3lT.js`: 314.45 kB
- **Time:** Built in 428ms (0 errors, 0 warnings)

---

## 5. Summary of Modified & Untracked Files

- `frontend/src/App.jsx`: Rebranded to NOVIS, added `CrewManagementPage`, `AstronautFormModal`, `DeleteConfirmModal`, active astronaut filtering.
- `frontend/src/theme.css`: Added styles for crew metrics, cards, table, and modal forms.
- `frontend/src/api.js`: Added `deleteAstronaut`, `archiveAstronaut`, `restoreAstronaut`.
- `frontend/index.html`: Updated page title and SVG favicon to NOVIS.
- `backend/app/main.py`: Rebranded FastAPI application title, description, and module docstring.
- `backend/app/schemas_phase3.py`: Added `is_calibrated` and `baseline_stress` to `AstronautResponse`; updated status enum.
- `backend/app/routers_astronauts.py`: Added safe delete/archive logic, bulk baseline resolution, archive/restore routes.
- `backend/tests/test_phase3_endpoints.py`: Added archival and safe deletion tests.
- `docs/CREW_MANAGEMENT_IMPLEMENTATION_REPORT.md`: Comprehensive documentation.

---

## 6. Conclusion

The NOVIS Crew Management module is fully operational, meeting all enterprise spaceflight criteria: full CRUD capabilities, intuitive personnel metrics, safety-first archival policies, and complete visual rebranding to NOVIS.
