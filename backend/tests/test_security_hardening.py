"""
ASTRA MIND — Phase 3.1 Security Hardening Regression Test Suite
==============================================================
Validates the 4 critical security blockers resolved in Phase 3.1:
1. SEC-01: Insecure default authentication removal (Missing/Invalid keys -> 401).
2. SEC-02: WebSocket connection authentication & subscription role authorization.
3. SEC-03: Mission health summary privacy protection (Ordinary astronauts -> 403).
4. SEC-04: Environment-driven credentials & production safe-failure.
"""

import os
import json
import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

SURGEON_HEADERS = {"X-API-Key": "ASTRA-SURGEON-KEY-99"}
MISSION_CONTROL_HEADERS = {"X-API-Key": "ASTRA-MISSION-CONTROL-2026"}
CREW_1_HEADERS = {"X-API-Key": "ASTRA-CREW-KEY-01"}
CREW_2_HEADERS = {"X-API-Key": "ASTRA-CREW-KEY-02"}


# =============================================================================
# 1. AUTHENTICATION REGRESSION TESTS (SEC-01)
# =============================================================================
class TestAuthenticationHardening:
    def test_missing_api_key_returns_401(self, client: TestClient):
        """Unauthenticated requests must return HTTP 401 (no default surgeon privilege)."""
        r = client.get("/api/extension/astronauts")
        assert r.status_code == 401
        assert "missing authentication credentials" in r.json()["detail"].lower()

    def test_missing_api_key_on_psi_returns_401(self, client: TestClient):
        """Unauthenticated access to PSI telemetry must return HTTP 401."""
        r = client.get("/api/extension/psi/readings/1/latest")
        assert r.status_code == 401
        assert "missing authentication credentials" in r.json()["detail"].lower()

    def test_missing_api_key_on_telemetry_returns_401(self, client: TestClient):
        """Unauthenticated access to physiological telemetry must return HTTP 401."""
        r = client.get("/api/extension/telemetry/astronaut/1/latest")
        assert r.status_code == 401

    def test_missing_api_key_on_dashboard_returns_401(self, client: TestClient):
        """Unauthenticated access to dashboard must return HTTP 401."""
        r = client.get("/api/extension/dashboard/astronaut/1")
        assert r.status_code == 401

    def test_invalid_api_key_returns_401(self, client: TestClient):
        """Invalid or forged credentials must return HTTP 401."""
        r = client.get(
            "/api/extension/astronauts",
            headers={"X-API-Key": "UNAUTHORIZED-HACKER-KEY"},
        )
        assert r.status_code == 401
        assert "invalid authentication credentials" in r.json()["detail"].lower()

    def test_bearer_token_authentication(self, client: TestClient):
        """Bearer token format in Authorization header must be accepted."""
        r = client.get(
            "/api/extension/astronauts",
            headers={"Authorization": "Bearer ASTRA-SURGEON-KEY-99"},
        )
        assert r.status_code == 200

    def test_valid_surgeon_credentials_work(self, client: TestClient):
        """Legitimate flight surgeon credentials grant authorized access."""
        r = client.get("/api/extension/astronauts", headers=SURGEON_HEADERS)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# =============================================================================
# 2. ASTRONAUT & MISSION HEALTH ISOLATION (SEC-01, SEC-03)
# =============================================================================
class TestHealthDataIsolation:
    def test_astronaut_cannot_access_another_astronaut_data(self, client: TestClient):
        """Crew member 1 must receive HTTP 403 when requesting crew member 2's telemetry."""
        r = client.get("/api/extension/psi/readings/2/latest", headers=CREW_1_HEADERS)
        assert r.status_code == 403
        assert "access denied" in r.json()["detail"].lower()

    def test_astronaut_cannot_access_another_astronaut_telemetry(self, client: TestClient):
        """Crew member 1 must receive HTTP 403 when requesting crew member 2's vitals."""
        r = client.get("/api/extension/telemetry/astronaut/2/latest", headers=CREW_1_HEADERS)
        assert r.status_code == 403
        assert "access denied" in r.json()["detail"].lower()

    def test_astronaut_cannot_access_another_astronaut_dashboard(self, client: TestClient):
        """Crew member 1 must receive HTTP 403 when requesting crew member 2's dashboard."""
        r = client.get("/api/extension/dashboard/astronaut/2", headers=CREW_1_HEADERS)
        assert r.status_code == 403

    def test_astronaut_can_access_own_data(self, client: TestClient):
        """Crew member 1 can access their own telemetry."""
        r = client.get("/api/extension/psi/readings/1/latest", headers=CREW_1_HEADERS)
        assert r.status_code == 200

    def test_astronaut_cannot_access_mission_summary(self, client: TestClient):
        """Ordinary astronauts must receive HTTP 403 on mission health summaries."""
        r = client.get("/api/extension/missions/1/summary", headers=CREW_1_HEADERS)
        assert r.status_code == 403
        assert "access forbidden" in r.json()["detail"].lower()

    def test_astronaut_cannot_access_mission_dashboard(self, client: TestClient):
        """Ordinary astronauts must receive HTTP 403 on mission-wide crew dashboard."""
        r = client.get("/api/extension/dashboard/mission/1", headers=CREW_1_HEADERS)
        assert r.status_code == 403
        assert "access forbidden" in r.json()["detail"].lower()

    def test_surgeon_can_access_mission_summary_and_dashboard(self, client: TestClient):
        """Flight surgeon can access mission summaries and multi-crew dashboard."""
        r1 = client.get("/api/extension/missions/1/summary", headers=SURGEON_HEADERS)
        assert r1.status_code == 200

        r2 = client.get("/api/extension/dashboard/mission/1", headers=SURGEON_HEADERS)
        assert r2.status_code == 200

    def test_director_can_access_mission_summary_and_dashboard(self, client: TestClient):
        """Mission director can access mission summaries and multi-crew dashboard."""
        r1 = client.get("/api/extension/missions/1/summary", headers=MISSION_CONTROL_HEADERS)
        assert r1.status_code == 200

        r2 = client.get("/api/extension/dashboard/mission/1", headers=MISSION_CONTROL_HEADERS)
        assert r2.status_code == 200


# =============================================================================
# 3. WEBSOCKET CONNECTION & SUBSCRIPTION SECURITY (SEC-02)
# =============================================================================
class TestWebSocketSecurity:
    def test_unauthenticated_websocket_connection_rejected(self, client: TestClient):
        """Connection without token must be closed immediately with code 1008."""
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/extension/ws/telemetry"):
                pass
        assert exc.value.code == 1008

    def test_invalid_token_websocket_connection_rejected(self, client: TestClient):
        """Connection with invalid token must be closed immediately with code 1008."""
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/extension/ws/telemetry?token=FAKE-INVALID-TOKEN"):
                pass
        assert exc.value.code == 1008

    def test_authorized_surgeon_websocket_connection(self, client: TestClient):
        """Surgeon token establishes authenticated WebSocket connection."""
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-SURGEON-KEY-99") as ws:
            ws.send_json({"action": "ping"})
            resp = ws.receive_json()
            assert resp.get("type") == "pong"

    def test_surgeon_can_subscribe_to_any_astronaut(self, client: TestClient):
        """Surgeon can subscribe to any astronaut's live stream."""
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-SURGEON-KEY-99") as ws:
            ws.send_json({"action": "subscribe_astronaut", "astronaut_id": 2})
            resp = ws.receive_json()
            assert resp.get("type") == "subscribed"
            assert resp.get("channel") == "astronaut"
            assert resp.get("id") == 2

    def test_surgeon_can_subscribe_to_mission(self, client: TestClient):
        """Surgeon can subscribe to mission-wide live stream."""
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-SURGEON-KEY-99") as ws:
            ws.send_json({"action": "subscribe_mission", "mission_id": 1})
            resp = ws.receive_json()
            assert resp.get("type") == "subscribed"
            assert resp.get("channel") == "mission"
            assert resp.get("id") == 1

    def test_astronaut_can_subscribe_to_own_stream(self, client: TestClient):
        """Astronaut 1 is authorized to subscribe to astronaut 1's stream."""
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-CREW-KEY-01") as ws:
            ws.send_json({"action": "subscribe_astronaut", "astronaut_id": 1})
            resp = ws.receive_json()
            assert resp.get("type") == "subscribed"
            assert resp.get("channel") == "astronaut"
            assert resp.get("id") == 1

    def test_astronaut_cannot_subscribe_to_another_astronaut(self, client: TestClient):
        """Astronaut 1 attempting to subscribe to astronaut 2 is rejected."""
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-CREW-KEY-01") as ws:
            ws.send_json({"action": "subscribe_astronaut", "astronaut_id": 2})
            resp = ws.receive_json()
            assert resp.get("type") == "error"
            assert "unauthorized subscription" in resp.get("message", "").lower()

    def test_astronaut_cannot_subscribe_to_mission_stream(self, client: TestClient):
        """Astronaut 1 attempting to subscribe to mission-wide stream is rejected."""
        with client.websocket_connect("/api/extension/ws/telemetry?token=ASTRA-CREW-KEY-01") as ws:
            ws.send_json({"action": "subscribe_mission", "mission_id": 1})
            resp = ws.receive_json()
            assert resp.get("type") == "error"
            assert "unauthorized subscription" in resp.get("message", "").lower()


# =============================================================================
# 4. ENVIRONMENT-BASED CREDENTIALS & SAFE FAILURE (SEC-04)
# =============================================================================
class TestEnvironmentConfiguration:
    def test_missing_production_credentials_fail_safely(self, monkeypatch, client: TestClient):
        """In production environment without configured keys, requests fail safely with 401."""
        monkeypatch.setenv("ASTRA_ENV", "production")
        monkeypatch.delenv("ASTRA_SURGEON_API_KEY", raising=False)
        monkeypatch.delenv("ASTRA_MISSION_DIRECTOR_API_KEY", raising=False)
        monkeypatch.delenv("ASTRA_CREW_1_API_KEY", raising=False)
        monkeypatch.delenv("ASTRA_CREW_2_API_KEY", raising=False)
        monkeypatch.delenv("ASTRA_EXTRA_CREW_KEYS", raising=False)

        # Attempt request with an old hardcoded key: must fail with 401
        r = client.get(
            "/api/extension/astronauts",
            headers={"X-API-Key": "ASTRA-SURGEON-KEY-99"},
        )
        assert r.status_code == 401
        assert "invalid authentication credentials" in r.json()["detail"].lower()
