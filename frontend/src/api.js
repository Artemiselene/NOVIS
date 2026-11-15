/**
 * ASTRA MIND Health Extension — Centralized API Client
 * ====================================================
 * Configurable REST client connecting to FastAPI backend endpoints.
 * Automatically injects authentication headers from active session.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/extension";

// Active authentication state (managed in memory & localStorage)
// Default to verified demonstration flight surgeon token if unset
let currentApiKey = localStorage.getItem("astra_api_key") || "ASTRA-SURGEON-KEY-99";

export function setApiKey(key) {
  currentApiKey = key ? key.trim() : "";
  if (currentApiKey) {
    localStorage.setItem("astra_api_key", currentApiKey);
  } else {
    localStorage.removeItem("astra_api_key");
  }
}

export function getApiKey() {
  return currentApiKey || localStorage.getItem("astra_api_key") || "";
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  const key = getApiKey();
  if (key) {
    headers["X-API-Key"] = key;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (!res.ok) {
    let errDetail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch (_) {
      try {
        const text = await res.text();
        if (text) errDetail = text;
      } catch (__) {}
    }
    const error = new Error(errDetail);
    error.status = res.status;
    throw error;
  }

  // Handle 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getBaseUrl: () => BASE_URL,
  getApiKey,
  setApiKey,

  // --- Astronauts ---
  listAstronauts: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/astronauts${qs ? `?${qs}` : ""}`);
  },
  getAstronaut: (id) => request(`/astronauts/${id}`),
  createAstronaut: (data) => request("/astronauts", { method: "POST", body: JSON.stringify(data) }),
  updateAstronaut: (id, data) => request(`/astronauts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAstronaut: (id, force = false) =>
    request(`/astronauts/${id}${force ? "?force=true" : ""}`, { method: "DELETE" }),
  archiveAstronaut: (id) => request(`/astronauts/${id}/archive`, { method: "POST" }),
  restoreAstronaut: (id) => request(`/astronauts/${id}/restore`, { method: "POST" }),

  // --- Missions ---
  listMissions: (statusFilter) => {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : "";
    return request(`/missions${qs}`);
  },
  getMission: (id) => request(`/missions/${id}`),
  getMissionSummary: (id) => request(`/missions/${id}/summary`),
  assignAstronaut: (missionId, astronautId) =>
    request(`/missions/${missionId}/assign`, {
      method: "POST",
      body: JSON.stringify({ astronaut_id: astronautId })
    }),

  // --- Physiological Telemetry ---
  submitTelemetry: (data) => request("/telemetry", { method: "POST", body: JSON.stringify(data) }),
  getLatestTelemetry: (astronautId) => request(`/telemetry/astronaut/${astronautId}/latest`),
  getTelemetryHistory: (astronautId, hours = 24) =>
    request(`/telemetry/astronaut/${astronautId}/history?hours=${hours}`),

  // --- PSI Behavioral Health ---
  getBaseline: (astronautId) => request(`/psi/baseline/${astronautId}`),
  calibrateAstronaut: (astronautId, poses) =>
    request(`/psi/calibrate/${astronautId}`, {
      method: "POST",
      body: JSON.stringify({ poses })
    }),
  analyzeCalibrationFrame: (astronautId, data) =>
    request(`/psi/calibrate/${astronautId}/analyze-frame`, {
      method: "POST",
      body: JSON.stringify(data)
    }),
  runBenchmarkCalibration: (astronautId) =>
    request(`/psi/calibrate/${astronautId}/benchmark`, {
      method: "POST"
    }),
  submitDirectReading: (astronautId, data) =>
    request(`/psi/readings/${astronautId}`, {
      method: "POST",
      body: JSON.stringify(data)
    }),
  getLatestPsi: (astronautId) => request(`/psi/readings/${astronautId}/latest`),
  getPsiHistory: (astronautId, hours = 24, limit = 50) =>
    request(`/psi/readings/${astronautId}/history?hours=${hours}&limit=${limit}`),
  getChronicAnalytics: (astronautId) => request(`/psi/analytics/chronic/${astronautId}`),
  getBurnoutAnalytics: (astronautId) => request(`/psi/analytics/burnout/${astronautId}`),

  // --- Dashboards ---
  getAstronautDashboard: (astronautId) => request(`/dashboard/astronaut/${astronautId}`),
  getMissionDashboard: (missionId) => request(`/dashboard/mission/${missionId}`),

  // --- Core Health Extension (Legacy preserved) ---
  environments: () => request("/environments"),
  bodySystems: () => request("/body-systems"),
  bodyStatus: (key, astronautId = 1) => request(`/body-systems/${key}/status?astronaut_id=${astronautId}`),
  routines: (astronautId) => request(`/routines${astronautId ? `?astronaut_id=${astronautId}` : ""}`),
  createRoutine: (data) => request("/routines", { method: "POST", body: JSON.stringify(data) }),
  completeRoutine: (id, notes = "Completed") =>
    request(`/routines/${id}/complete`, { method: "POST", body: JSON.stringify({ notes }) }),
  challenges: () => request("/challenges"),
  completeChallenge: (id, astronautId = 1) =>
    request(`/challenges/${id}/complete/${astronautId}`, { method: "POST", body: "{}" }),
  education: () => request("/education")
};
