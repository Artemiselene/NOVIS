"""
ASTRA MIND — Phase 3 Endpoints & Telemetry Integration Test Suite
=================================================================
Validates authorized workflows:
1. Astronaut Management CRUD & role-based isolation.
2. Mission Operations, Crew Assignment & Summaries.
3. Physiological Telemetry Ingestion, Validation & Segregation.
4. PSI Baseline Calibration, Direct Readings, Frame Ingestion & Analytics.
5. Health Intelligence Dashboard Aggregations (Astronaut & Mission).
6. Security (Authentication, Authorization, Data Isolation).
7. WebSocket real-time subscription & telemetry dispatch.
"""

import base64
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

SURGEON_HEADERS = {"X-API-Key": "ASTRA-SURGEON-KEY-99"}
MISSION_CONTROL_HEADERS = {"X-API-Key": "ASTRA-MISSION-CONTROL-2026"}
CREW_1_HEADERS = {"X-API-Key": "ASTRA-CREW-KEY-01"}
CREW_2_HEADERS = {"X-API-Key": "ASTRA-CREW-KEY-02"}


# =============================================================================
# 1. ASTRONAUT MANAGEMENT TESTS
# =============================================================================
class TestAstronautEndpoints:
    def test_list_astronauts(self, client: TestClient):
        r = client.get("/api/extension/astronauts", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Seed has astronaut 1 and 2

    def test_get_astronaut_success(self, client: TestClient):
        r = client.get("/api/extension/astronauts/1", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert "name" in data
        assert "role" in data

    def test_get_astronaut_not_found(self, client: TestClient):
        r = client.get("/api/extension/astronauts/9999", headers=SURGEON_HEADERS)
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_create_astronaut_success(self, client: TestClient):
        payload = {
            "name": "Dr. Jessica Meir",
            "callsign": "BioSpecialist",
            "role": "Flight Engineer",
            "status": "active",
            "current_mission_id": 1,
            "biometric_profile": {"blood_type": "O+", "resting_hr": 58},
        }
        r = client.post(
            "/api/extension/astronauts",
            json=payload,
            headers=SURGEON_HEADERS,
        )
        assert r.status_code == 201
        created = r.json()
        assert created["id"] > 2
        assert created["name"] == "Dr. Jessica Meir"
        assert created["current_mission_id"] == 1

    def test_create_astronaut_invalid_mission(self, client: TestClient):
        payload = {
            "name": "Phantom Astronaut",
            "role": "Mission Specialist",
            "current_mission_id": 99999,
        }
        r = client.post(
            "/api/extension/astronauts",
            json=payload,
            headers=SURGEON_HEADERS,
        )
        assert r.status_code == 404
        assert "mission not found" in r.json()["detail"].lower()

    def test_update_astronaut(self, client: TestClient):
        update_payload = {"status": "resting", "callsign": "HorizonLead"}
        r = client.put(
            "/api/extension/astronauts/1",
            json=update_payload,
            headers=SURGEON_HEADERS,
        )
        assert r.status_code == 200
        updated = r.json()
        assert updated["status"] == "resting"
        assert updated["callsign"] == "HorizonLead"

    def test_archive_and_restore_astronaut(self, client: TestClient):
        # Create candidate astronaut
        create_res = client.post(
            "/api/extension/astronauts",
            json={"name": "Archive Test Candidate", "callsign": "Tester", "role": "Specialist", "status": "active"},
            headers=SURGEON_HEADERS,
        )
        assert create_res.status_code == 201
        astro_id = create_res.json()["id"]

        # Archive
        r_arch = client.post(f"/api/extension/astronauts/{astro_id}/archive", headers=SURGEON_HEADERS)
        assert r_arch.status_code == 200
        assert r_arch.json()["status"] == "archived"

        # Restore
        r_rest = client.post(f"/api/extension/astronauts/{astro_id}/restore", headers=SURGEON_HEADERS)
        assert r_rest.status_code == 200
        assert r_rest.json()["status"] == "active"

    def test_safe_delete_or_archive_behavior(self, client: TestClient):
        # Astronaut 1 has historical baseline/records -> safe archive instead of destruction
        r_del = client.delete("/api/extension/astronauts/1", headers=SURGEON_HEADERS)
        assert r_del.status_code == 200
        data = r_del.json()
        assert data["action"] == "archived"
        assert data["has_history"] is True

        # Clean new astronaut without history can be deleted
        r_new = client.post(
            "/api/extension/astronauts",
            json={"name": "Ephemeral Subject", "role": "Trainee", "status": "active"},
            headers=SURGEON_HEADERS,
        )
        assert r_new.status_code == 201
        new_id = r_new.json()["id"]

        r_clean_del = client.delete(f"/api/extension/astronauts/{new_id}?force=true", headers=SURGEON_HEADERS)
        assert r_clean_del.status_code == 200
        assert r_clean_del.json()["action"] == "deleted"


# =============================================================================
# 2. MISSION MANAGEMENT TESTS
# =============================================================================
class TestMissionEndpoints:
    def test_list_missions(self, client: TestClient):
        r = client.get("/api/extension/missions", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_mission_details(self, client: TestClient):
        r = client.get("/api/extension/missions/1", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert "crew_count" in data
        assert data["code"] == "ABA-01"

    def test_get_mission_not_found(self, client: TestClient):
        r = client.get("/api/extension/missions/9999", headers=SURGEON_HEADERS)
        assert r.status_code == 404

    def test_create_mission_success(self, client: TestClient):
        payload = {
            "name": "Artemis Lunar Base Camp III",
            "code": "ART-03",
            "status": "planned",
            "description": "Long-duration lunar surface habitation trial",
        }
        r = client.post(
            "/api/extension/missions",
            json=payload,
            headers=MISSION_CONTROL_HEADERS,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == "ART-03"

    def test_assign_astronaut_to_mission(self, client: TestClient):
        r = client.post(
            "/api/extension/missions/1/assign",
            json={"astronaut_id": 2},
            headers=MISSION_CONTROL_HEADERS,
        )
        assert r.status_code == 200
        res = r.json()
        assert res["success"] is True
        assert res["astronaut_id"] == 2

    def test_assign_invalid_astronaut(self, client: TestClient):
        r = client.post(
            "/api/extension/missions/1/assign",
            json={"astronaut_id": 9999},
            headers=MISSION_CONTROL_HEADERS,
        )
        assert r.status_code == 404

    def test_mission_summary(self, client: TestClient):
        r = client.get("/api/extension/missions/1/summary", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        summary = r.json()
        assert summary["mission_id"] == 1
        assert "crew" in summary
        assert "crew_count" in summary


# =============================================================================
# 3. PHYSIOLOGICAL TELEMETRY TESTS
# =============================================================================
class TestPhysiologicalTelemetryEndpoints:
    def test_submit_valid_telemetry(self, client: TestClient):
        payload = {
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
            "is_simulated": False,
            "source_device": "BioHarness-Alpha",
        }
        r = client.post("/api/extension/telemetry", json=payload, headers=SURGEON_HEADERS)
        assert r.status_code == 201
        data = r.json()
        assert data["heart_rate"] == 72.0
        assert data["spo2"] == 98.5
        assert data["is_simulated"] is False

    def test_submit_partial_telemetry_no_fabrication(self, client: TestClient):
        # Omit heart_rate, respiration_rate, sleep_quality
        payload = {
            "astronaut_id": 1,
            "spo2": 99.0,
            "body_temperature": 36.7,
            "is_simulated": True,
        }
        r = client.post("/api/extension/telemetry", json=payload, headers=SURGEON_HEADERS)
        assert r.status_code == 201
        data = r.json()
        assert data["spo2"] == 99.0
        assert data["heart_rate"] is None  # Never fabricated!
        assert data["respiration_rate"] is None
        assert data["sleep_hours"] is None

    def test_telemetry_out_of_range_validation(self, client: TestClient):
        # Heart rate above upper bound (240 bpm)
        payload = {
            "astronaut_id": 1,
            "heart_rate": 280.0,
        }
        r = client.post("/api/extension/telemetry", json=payload, headers=SURGEON_HEADERS)
        assert r.status_code == 422

    def test_get_latest_telemetry(self, client: TestClient):
        # Ensure at least one reading exists
        client.post(
            "/api/extension/telemetry",
            json={"astronaut_id": 1, "heart_rate": 68.0},
            headers=SURGEON_HEADERS,
        )
        r = client.get("/api/extension/telemetry/astronaut/1/latest", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data is not None
        assert data["astronaut_id"] == 1
        assert data["heart_rate"] == 68.0

    def test_get_telemetry_history(self, client: TestClient):
        r = client.get("/api/extension/telemetry/astronaut/1/history?hours=24", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        history = r.json()
        assert isinstance(history, list)


# =============================================================================
# 4. PSI APIS & BEHAVIORAL ANALYTICS TESTS
# =============================================================================
class TestPsiEndpoints:
    def test_submit_calibration(self, client: TestClient):
        poses = [
            {"photo_number": 1, "pose_name": "neutral_forward", "valid": True, "emotions": {"neutral": 0.85, "happy": 0.15}},
            {"photo_number": 2, "pose_name": "neutral_tilt_left", "valid": True, "emotions": {"neutral": 0.90, "happy": 0.10}},
            {"photo_number": 3, "pose_name": "neutral_tilt_right", "valid": True, "emotions": {"neutral": 0.88, "happy": 0.12}},
            {"photo_number": 4, "pose_name": "neutral_up", "valid": True, "emotions": {"neutral": 0.82, "happy": 0.18}},
            {"photo_number": 5, "pose_name": "neutral_down", "valid": True, "emotions": {"neutral": 0.86, "happy": 0.14}},
        ]
        r = client.post("/api/extension/psi/calibrate/1", json={"poses": poses}, headers=SURGEON_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "baseline_stress" in data
        assert "baseline_sigma" in data
        assert len(data["optimal_range"]) == 2

    def test_get_astronaut_baseline(self, client: TestClient):
        r = client.get("/api/extension/psi/baseline/1", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        baseline = r.json()
        assert baseline["astronaut_id"] == 1
        assert "baseline_stress" in baseline
        assert "stress_threshold" in baseline

    def test_submit_direct_reading_success(self, client: TestClient):
        payload = {
            "raw_stress": 32.5,
            "smoothed_stress": 30.0,
            "dominant_emotion": "neutral",
            "emotion_vector": {
                "angry": 0.05,
                "disgust": 0.02,
                "fear": 0.03,
                "happy": 0.10,
                "sad": 0.05,
                "surprise": 0.05,
                "neutral": 0.70,
            },
            "motion_level": 1.2,
            "task_complexity": 6.0,
            "mission_id": 1,
        }
        r = client.post("/api/extension/psi/readings/1", json=payload, headers=SURGEON_HEADERS)
        assert r.status_code == 201
        res = r.json()
        assert res["astronaut_id"] == 1
        assert res["raw_stress"] == 32.5
        assert res["smoothed_stress"] == 30.0
        assert "risk_level" in res

    def test_submit_direct_reading_invalid_bounds(self, client: TestClient):
        payload = {
            "raw_stress": 150.0,  # Invalid: > 100
            "smoothed_stress": 30.0,
            "dominant_emotion": "neutral",
            "emotion_vector": {"neutral": 1.0},
        }
        r = client.post("/api/extension/psi/readings/1", json=payload, headers=SURGEON_HEADERS)
        assert r.status_code == 422

    def test_get_latest_reading_and_status(self, client: TestClient):
        client.post(
            "/api/extension/psi/readings/1",
            json={
                "raw_stress": 25.0,
                "smoothed_stress": 26.0,
                "dominant_emotion": "neutral",
                "emotion_vector": {"neutral": 0.8, "happy": 0.2},
            },
            headers=SURGEON_HEADERS,
        )
        r = client.get("/api/extension/psi/readings/1/latest", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        status_data = r.json()
        assert "status" in status_data
        assert "status_label" in status_data
        assert "latest_reading" in status_data

    def test_get_psi_reading_history(self, client: TestClient):
        r = client.get("/api/extension/psi/readings/1/history?hours=48&limit=50", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_chronic_stress_analytics(self, client: TestClient):
        r = client.get("/api/extension/psi/analytics/chronic/1", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        res = r.json()
        assert res["astronaut_id"] == 1
        assert "is_chronic" in res
        assert isinstance(res["is_chronic"], bool)

    def test_get_burnout_analytics(self, client: TestClient):
        r = client.get("/api/extension/psi/analytics/burnout/1", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        res = r.json()
        assert res["astronaut_id"] == 1
        assert "brs" in res
        assert "classification" in res

    def test_process_frame_invalid_base64(self, client: TestClient):
        r = client.post(
            "/api/extension/psi/process-frame/1",
            json={"frame_base64": "not-valid-base64-content!!!"},
            headers=SURGEON_HEADERS,
        )
        assert r.status_code == 400

    def test_process_frame_mock_synthetic_image(self, client: TestClient):
        # Generate a small blank synthetic test frame
        img = np.zeros((120, 120, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", img)
        b64 = base64.b64encode(buf).decode("utf-8")

        r = client.post(
            "/api/extension/psi/process-frame/1",
            json={"frame_base64": b64, "task_complexity": 5.0},
            headers=SURGEON_HEADERS,
        )
        # OpenCV fallback processes the synthetic image frame
        assert r.status_code == 200
        data = r.json()
        assert "smoothed_stress" in data
        assert "dominant_emotion" in data

    def test_analyze_calibration_frame_handling(self, client: TestClient):
        # Invalid base64
        r = client.post(
            "/api/extension/psi/calibrate/1/analyze-frame",
            json={"frame_base64": "invalid-base64-payload"},
            headers=SURGEON_HEADERS,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert data["quality"] == "unreadable"

        # Too dark frame
        dark_img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", dark_img)
        dark_b64 = base64.b64encode(buf).decode("utf-8")
        r_dark = client.post(
            "/api/extension/psi/calibrate/1/analyze-frame",
            json={"frame_base64": dark_b64, "pose_name": "neutral_1", "photo_number": 1},
            headers=SURGEON_HEADERS,
        )
        assert r_dark.status_code == 200
        dark_res = r_dark.json()
        assert dark_res["valid"] is False
        assert dark_res["quality"] == "too_dark"

    def test_run_benchmark_calibration_endpoint(self, client: TestClient):
        r = client.post("/api/extension/psi/calibrate/1/benchmark", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        res = r.json()
        assert res["success"] is True
        assert "baseline_stress" in res
        assert "baseline_sigma" in res
        assert "optimal_range" in res
        assert res["valid_photos"] == 5

        # Verify baseline can now be queried
        r_base = client.get("/api/extension/psi/baseline/1", headers=SURGEON_HEADERS)
        assert r_base.status_code == 200
        base_data = r_base.json()
        assert base_data["is_calibrated"] is True
        assert base_data["baseline_stress"] == res["baseline_stress"]


# =============================================================================
# 5. DASHBOARD APIS TESTS
# =============================================================================
class TestDashboardEndpoints:
    def test_astronaut_dashboard_overview(self, client: TestClient):
        # Ingest reading so astronaut has active data
        client.post(
            "/api/extension/psi/readings/1",
            json={
                "raw_stress": 24.0,
                "smoothed_stress": 25.0,
                "dominant_emotion": "neutral",
                "emotion_vector": {"neutral": 0.9, "happy": 0.1},
            },
            headers=SURGEON_HEADERS,
        )
        client.post(
            "/api/extension/telemetry",
            json={"astronaut_id": 1, "heart_rate": 65.0, "spo2": 99.0, "sleep_hours": 8.0},
            headers=SURGEON_HEADERS,
        )

        r = client.get("/api/extension/dashboard/astronaut/1", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        overview = r.json()
        assert "astronaut" in overview
        assert overview["astronaut"]["id"] == 1
        assert "psi_status" in overview
        assert "physiological" in overview
        assert overview["physiological"]["available"] is True
        assert "recovery" in overview
        assert "alerts" in overview
        assert overview["recovery"]["readiness_classification"] in ["optimal", "moderate", "depleted"]

    def test_astronaut_dashboard_not_found(self, client: TestClient):
        r = client.get("/api/extension/dashboard/astronaut/9999", headers=SURGEON_HEADERS)
        assert r.status_code == 404

    def test_mission_dashboard_overview(self, client: TestClient):
        r = client.get("/api/extension/dashboard/mission/1", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        overview = r.json()
        assert "mission" in overview
        assert overview["mission"]["id"] == 1
        assert "crew" in overview
        assert "crew_count" in overview
        assert "active_alerts" in overview

    def test_mission_dashboard_not_found(self, client: TestClient):
        r = client.get("/api/extension/dashboard/mission/9999", headers=SURGEON_HEADERS)
        assert r.status_code == 404


# =============================================================================
# 6. SECURITY & ASTRONAUT ISOLATION TESTS
# =============================================================================
class TestSecurityAndIsolation:
    def test_invalid_api_key_rejected(self, client: TestClient):
        r = client.get(
            "/api/extension/astronauts/1",
            headers={"X-API-Key": "INVALID-MALICIOUS-TOKEN"},
        )
        assert r.status_code == 401
        assert "invalid" in r.json()["detail"].lower()

    def test_astronaut_cannot_access_other_astronaut(self, client: TestClient):
        # Crew member 1 tries to access crew member 2's data
        r = client.get(
            "/api/extension/psi/readings/2/latest",
            headers=CREW_1_HEADERS,
        )
        assert r.status_code == 403
        assert "access denied" in r.json()["detail"].lower()

    def test_astronaut_can_access_own_data(self, client: TestClient):
        # Crew member 1 accesses crew member 1's data
        r = client.get(
            "/api/extension/psi/readings/1/latest",
            headers=CREW_1_HEADERS,
        )
        assert r.status_code == 200

    def test_flight_surgeon_can_access_any_astronaut(self, client: TestClient):
        # Flight surgeon accesses crew member 2's data
        r = client.get(
            "/api/extension/psi/readings/2/latest",
            headers=SURGEON_HEADERS,
        )
        assert r.status_code == 200

    def test_role_enforcement_on_astronaut_creation(self, client: TestClient):
        # Regular astronaut cannot create new astronauts
        payload = {"name": "Unauthorized Astro", "role": "Payload Specialist"}
        r = client.post(
            "/api/extension/astronauts",
            json=payload,
            headers=CREW_1_HEADERS,
        )
        assert r.status_code == 403


# =============================================================================
# 7. WEBSOCKET REAL-TIME STREAMING TESTS
# =============================================================================
class TestWebSocketStreaming:
    def test_websocket_connection_and_ping(self, client: TestClient):
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-SURGEON-KEY-99") as ws:
            ws.send_json({"action": "ping"})
            resp = ws.receive_json()
            assert resp.get("type") == "pong"

    def test_websocket_channel_subscription(self, client: TestClient):
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-SURGEON-KEY-99") as ws:
            ws.send_json({"action": "subscribe_astronaut", "astronaut_id": 1})
            resp = ws.receive_json()
            assert resp.get("type") == "subscribed"
            assert resp.get("channel") == "astronaut"
            assert resp.get("id") == 1

            ws.send_json({"action": "subscribe_mission", "mission_id": 2})
            resp = ws.receive_json()
            assert resp.get("type") == "subscribed"
            assert resp.get("channel") == "mission"
            assert resp.get("id") == 2
