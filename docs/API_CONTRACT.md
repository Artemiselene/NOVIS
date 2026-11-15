# ASTRA MIND Extension — API Contract (Phase 3)

**Base URL:** `http://localhost:8001/api/extension`  
**WebSocket URL:** `ws://localhost:8001/api/extension/ws/telemetry`  
**Version:** 3.0.0

---

## 1. Authentication & Access Control

Authentication is enforced via header tokens. Unauthenticated demo requests inherit default mission operator (`flight_surgeon`) permissions in local development mode.

| Header | Description |
|---|---|
| `X-API-Key` | Plain API key string |
| `Authorization` | `Bearer <token>` |

### Configured Identities & Roles

| API Key / Token | Role | Scoped Astronaut ID | Permissions |
|---|---|---|---|
| `ASTRA-SURGEON-KEY-99` | `flight_surgeon` | Any | Full read/write access to all astronauts, telemetry, and baselines |
| `ASTRA-MISSION-CONTROL-2026` | `mission_director` | Any | Read/write access to missions, astronaut status, and telemetry summaries |
| `ASTRA-CREW-KEY-01` | `astronaut` | 1 | Restricted access strictly scoped to Astronaut 1 |
| `ASTRA-CREW-KEY-02` | `astronaut` | 2 | Restricted access strictly scoped to Astronaut 2 |

---

## 2. Astronaut Management Endpoints

### `GET /astronauts`
List all registered astronauts with optional query filtering.
- **Query Parameters:** `mission_id` (int, optional), `status_filter` (string, optional: `active`, `training`, `resting`, `grounded`)
- **Response `200 OK`:** `List[AstronautResponse]`

### `POST /astronauts`
Register a new astronaut into the mission flight roster.
- **Access:** Requires `flight_surgeon` or `mission_director`.
- **Request Body:**
  ```json
  {
    "name": "Dr. Jessica Meir",
    "callsign": "BioSpecialist",
    "role": "Flight Engineer",
    "status": "active",
    "current_mission_id": 1,
    "biometric_profile": { "resting_hr": 58, "blood_type": "O+" }
  }
  ```
- **Response `201 Created`:** `AstronautResponse`

### `GET /astronauts/{astronaut_id}`
Retrieve profile and mission assignment details for an astronaut.
- **Access:** Scoped to the astronaut's ID or `flight_surgeon`/`mission_director`.
- **Response `200 OK`:** `AstronautResponse`
- **Error `404 Not Found`:** Astronaut does not exist.

### `PUT /astronauts/{astronaut_id}`
Update operational status, callsign, or profile metadata.
- **Access:** Requires `flight_surgeon` or `mission_director`.
- **Response `200 OK`:** `AstronautResponse`

---

## 3. Mission Operations Endpoints

### `GET /missions`
List all missions with optional status filter (`planned`, `active`, `completed`, `contingency`).
- **Response `200 OK`:** `List[MissionResponse]`

### `POST /missions`
Create a new space exploration mission.
- **Access:** Requires `flight_surgeon` or `mission_director`.
- **Request Body:**
  ```json
  {
    "name": "Artemis Lunar Base Camp III",
    "code": "ART-03",
    "status": "planned",
    "description": "Long-duration lunar surface habitation trial"
  }
  ```
- **Response `201 Created`:** `MissionResponse`

### `GET /missions/{mission_id}`
Retrieve mission status, assigned crew count, and operational timeline.
- **Response `200 OK`:** `MissionResponse`

### `PUT /missions/{mission_id}`
Update mission timeline, description, or operational status.
- **Response `200 OK`:** `MissionResponse`

### `POST /missions/{mission_id}/assign`
Assign an astronaut to a mission.
- **Request Body:** `{"astronaut_id": 2}`
- **Response `200 OK`:** `{"success": true, "message": "...", "mission_id": 1, "astronaut_id": 2}`

### `GET /missions/{mission_id}/summary`
Retrieve consolidated behavioral and physiological monitoring summary for all crew on the mission.
- **Response `200 OK`:**
  ```json
  {
    "mission_id": 1,
    "name": "Artemis Base Alpha",
    "code": "ABA-01",
    "status": "active",
    "crew_count": 2,
    "crew": [
      {
        "astronaut_id": 1,
        "name": "Dr. Sarah Walker",
        "psi_status": "green",
        "smoothed_stress": 26.0,
        "brs": 12.4,
        "burnout_classification": "Low"
      }
    ]
  }
  ```

---

## 4. Physiological Telemetry Endpoints

> **Sensor Integrity Guarantee:** Unconnected sensors produce `null` values; no biometric measurements are fabricated. Real and simulated streams are strictly segregated using `is_simulated: bool`.

### `POST /telemetry`
Ingest physiological measurements from wearable or simulated streams.
- **Request Body:**
  ```json
  {
    "astronaut_id": 1,
    "mission_id": 1,
    "heart_rate": 72.0,
    "spo2": 98.5,
    "body_temperature": 36.8,
    "respiration_rate": 14.0,
    "sleep_hours": 7.5,
    "sleep_quality": 88.0,
    "activity_level": 4.2,
    "workload_score": 5.0,
    "is_simulated": false,
    "source_device": "BioHarness-Alpha"
  }
  ```
- **Response `201 Created`:** `PhysiologicalResponse`
- **Validation:** Heart rate `[30, 240]`, SpO2 `[50, 100]`, Body temp `[30, 45]`. Invalid values return `422 Unprocessable Entity`.

### `GET /telemetry/astronaut/{astronaut_id}/latest`
Retrieve the latest physiological telemetry frame for an astronaut.
- **Response `200 OK`:** `PhysiologicalResponse` (or `null` if none recorded).

### `GET /telemetry/astronaut/{astronaut_id}/history`
Retrieve time-windowed physiological history.
- **Query Parameters:** `hours` (int, default: 24), `limit` (int, default: 100)
- **Response `200 OK`:** `List[PhysiologicalResponse]`

---

## 5. Psychological Stress Index (PSI) Endpoints

> **Ethical & Methodological Notice:** PSI is an experimental behavioral proxy signal derived from voluntary facial tracking. It is NOT interpreted as definitive psychological stress, is kept separate from physiological exertion, and does not constitute a clinical diagnosis.

### `POST /psi/calibrate/{astronaut_id}`
Submit 5-pose neutral calibration data to establish astronaut personal baseline with IQR outlier trimming.
- **Request Body:**
  ```json
  {
    "poses": [
      { "photo_number": 1, "pose_name": "neutral_forward", "valid": true, "emotions": { "neutral": 0.85, "happy": 0.15 } },
      { "photo_number": 2, "pose_name": "neutral_tilt_left", "valid": true, "emotions": { "neutral": 0.90, "happy": 0.10 } },
      { "photo_number": 3, "pose_name": "neutral_tilt_right", "valid": true, "emotions": { "neutral": 0.88, "happy": 0.12 } },
      { "photo_number": 4, "pose_name": "neutral_up", "valid": true, "emotions": { "neutral": 0.82, "happy": 0.18 } },
      { "photo_number": 5, "pose_name": "neutral_down", "valid": true, "emotions": { "neutral": 0.86, "happy": 0.14 } }
    ]
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "baseline_stress": 21.4,
    "baseline_sigma": 3.8,
    "optimal_range": [15.0, 32.0],
    "natural_emotions": { "angry": 0.0, "sad": 0.0, "fear": 0.0 },
    "valid_photos": 5
  }
  ```

### `POST /psi/calibrate/{astronaut_id}/analyze-frame`
Transient in-memory analysis of a single live webcam frame for personal baseline calibration. Evaluates face detection, bounding box, illumination level, and resting emotion distribution. Raw imagery is never persisted to disk.
- **Request Body:**
  ```json
  {
    "frame_base64": "<base64_data_url>",
    "pose_name": "neutral_sample_1",
    "photo_number": 1
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "valid": true,
    "face_detected": true,
    "face_box": { "x": 180, "y": 120, "w": 280, "h": 280 },
    "quality": "good",
    "lighting": "adequate",
    "mean_brightness": 124.6,
    "emotions": { "neutral": 0.91, "happy": 0.09 },
    "dominant_emotion": "neutral",
    "calculated_stress": 22.1,
    "pose_name": "neutral_sample_1",
    "photo_number": 1
  }
  ```

### `POST /psi/calibrate/{astronaut_id}/benchmark`
Execute standardized 5-pose demonstration calibration when physical webcam is unavailable. Applies identical IQR outlier trimming and persists calibrated baseline to database.
- **Response `200 OK`:** `CalibrationResponse`

### `GET /psi/baseline/{astronaut_id}`
Retrieve personal baseline parameters for an astronaut.
- **Response `200 OK`:** `PsiBaselineResponse`

### `POST /psi/process-frame/{astronaut_id}`
Ingest a base64-encoded video/camera frame, run emotion detection, calculate smoothed PSI, and persist the reading.
- **Request Body:**
  ```json
  {
    "frame_base64": "<base64_string>",
    "task_complexity": 5.0,
    "mission_id": 1
  }
  ```
- **Response `200 OK`:** Full reading object with `face_box`, `expression` metrics, `smoothed_stress`, and `risk_level`.

### `POST /psi/readings/{astronaut_id}`
Directly persist pre-calculated stress readings.
- **Request Body:**
  ```json
  {
    "raw_stress": 32.5,
    "smoothed_stress": 30.0,
    "dominant_emotion": "neutral",
    "emotion_vector": { "angry": 0.05, "disgust": 0.02, "fear": 0.03, "happy": 0.10, "sad": 0.05, "surprise": 0.05, "neutral": 0.70 },
    "motion_level": 1.2,
    "task_complexity": 6.0,
    "mission_id": 1
  }
  ```
- **Response `201 Created`:** `PsiReadingResponse`

### `GET /psi/readings/{astronaut_id}/latest`
Retrieve the latest PSI telemetry, status categorization (`green`, `yellow`, `red`, `grey`), and baseline comparison.
- **Response `200 OK`:**
  ```json
  {
    "astronaut_id": 1,
    "status": "green",
    "status_label": "nominal",
    "latest_reading": { "raw_stress": 32.5, "smoothed_stress": 30.0, "stress_deviation": 5.0, "risk_level": "low" },
    "baseline": { "baseline_stress": 25.0, "optimal_range": [15.0, 35.0], "stress_threshold": 70.0 }
  }
  ```

### `GET /psi/readings/{astronaut_id}/history`
Retrieve historical PSI readings.
- **Query Parameters:** `hours` (default: 24), `limit` (default: 100)
- **Response `200 OK`:** `List[Dict[str, Any]]`

### `GET /psi/analytics/chronic/{astronaut_id}`
7-day rolling chronic stress pattern detection.
- **Response `200 OK`:** `ChronicResponse` (`is_chronic: bool`, `daily_averages: List`, `threshold: float`)

### `GET /psi/analytics/burnout/{astronaut_id}`
Burnout Risk Score (BRS) combining 7-day average stress, variability, and task demand.
- **Response `200 OK`:** `BurnoutResponse` (`brs: float`, `classification: str`, `weekly_avg: float`, `variability: float`)

---

## 6. Health Intelligence Dashboard Endpoints

### `GET /dashboard/astronaut/{astronaut_id}`
Aggregated overview combining astronaut demographics, mission status, latest PSI, BRS, physiological vitals, recovery index, and synthesized health alerts.
- **Response `200 OK`:**
  ```json
  {
    "astronaut": { "id": 1, "name": "Dr. Sarah Walker", "callsign": "VanguardLead", "role": "Commander", "status": "active" },
    "mission": { "id": 1, "name": "Artemis Base Alpha", "code": "ABA-01", "status": "active" },
    "psi_status": { "status": "green", "status_label": "nominal", "latest_reading": { "smoothed_stress": 26.0 } },
    "physiological": { "available": true, "heart_rate": 65.0, "spo2": 99.0, "sleep_hours": 8.0 },
    "recovery": { "recovery_index": 82.5, "readiness_classification": "optimal", "contributing_factors": { "sleep_score": 100.0, "stress_moderation": 74.0 } },
    "alerts": []
  }
  ```

### `GET /dashboard/mission/{mission_id}`
Commander overview summarizing all crew members assigned to a mission, average crew behavioral stress, and active mission-wide health alerts.
- **Response `200 OK`:**
  ```json
  {
    "mission": { "id": 1, "name": "Artemis Base Alpha", "code": "ABA-01", "status": "active" },
    "crew_count": 2,
    "crew_behavioral_average_stress": 25.5,
    "crew": [ ... ],
    "active_alerts": [ ... ]
  }
  ```

---

## 7. Real-Time WebSocket Streaming

**Endpoint:** `ws://localhost:8001/api/extension/ws/telemetry`

### Connection & Control Commands

Clients may send JSON control messages over the WebSocket connection:

| Command Action | Payload | Purpose | Server Response |
|---|---|---|---|
| `subscribe_astronaut` | `{"action": "subscribe_astronaut", "astronaut_id": 1}` | Subscribe to an individual astronaut's stream | `{"type": "subscribed", "channel": "astronaut", "id": 1}` |
| `unsubscribe_astronaut` | `{"action": "unsubscribe_astronaut", "astronaut_id": 1}` | Unsubscribe from astronaut stream | `{"type": "unsubscribed", "channel": "astronaut", "id": 1}` |
| `subscribe_mission` | `{"action": "subscribe_mission", "mission_id": 1}` | Subscribe to all crew updates on a mission | `{"type": "subscribed", "channel": "mission", "id": 1}` |
| `unsubscribe_mission` | `{"action": "unsubscribe_mission", "mission_id": 1}` | Unsubscribe from mission stream | `{"type": "unsubscribed", "channel": "mission", "id": 1}` |
| `ping` | `{"action": "ping"}` | Heartbeat check | `{"type": "pong"}` |

### Live Server Broadcast Messages

When telemetry or PSI frames are ingested via REST, the server broadcasts to subscribed WebSockets:
- `psi_reading`: Direct reading ingestion
- `psi_frame_reading`: Frame processed via webcam/video feed
- `physiological_telemetry`: Heart rate, SpO2, sleep, or exertion vitals
- `crew_psi_reading` / `crew_physiological_telemetry`: Mission-wide broadcasts
