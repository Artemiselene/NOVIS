/**
 * NOVIS — Neural Onboard Vitality & Intelligence System — & Physiological Health Platform
 * =================================================================
 * Interactive Mission Control Dashboard for Astronaut Health Intelligence.
 * Integrates PSI stress monitoring, Burnout Risk Scoring (BRS), physiological
 * vitals, real-time WebSocket streaming, and role-based demonstration access.
 */

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import {
  Activity,
  HeartPulse,
  BookOpen,
  CalendarCheck,
  Medal,
  Globe2,
  Brain,
  Wind,
  PersonStanding,
  ShieldAlert,
  Zap,
  Radio,
  TrendingUp,
  Moon,
  Thermometer,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  LogOut,
  Key,
  Users,
  Compass,
  Sliders,
  Send,
  Camera,
  Video,
  VideoOff,
  Sparkles,
  ShieldCheck,
  X,
  Play,
  RotateCcw,
  Trash2,
  Sun,
  UserCheck,
  ChevronRight,
  AlertCircle,
  Plus,
  Search,
  Edit2,
  Archive,
  ArchiveRestore,
  Grid,
  List,
  UserPlus
} from "lucide-react";
import { api, getApiKey, setApiKey } from "./api";
import { useWebSocket } from "./useWebSocket";

// Navigation tabs — Crew Management & Baseline Calibration primary workflows
const TABS = [
  { id: "crew", label: "Crew Management", icon: Users },
  { id: "calibration", label: "Baseline Calibration", icon: Camera },
  { id: "dashboard", label: "Astronaut Telemetry", icon: Activity },
  { id: "mission", label: "Mission Overview", icon: Compass },
  { id: "psi", label: "Behavioral PSI Analytics", icon: Brain },
  { id: "body", label: "Human Health Map", icon: PersonStanding },
  { id: "env", label: "Mission Environments", icon: Globe2 },
  { id: "routines", label: "Health Routines", icon: CalendarCheck },
  { id: "challenges", label: "Mission Challenges", icon: Medal },
  { id: "education", label: "Health Education", icon: BookOpen }
];

// Demo login personas (local dev tokens configured on backend)
const DEMO_PERSONAS = [
  {
    id: "surgeon",
    label: "Flight Surgeon (Dr. E. Hansen)",
    role: "flight_surgeon",
    key: "ASTRA-SURGEON-KEY-99",
    desc: "Full fleet access to all astronaut vitals, PSI telemetry, and clinical dashboards."
  },
  {
    id: "director",
    label: "Mission Director (Flight Control)",
    role: "mission_director",
    key: "ASTRA-MISSION-CONTROL-2026",
    desc: "Operational access to mission status, crew summaries, and safety alerts."
  },
  {
    id: "crew1",
    label: "Astronaut 1 (Dr. Sarah Walker - Cmdr)",
    role: "astronaut",
    astronautId: 1,
    key: "ASTRA-CREW-KEY-01",
    desc: "Scoped strictly to Astronaut 1 personal health data."
  },
  {
    id: "crew2",
    label: "Astronaut 2 (Mark Kelly - Eng)",
    role: "astronaut",
    astronautId: 2,
    key: "ASTRA-CREW-KEY-02",
    desc: "Scoped strictly to Astronaut 2 personal health data."
  }
];

// Interactive Human silhouette mapping
const REGION_POSITIONS = {
  brain: { x: 105, y: 18, w: 70, h: 58 },
  lungs: { x: 83, y: 104, w: 114, h: 75 },
  heart: { x: 124, y: 123, w: 35, h: 42 },
  muscles: { x: 69, y: 184, w: 142, h: 112 },
  digestive: { x: 111, y: 177, w: 58, h: 72 },
  sleep: { x: 207, y: 23, w: 36, h: 36 }
};

// 5 Standardized Sequential Calibration Poses
const CALIBRATION_POSES = [
  { id: 1, name: "Neutral Forward", desc: "Face forward directly at lens. Relax facial, brow, and jaw muscles." },
  { id: 2, name: "Slight Left Offset", desc: "Turn head 5° left. Keep chin level and maintain neutral resting affect." },
  { id: 3, name: "Slight Right Offset", desc: "Turn head 5° right. Keep gaze centered and avoid tension." },
  { id: 4, name: "Chin Level Rest", desc: "Return face to center. Ensure chin is level with horizontal axis." },
  { id: 5, name: "Resting Baseline", desc: "Breathe naturally and hold steady for final baseline convergence." }
];

function getCanvasFingerprint(canvas) {
  try {
    const ctx = canvas.getContext("2d");
    const points = [
      [160, 120], [320, 120], [480, 120],
      [200, 240], [320, 240], [440, 240],
      [240, 320], [320, 320], [400, 320],
      [320, 180], [320, 280], [280, 220]
    ];
    let sum = 0;
    for (const [x, y] of points) {
      const p = ctx.getImageData(x, y, 1, 1).data;
      sum += p[0] + p[1] + p[2];
    }
    return sum;
  } catch (_) {
    return Math.floor(Math.random() * 100000);
  }
}

/**
 * BaselineCalibrationPage
 * =======================
 * Dedicated space-grade personal PSI baseline calibration station.
 * Primary Mission Operations workflow.
 */
function BaselineCalibrationPage({
  astronauts,
  selectedAstronautId,
  setSelectedAstronautId,
  psiBaseline,
  onCalibrationComplete,
  onNavigateToDashboard
}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCameraStarting, setIsCameraStarting] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [samples, setSamples] = useState([]);
  const [detectedFaceBox, setDetectedFaceBox] = useState(null);
  const [liveFeedback, setLiveFeedback] = useState({
    faceDetected: false,
    quality: "searching",
    lightingStatus: "optimal",
    meanBrightness: 0,
    dominantEmotion: "neutral",
    message: "Start camera to align face and begin 5-sample baseline calibration."
  });
  const [rejectionReason, setRejectionReason] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isComputingBaseline, setIsComputingBaseline] = useState(false);
  const [calibrationResult, setCalibrationResult] = useState(null);
  const [autoCapture, setAutoCapture] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const trackerTimerRef = useRef(null);
  const autoCaptureTimerRef = useRef(null);
  const lastCaptureTimeRef = useRef(0);

  const selectedAstronaut = useMemo(
    () => astronauts.find((a) => a.id === selectedAstronautId) || astronauts[0],
    [astronauts, selectedAstronautId]
  );

  // Stop camera tracks and timers
  const stopCamera = useCallback(() => {
    if (trackerTimerRef.current) {
      clearInterval(trackerTimerRef.current);
      trackerTimerRef.current = null;
    }
    if (autoCaptureTimerRef.current) {
      clearInterval(autoCaptureTimerRef.current);
      autoCaptureTimerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsStreaming(false);
    setIsCameraStarting(false);
    setDetectedFaceBox(null);
  }, []);

  // Cleanup on unmount or astronaut switch
  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  // Reset state when switching astronaut
  useEffect(() => {
    stopCamera();
    setSamples([]);
    setCalibrationResult(null);
    setRejectionReason("");
    setCameraError("");
  }, [selectedAstronautId, stopCamera]);

  // Periodic face tracking & lighting analysis loop
  const runLiveTracker = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !isStreaming || isAnalyzing) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, 640, 480);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.65);

    try {
      const targetPose = CALIBRATION_POSES[samples.length]?.name || "Neutral Resting";
      const res = await api.analyzeCalibrationFrame(selectedAstronautId, {
        frame_base64: dataUrl,
        pose_name: targetPose,
        photo_number: samples.length + 1
      });

      const brightness = res.mean_brightness || 0;
      const lighting = brightness < 25 ? "under_exposed" : brightness > 235 ? "over_exposed" : "optimal";

      if (res.face_detected && res.face_box) {
        // Mirrored coordinate calculation because camera preview is flipped
        const box = res.face_box;
        const wPct = (box.w / 640) * 100;
        const hPct = (box.h / 480) * 100;
        const xPct = Math.max(0, 100 - ((box.x + box.w) / 640) * 100);
        const yPct = (box.y / 480) * 100;

        setDetectedFaceBox({ xPct, yPct, wPct, hPct, raw: box });
        setLiveFeedback({
          faceDetected: true,
          quality: res.quality,
          lightingStatus: lighting,
          meanBrightness: brightness,
          dominantEmotion: res.dominant_emotion || "neutral",
          message: "Face tracked and aligned. Hold steady to capture."
        });
      } else {
        setDetectedFaceBox(null);
        setLiveFeedback({
          faceDetected: false,
          quality: res.quality || "no_face",
          lightingStatus: lighting,
          meanBrightness: brightness,
          dominantEmotion: "neutral",
          message: res.error || "Searching for face... Center your face within the frame."
        });
      }
    } catch (_) {}
  }, [isStreaming, isAnalyzing, samples.length, selectedAstronautId]);

  // Start webcam
  const startCamera = async () => {
    setCameraError("");
    setRejectionReason("");
    setIsCameraStarting(true);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setIsCameraStarting(false);
      setCameraError("Webcam API (getUserMedia) not supported in this browser. You can use Demonstration Mode.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsStreaming(true);
      setIsCameraStarting(false);

      // Start tracker loop (every 750ms)
      trackerTimerRef.current = setInterval(() => {
        runLiveTracker();
      }, 750);
    } catch (err) {
      console.warn("Camera start error:", err);
      setIsCameraStarting(false);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setCameraError("Webcam access denied by browser permissions. Allow camera permissions or use Demonstration Mode.");
      } else {
        setCameraError(`Camera unavailable: ${err.message || "Device not detected"}. You can use Demonstration Mode.`);
      }
    }
  };

  // Submit collected 5 samples to backend
  const finalizeCalibration = useCallback(async (samplesToSubmit) => {
    setIsComputingBaseline(true);
    setRejectionReason("");
    try {
      const posesPayload = samplesToSubmit.map((s) => ({
        photo_number: s.photo_number,
        pose_name: s.pose_name,
        valid: true,
        emotions: s.emotions
      }));

      const calibRes = await api.calibrateAstronaut(selectedAstronautId, posesPayload);
      setCalibrationResult(calibRes);
      if (onCalibrationComplete) onCalibrationComplete(calibRes);
    } catch (e) {
      setRejectionReason(`Calibration calculation failed: ${e.message}`);
    } finally {
      setIsComputingBaseline(false);
    }
  }, [selectedAstronautId, onCalibrationComplete]);

  // Capture a single valid facial sample
  const capturePhoto = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !isStreaming || isAnalyzing) return;
    if (samples.length >= 5) return;

    // Check rate limit: minimum 800ms between captures
    const now = Date.now();
    if (now - lastCaptureTimeRef.current < 800) {
      setRejectionReason("Capture throttled: please allow at least 1.0s between sequential samples.");
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, 640, 480);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.75);

    // Compute frame fingerprint for duplicate prevention
    const currentFingerprint = getCanvasFingerprint(canvas);
    if (samples.length > 0) {
      const last = samples[samples.length - 1];
      if (last.rawHash && Math.abs(currentFingerprint - last.rawHash) < 18) {
        setRejectionReason("Duplicate frame rejected: adjust facial angle or posture slightly before capturing next sample.");
        return;
      }
    }

    setIsAnalyzing(true);
    setRejectionReason("");

    try {
      const photoNum = samples.length + 1;
      const targetPose = CALIBRATION_POSES[samples.length];

      const res = await api.analyzeCalibrationFrame(selectedAstronautId, {
        frame_base64: dataUrl,
        pose_name: targetPose.name,
        photo_number: photoNum
      });

      if (res.valid) {
        const newSample = {
          photo_number: photoNum,
          pose_name: targetPose.name,
          desc: targetPose.desc,
          thumbnailUrl: dataUrl,
          timestamp: new Date().toLocaleTimeString(),
          valid: true,
          emotions: res.emotions,
          dominantEmotion: res.dominant_emotion || "neutral",
          calculated_stress: res.calculated_stress ?? 20.0,
          brightness: res.mean_brightness,
          rawHash: currentFingerprint
        };

        const updated = [...samples, newSample];
        setSamples(updated);
        lastCaptureTimeRef.current = Date.now();

        // If 5 samples reached, auto-submit
        if (updated.length >= 5) {
          stopCamera();
          finalizeCalibration(updated);
        }
      } else {
        setRejectionReason(`Sample Rejected: ${res.error || "Frame does not satisfy quality standards."}`);
      }
    } catch (e) {
      setRejectionReason(`Analysis error: ${e.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  }, [isStreaming, isAnalyzing, samples, selectedAstronautId, stopCamera, finalizeCalibration]);

  // Auto-capture timer
  useEffect(() => {
    if (isStreaming && autoCapture && samples.length < 5) {
      autoCaptureTimerRef.current = setInterval(() => {
        capturePhoto();
      }, 2000);
    } else {
      if (autoCaptureTimerRef.current) {
        clearInterval(autoCaptureTimerRef.current);
        autoCaptureTimerRef.current = null;
      }
    }
    return () => {
      if (autoCaptureTimerRef.current) {
        clearInterval(autoCaptureTimerRef.current);
        autoCaptureTimerRef.current = null;
      }
    };
  }, [isStreaming, autoCapture, samples.length, capturePhoto]);

  // Delete individual sample
  const deleteSample = (index) => {
    setSamples((prev) => prev.filter((_, i) => i !== index).map((s, idx) => ({ ...s, photo_number: idx + 1 })));
    setCalibrationResult(null);
  };

  // Retake sample from index
  const retakeSample = (index) => {
    setSamples((prev) => prev.slice(0, index));
    setCalibrationResult(null);
    if (!isStreaming) startCamera();
  };

  // Run standardized benchmark demonstration mode
  const handleBenchmarkMode = async () => {
    stopCamera();
    setIsComputingBaseline(true);
    setRejectionReason("");
    try {
      const calibRes = await api.runBenchmarkCalibration(selectedAstronautId);
      setCalibrationResult(calibRes);
      // Populate visual sample previews with canonical benchmark poses
      setSamples([
        { photo_number: 1, pose_name: "Neutral Forward", desc: "Canonical forward resting gaze", timestamp: "Benchmark", dominantEmotion: "neutral", calculated_stress: 5.0, emotions: { neutral: 0.85, happy: 0.15 } },
        { photo_number: 2, pose_name: "Slight Left Offset", desc: "Canonical 5° left orientation", timestamp: "Benchmark", dominantEmotion: "neutral", calculated_stress: 4.8, emotions: { neutral: 0.90, happy: 0.10 } },
        { photo_number: 3, pose_name: "Slight Right Offset", desc: "Canonical 5° right orientation", timestamp: "Benchmark", dominantEmotion: "neutral", calculated_stress: 5.2, emotions: { neutral: 0.88, happy: 0.12 } },
        { photo_number: 4, pose_name: "Chin Level Rest", desc: "Canonical chin-level baseline", timestamp: "Benchmark", dominantEmotion: "neutral", calculated_stress: 5.1, emotions: { neutral: 0.82, happy: 0.18 } },
        { photo_number: 5, pose_name: "Resting Baseline", desc: "Canonical steady baseline convergence", timestamp: "Benchmark", dominantEmotion: "neutral", calculated_stress: 4.9, emotions: { neutral: 0.86, happy: 0.14 } }
      ]);
      if (onCalibrationComplete) onCalibrationComplete(calibRes);
    } catch (e) {
      setRejectionReason(`Demonstration calibration failed: ${e.message}`);
    } finally {
      setIsComputingBaseline(false);
    }
  };

  const nextPose = CALIBRATION_POSES[samples.length] || CALIBRATION_POSES[4];

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Astronaut Selector Bar */}
      <div className="card" style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Target Astronaut:
            </span>
            <select
              value={selectedAstronautId}
              onChange={(e) => setSelectedAstronautId(Number(e.target.value))}
              style={{
                padding: "8px 12px",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                fontSize: "13px",
                fontWeight: "600",
                background: "#fff",
                color: "#0f172a",
                cursor: "pointer"
              }}
            >
              {astronauts.filter(a => a.status !== "archived" || a.id === selectedAstronautId).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.role}) &bull; ID #{a.id} {a.status === "archived" ? "[Archived]" : ""}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {psiBaseline?.is_calibrated ? (
              <span className="status green" style={{ padding: "6px 12px", fontSize: "12px" }}>
                <CheckCircle2 size={14} /> CALIBRATED & VERIFIED (Resting: {psiBaseline.baseline_stress}%)
              </span>
            ) : (
              <span className="status red" style={{ padding: "6px 12px", fontSize: "12px" }}>
                <AlertCircle size={14} /> NOT CALIBRATED (Personal Baseline Required)
              </span>
            )}

            <button
              style={{
                background: "#f8fafc",
                color: "#475569",
                border: "1px solid #cbd5e1",
                borderRadius: "8px",
                padding: "7px 12px",
                fontSize: "12px",
                fontWeight: "600",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}
              onClick={handleBenchmarkMode}
              title="Execute standardized 5-pose benchmark calibration"
            >
              <Sparkles size={14} color="#6366f1" />
              <span>Standardized Demonstration Mode</span>
            </button>
          </div>
        </div>
      </div>

      {/* Calibration Completed Success Card */}
      {calibrationResult && (
        <div className="card" style={{ marginBottom: "20px", border: "2px solid #a7f3d0", background: "#f0fdf4" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
            <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "#10b981", color: "#fff", display: "grid", placeItems: "center" }}>
                <CheckCircle2 size={28} />
              </div>
              <div>
                <span className="status green" style={{ marginBottom: "4px" }}>CALIBRATED & VERIFIED</span>
                <h2 style={{ margin: "2px 0 0", color: "#065f46" }}>
                  Personal Baseline Active: {selectedAstronaut?.name}
                </h2>
                <div style={{ fontSize: "12px", color: "#047857" }}>
                  5 distinct resting poses analyzed with IQR outlier trimming &bull; Persisted to <code>AstronautPsiBaseline</code>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                style={{
                  background: "#fff",
                  color: "#334155",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                  padding: "8px 14px",
                  fontSize: "12px",
                  fontWeight: "600",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}
                onClick={() => {
                  setCalibrationResult(null);
                  setSamples([]);
                  startCamera();
                }}
              >
                <RotateCcw size={14} /> Recalibrate
              </button>
              <button
                className="primary"
                onClick={onNavigateToDashboard}
                style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 16px" }}
              >
                <span>View Live Telemetry</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>

          <div className="grid4" style={{ marginTop: "16px", gap: "12px" }}>
            <div style={{ background: "#fff", padding: "12px", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
              <div className="metric-label" style={{ color: "#065f46" }}>Resting PSI Baseline</div>
              <div style={{ fontSize: "24px", fontWeight: "700", color: "#0f172a", marginTop: "4px" }}>
                {calibrationResult.baseline_stress}%
              </div>
              <small className="muted">Mean resting emotional load</small>
            </div>

            <div style={{ background: "#fff", padding: "12px", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
              <div className="metric-label" style={{ color: "#065f46" }}>Tolerance Sigma (σ)</div>
              <div style={{ fontSize: "24px", fontWeight: "700", color: "#2563eb", marginTop: "4px" }}>
                ±{calibrationResult.baseline_sigma}%
              </div>
              <small className="muted">Natural resting dispersion</small>
            </div>

            <div style={{ background: "#fff", padding: "12px", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
              <div className="metric-label" style={{ color: "#065f46" }}>Optimal Operating Range</div>
              <div style={{ fontSize: "20px", fontWeight: "700", color: "#059669", marginTop: "4px" }}>
                {calibrationResult.optimal_range?.[0]}% – {calibrationResult.optimal_range?.[1]}%
              </div>
              <small className="muted">Nominal mission baseline</small>
            </div>

            <div style={{ background: "#fff", padding: "12px", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
              <div className="metric-label" style={{ color: "#065f46" }}>Stress Alert Threshold</div>
              <div style={{ fontSize: "20px", fontWeight: "700", color: "#dc2626", marginTop: "4px" }}>
                {calibrationResult.stress_threshold || Math.round(calibrationResult.baseline_stress + 3 * calibrationResult.baseline_sigma)}%
              </div>
              <small className="muted">Safety trigger elevation</small>
            </div>
          </div>
        </div>
      )}

      {/* Main 2-Column Calibration Studio */}
      <div className="calib-page-grid">
        {/* Left Column: Camera Viewport & Capture Station */}
        <div className="card">
          <div className="card-header">
            <div>
              <span className="card-title" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Camera size={18} color="#2563eb" /> Optical Calibration Station
              </span>
              <p className="muted" style={{ margin: "4px 0 0", fontSize: "12px" }}>
                Step {Math.min(5, samples.length + 1)} of 5: <b>{nextPose.name}</b>
              </p>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {isStreaming ? (
                <button
                  style={{
                    background: "#fef2f2",
                    color: "#991b1b",
                    border: "1px solid #fecaca",
                    borderRadius: "8px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px"
                  }}
                  onClick={stopCamera}
                >
                  <VideoOff size={14} /> Stop Camera
                </button>
              ) : (
                <button
                  className="primary"
                  onClick={startCamera}
                  disabled={isCameraStarting}
                  style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 14px", fontSize: "12px" }}
                >
                  <Video size={14} />
                  <span>{isCameraStarting ? "Starting..." : "Start Camera"}</span>
                </button>
              )}
            </div>
          </div>

          {/* Step Guidance Banner */}
          <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "8px", padding: "10px 14px", margin: "14px 0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", color: "#1d4ed8", textTransform: "uppercase" }}>
                Target Pose: {nextPose.name}
              </span>
              <span style={{ fontSize: "11px", fontWeight: "600", color: "#2563eb" }}>
                Progress: {samples.length} / 5 Distinct Samples
              </span>
            </div>
            <div style={{ fontSize: "12px", color: "#1e40af" }}>
              {nextPose.desc}
            </div>
          </div>

          {/* Progress Step Pills */}
          <div className="calib-step-pills">
            {[1, 2, 3, 4, 5].map((idx) => (
              <div
                key={idx}
                className={`calib-step-pill ${
                  samples.length >= idx ? "completed" : samples.length + 1 === idx ? "active" : ""
                }`}
                title={`Pose ${idx} of 5`}
              />
            ))}
          </div>

          {/* Video Viewport Container */}
          <div className="camera-container" style={{ minHeight: "360px" }}>
            <video ref={videoRef} playsInline muted autoPlay className="camera-video" />
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {!isStreaming && (
              <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", background: "#0f172a", color: "#94a3b8", textAlign: "center", padding: "20px" }}>
                <div>
                  <div style={{ width: "54px", height: "54px", borderRadius: "14px", background: "#1e293b", color: "#38bdf8", display: "grid", placeItems: "center", margin: "0 auto 12px" }}>
                    <Camera size={26} />
                  </div>
                  <h3 style={{ margin: "0 0 6px", color: "#f8fafc" }}>Webcam Viewfinder Inactive</h3>
                  <p style={{ margin: "0 0 16px", fontSize: "12px", maxWidth: "320px" }}>
                    Click <b>Start Camera</b> to initialize facial alignment and begin 5-sample calibration.
                  </p>
                  <button className="primary" onClick={startCamera}>
                    Start Camera
                  </button>
                </div>
              </div>
            )}

            {/* Real-Time Face Bounding Box Overlay */}
            {isStreaming && detectedFaceBox && (
              <div
                className="face-bounding-box"
                style={{
                  left: `${detectedFaceBox.xPct}%`,
                  top: `${detectedFaceBox.yPct}%`,
                  width: `${detectedFaceBox.wPct}%`,
                  height: `${detectedFaceBox.hPct}%`
                }}
              >
                <span className="face-box-tag">
                  ✓ Face Aligned &bull; {liveFeedback.dominantEmotion.toUpperCase()}
                </span>
              </div>
            )}

            {/* Reticle Guide when no face is locked */}
            {isStreaming && !detectedFaceBox && (
              <div className="camera-reticle-overlay">
                <div className="camera-reticle-oval warning" />
              </div>
            )}

            {/* Badges Overlay */}
            {isStreaming && (
              <>
                <div className="camera-overlay-badge top-left">
                  <span className="dot live" />
                  <span>LIVE TRACKER (640×480)</span>
                </div>

                <div className="camera-overlay-badge top-right">
                  <Sun size={12} color="#fbbf24" />
                  <span>{Math.round(liveFeedback.meanBrightness)} LUX &bull; {liveFeedback.lightingStatus.replace("_", " ").toUpperCase()}</span>
                </div>

                <div className="camera-overlay-badge bottom">
                  <span>{liveFeedback.message}</span>
                </div>
              </>
            )}
          </div>

          {/* Quality Indicators Bar */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "8px",
              background: "#f8fafc",
              padding: "10px 12px",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
              fontSize: "11px",
              margin: "12px 0"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: detectedFaceBox ? "#10b981" : "#f59e0b", fontWeight: "700", fontSize: "14px" }}>
                {detectedFaceBox ? "✓" : "○"}
              </span>
              <span>{detectedFaceBox ? "Face Detected in Reticle" : "Searching for Face..."}</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: liveFeedback.lightingStatus === "optimal" ? "#10b981" : "#ef4444", fontWeight: "700", fontSize: "14px" }}>
                {liveFeedback.lightingStatus === "optimal" ? "✓" : "⚠"}
              </span>
              <span style={{ textTransform: "capitalize" }}>
                Lighting: {liveFeedback.lightingStatus === "optimal" ? "Optimal (~" + Math.round(liveFeedback.meanBrightness) + " lux)" : liveFeedback.lightingStatus.replace("_", " ")}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: "#3b82f6", fontWeight: "700" }}>●</span>
              <span style={{ textTransform: "capitalize" }}>
                Dominant Affect: {liveFeedback.dominantEmotion}
              </span>
            </div>
          </div>

          {/* Rejection / Warning Alert Banner */}
          {rejectionReason && (
            <div className="error" style={{ margin: "10px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertCircle size={16} />
                <span>{rejectionReason}</span>
              </div>
              <button onClick={() => setRejectionReason("")}>Dismiss</button>
            </div>
          )}

          {/* Camera Error Banner */}
          {cameraError && (
            <div className="alert-card critical" style={{ margin: "10px 0" }}>
              <AlertTriangle size={16} />
              <div style={{ flex: 1 }}>
                <b>Camera Access Notice</b>
                <div style={{ fontSize: "12px", marginTop: "2px" }}>{cameraError}</div>
              </div>
              <button
                className="primary"
                onClick={handleBenchmarkMode}
                style={{ padding: "6px 12px", fontSize: "11px" }}
              >
                Use Benchmark Mode
              </button>
            </div>
          )}

          {/* Capture Controls */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px", marginTop: "14px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#475569", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={autoCapture}
                onChange={(e) => setAutoCapture(e.target.checked)}
                disabled={!isStreaming || samples.length >= 5}
              />
              <span>Auto-capture sequential poses (2.0s interval)</span>
            </label>

            <button
              className="primary"
              onClick={capturePhoto}
              disabled={!isStreaming || isAnalyzing || samples.length >= 5}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 20px",
                fontSize: "13px"
              }}
            >
              <Camera size={16} />
              <span>
                {isAnalyzing
                  ? "Analyzing Frame..."
                  : samples.length >= 5
                  ? "All 5 Samples Captured"
                  : `Capture Sample ${samples.length + 1} of 5`}
              </span>
            </button>
          </div>
        </div>

        {/* Right Column: Captured Samples Gallery & Baseline Submission */}
        <div>
          <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div className="card-header">
              <div>
                <span className="card-title">
                  Captured Samples Gallery ({samples.length} / 5)
                </span>
                <p className="muted" style={{ margin: "4px 0 0", fontSize: "12px" }}>
                  5 distinct resting samples required for IQR baseline calculation.
                </p>
              </div>

              {samples.length > 0 && (
                <button
                  style={{ background: "transparent", border: 0, color: "#64748b", fontSize: "12px", cursor: "pointer" }}
                  onClick={() => setSamples([])}
                >
                  Clear All
                </button>
              )}
            </div>

            {/* Transient privacy badge */}
            <div className="notice" style={{ margin: "10px 0 14px", padding: "8px 12px", fontSize: "11px", background: "#f8fafc" }}>
              <b>Transient In-Memory Verification:</b> Captured frames are analyzed in-memory and immediately released. Zero raw photographic imagery is stored permanently in the database.
            </div>

            {/* Sample List / Slots */}
            <div className="sample-gallery" style={{ flex: 1 }}>
              {CALIBRATION_POSES.map((pose, idx) => {
                const sample = samples[idx];
                if (sample) {
                  return (
                    <div key={pose.id} className="sample-card">
                      <img src={sample.thumbnailUrl} alt={`Sample ${idx + 1}`} className="sample-thumb" />
                      <div className="sample-details">
                        <div className="sample-title">
                          <span>Sample {idx + 1}: {sample.pose_name}</span>
                          <span className="status green" style={{ fontSize: "10px", padding: "2px 6px" }}>VALID</span>
                        </div>
                        <div className="sample-meta">
                          <span>Time: {sample.timestamp}</span>
                          <span>&bull;</span>
                          <span style={{ textTransform: "capitalize" }}>Affect: {sample.dominantEmotion}</span>
                          <span>&bull;</span>
                          <span>Stress: {Math.round(sample.calculated_stress)}%</span>
                        </div>
                      </div>
                      <div className="sample-actions">
                        <button
                          className="icon-btn"
                          title="Retake from this sample"
                          onClick={() => retakeSample(idx)}
                        >
                          <RotateCcw size={14} />
                        </button>
                        <button
                          className="icon-btn danger"
                          title="Delete this sample"
                          onClick={() => deleteSample(idx)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                } else if (idx === samples.length) {
                  return (
                    <div key={pose.id} className="sample-card empty" style={{ borderColor: "#2563eb", background: "#eff6ff" }}>
                      <div style={{ width: "56px", height: "56px", borderRadius: "8px", border: "1px dashed #93b4e9", display: "grid", placeItems: "center", color: "#2563eb" }}>
                        <Camera size={20} />
                      </div>
                      <div className="sample-details">
                        <div style={{ fontSize: "13px", fontWeight: "600", color: "#1d4ed8" }}>
                          Slot {idx + 1}: {pose.name} (Active Target)
                        </div>
                        <div style={{ fontSize: "11px", color: "#2563eb", marginTop: "2px" }}>
                          {pose.desc}
                        </div>
                      </div>
                    </div>
                  );
                } else {
                  return (
                    <div key={pose.id} className="sample-card empty">
                      <div style={{ width: "56px", height: "56px", borderRadius: "8px", border: "1px dashed #cbd5e1", display: "grid", placeItems: "center" }}>
                        <span style={{ fontSize: "14px", fontWeight: "600" }}>{idx + 1}</span>
                      </div>
                      <div className="sample-details">
                        <div style={{ fontSize: "13px", fontWeight: "500", color: "#64748b" }}>
                          Slot {idx + 1}: {pose.name}
                        </div>
                        <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>
                          Awaiting preceding sample captures
                        </div>
                      </div>
                    </div>
                  );
                }
              })}
            </div>

            {/* Submission Section */}
            <div style={{ marginTop: "16px", borderTop: "1px solid #e2e8f0", paddingTop: "14px" }}>
              {samples.length === 5 ? (
                <button
                  className="primary"
                  onClick={() => finalizeCalibration(samples)}
                  disabled={isComputingBaseline}
                  style={{
                    width: "100%",
                    padding: "12px",
                    fontSize: "14px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px"
                  }}
                >
                  <Sparkles size={16} />
                  <span>
                    {isComputingBaseline
                      ? "Applying IQR Outlier Trimming & Saving..."
                      : "Compute & Persist Baseline to Database"}
                  </span>
                </button>
              ) : (
                <button
                  disabled
                  style={{
                    width: "100%",
                    padding: "12px",
                    background: "#f1f5f9",
                    color: "#94a3b8",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    fontSize: "13px",
                    fontWeight: "600"
                  }}
                >
                  Capture {5 - samples.length} more sample(s) to compute baseline
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


/**
 * CrewManagementPage
 * ==================
 * Interactive Crew Management Dashboard for NOVIS.
 * Displays fleet personnel metrics, search/filtering, grid/table views,
 * and Create/Edit/Archive/Delete actions integrated with SQLite.
 */
function CrewManagementPage({
  astronauts,
  missions,
  selectedAstronautId,
  setSelectedAstronautId,
  onNavigateToCalibration,
  onNavigateToDashboard,
  onRefreshRoster,
  onError,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [missionFilter, setMissionFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [calibFilter, setCalibFilter] = useState("all");
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "table"

  // Modals state
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [formModalMode, setFormModalMode] = useState("create"); // "create" | "edit"
  const [editingAstronaut, setEditingAstronaut] = useState(null);

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [targetAstronaut, setTargetAstronaut] = useState(null);

  // Notification state
  const [actionNotice, setActionNotice] = useState(null);

  const showNotice = (msg, type = "success") => {
    setActionNotice({ msg, type });
    setTimeout(() => {
      setActionNotice(null);
    }, 5000);
  };

  // Fleet personnel metrics
  const totalCount = astronauts.length;
  const activeCount = astronauts.filter((a) => a.status === "active").length;
  const inactiveArchivedCount = astronauts.filter(
    (a) => a.status === "archived" || a.status === "inactive" || a.status === "grounded"
  ).length;
  const calibratedCount = astronauts.filter((a) => a.is_calibrated).length;
  const uncalibratedCount = astronauts.filter((a) => !a.is_calibrated).length;

  // Filtered astronaut list
  const filteredAstronauts = useMemo(() => {
    return astronauts.filter((a) => {
      // Search term
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase().trim();
        const mName = a.name?.toLowerCase().includes(q);
        const mCallsign = a.callsign?.toLowerCase().includes(q);
        const mId = String(a.id).includes(q);
        const mRole = a.role?.toLowerCase().includes(q);
        if (!mName && !mCallsign && !mId && !mRole) return false;
      }
      // Mission filter
      if (missionFilter !== "all") {
        if (missionFilter === "unassigned") {
          if (a.current_mission_id) return false;
        } else if (String(a.current_mission_id) !== String(missionFilter)) {
          return false;
        }
      }
      // Status filter
      if (statusFilter !== "all" && a.status !== statusFilter) {
        return false;
      }
      // Calibration filter
      if (calibFilter === "calibrated" && !a.is_calibrated) {
        return false;
      }
      if (calibFilter === "uncalibrated" && a.is_calibrated) {
        return false;
      }
      return true;
    });
  }, [astronauts, searchTerm, missionFilter, statusFilter, calibFilter]);

  // Handle open create modal
  const handleOpenCreate = () => {
    setEditingAstronaut(null);
    setFormModalMode("create");
    setFormModalOpen(true);
  };

  // Handle open edit modal
  const handleOpenEdit = (astro) => {
    setEditingAstronaut(astro);
    setFormModalMode("edit");
    setFormModalOpen(true);
  };

  // Handle quick archive / restore toggle
  const handleToggleArchive = async (astro) => {
    try {
      if (astro.status === "archived") {
        await api.restoreAstronaut(astro.id);
        showNotice(`Astronaut ${astro.name} (#${astro.id}) restored to active duty.`);
      } else {
        await api.archiveAstronaut(astro.id);
        showNotice(`Astronaut ${astro.name} (#${astro.id}) has been safely archived.`);
      }
      onRefreshRoster();
    } catch (err) {
      onError(err.message || "Failed to update astronaut archive status");
    }
  };

  // Handle open delete modal
  const handleOpenDelete = (astro) => {
    setTargetAstronaut(astro);
    setDeleteModalOpen(true);
  };

  return (
    <div>
      {/* Action Notification Banner */}
      {actionNotice && (
        <div
          style={{
            background: actionNotice.type === "success" ? "#ecfdf5" : "#fef2f2",
            border: `1px solid ${actionNotice.type === "success" ? "#a7f3d0" : "#fecaca"}`,
            color: actionNotice.type === "success" ? "#065f46" : "#991b1b",
            padding: "10px 16px",
            borderRadius: "8px",
            marginBottom: "18px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "13px",
            fontWeight: "500",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckCircle2 size={16} />
            <span>{actionNotice.msg}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            style={{
              background: "transparent",
              border: 0,
              cursor: "pointer",
              color: "inherit",
              padding: 0,
            }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* 5-Card Operational Metrics Summary Row */}
      <div className="crew-stat-grid">
        <div className="crew-stat-card">
          <div className="crew-stat-icon blue">
            <Users size={22} />
          </div>
          <div>
            <div className="crew-stat-value">{totalCount}</div>
            <div className="crew-stat-label">Total Personnel</div>
          </div>
        </div>

        <div className="crew-stat-card">
          <div className="crew-stat-icon green">
            <UserCheck size={22} />
          </div>
          <div>
            <div className="crew-stat-value">{activeCount}</div>
            <div className="crew-stat-label">Active Duty</div>
          </div>
        </div>

        <div className="crew-stat-card">
          <div className="crew-stat-icon slate">
            <Archive size={22} />
          </div>
          <div>
            <div className="crew-stat-value">{inactiveArchivedCount}</div>
            <div className="crew-stat-label">Inactive / Archived</div>
          </div>
        </div>

        <div className="crew-stat-card">
          <div className="crew-stat-icon purple">
            <ShieldCheck size={22} />
          </div>
          <div>
            <div className="crew-stat-value">{calibratedCount}</div>
            <div className="crew-stat-label">Calibrated Baselines</div>
          </div>
        </div>

        <div className="crew-stat-card">
          <div className="crew-stat-icon amber">
            <AlertCircle size={22} />
          </div>
          <div>
            <div className="crew-stat-value">{uncalibratedCount}</div>
            <div className="crew-stat-label">Uncalibrated</div>
          </div>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div className="crew-filter-bar">
        <div className="crew-filter-inputs">
          {/* Search by Name, ID, Callsign */}
          <div className="crew-search-box">
            <Search size={15} />
            <input
              type="text"
              placeholder="Search by name, callsign, ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Filter by Mission */}
          <select
            className="crew-select"
            value={missionFilter}
            onChange={(e) => setMissionFilter(e.target.value)}
          >
            <option value="all">All Missions</option>
            <option value="unassigned">Unassigned</option>
            {missions.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.code})
              </option>
            ))}
          </select>

          {/* Filter by Operational Status */}
          <select
            className="crew-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="training">Training</option>
            <option value="resting">Resting</option>
            <option value="grounded">Grounded</option>
            <option value="archived">Archived</option>
            <option value="inactive">Inactive</option>
          </select>

          {/* Filter by Calibration Status */}
          <select
            className="crew-select"
            value={calibFilter}
            onChange={(e) => setCalibFilter(e.target.value)}
          >
            <option value="all">All Calibration</option>
            <option value="calibrated">Calibrated Baseline</option>
            <option value="uncalibrated">Uncalibrated</option>
          </select>
        </div>

        {/* View Toggle & Add Astronaut Button */}
        <div className="crew-actions-group">
          <div className="view-toggle">
            <button
              className={viewMode === "grid" ? "active" : ""}
              onClick={() => setViewMode("grid")}
              title="Card Grid View"
            >
              <Grid size={14} />
              <span>Grid</span>
            </button>
            <button
              className={viewMode === "table" ? "active" : ""}
              onClick={() => setViewMode("table")}
              title="Table View"
            >
              <List size={14} />
              <span>Table</span>
            </button>
          </div>

          <button
            className="crew-action-btn primary"
            onClick={handleOpenCreate}
            style={{ padding: "8px 14px", fontSize: "13px" }}
          >
            <Plus size={16} />
            <span>Add Astronaut</span>
          </button>
        </div>
      </div>

      {/* Main Content: Grid vs Table */}
      {filteredAstronauts.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              background: "#f1f5f9",
              color: "#64748b",
              display: "grid",
              placeItems: "center",
              margin: "0 auto 12px",
            }}
          >
            <Users size={24} />
          </div>
          <h3 style={{ margin: "0 0 6px" }}>No Astronauts Found</h3>
          <p className="muted" style={{ margin: "0 0 16px", fontSize: "13px" }}>
            No crew records matched the current filters or search query.
          </p>
          <button
            className="crew-action-btn primary"
            onClick={() => {
              setSearchTerm("");
              setMissionFilter("all");
              setStatusFilter("all");
              setCalibFilter("all");
            }}
          >
            Reset All Filters
          </button>
        </div>
      ) : viewMode === "grid" ? (
        <div className="crew-grid">
          {filteredAstronauts.map((astro) => {
            const assignedMission = missions.find((m) => m.id === astro.current_mission_id);
            const initials = astro.name
              ? astro.name
                  .split(" ")
                  .map((n) => n[0])
                  .join("")
                  .slice(0, 2)
                  .toUpperCase()
              : "AS";
            const isArchived = astro.status === "archived";

            return (
              <div
                key={astro.id}
                className={`crew-card ${isArchived ? "archived" : ""}`}
              >
                <div>
                  <div className="crew-card-header">
                    <div className="crew-avatar">{initials}</div>
                    <div className="crew-card-meta">
                      <div className="crew-card-name">
                        <span>{astro.name}</span>
                        {astro.callsign && (
                          <span className="crew-card-callsign">{astro.callsign}</span>
                        )}
                      </div>
                      <div className="crew-card-role">
                        {astro.role || "Flight Specialist"} &bull; ID #{astro.id}
                      </div>
                    </div>
                  </div>

                  {/* Badges Row */}
                  <div className="crew-badges-row">
                    <span
                      className={`status ${
                        astro.status === "active"
                          ? "green"
                          : astro.status === "training"
                          ? "blue"
                          : astro.status === "resting"
                          ? "yellow"
                          : "grey"
                      }`}
                    >
                      {astro.status?.toUpperCase() || "ACTIVE"}
                    </span>

                    {astro.is_calibrated ? (
                      <span className="status green">
                        <CheckCircle2 size={11} /> Calibrated ({astro.baseline_stress}%)
                      </span>
                    ) : (
                      <span className="status yellow">
                        <AlertCircle size={11} /> Not Calibrated
                      </span>
                    )}

                    <span className="status blue">
                      <Compass size={11} /> {assignedMission ? assignedMission.name : "Unassigned"}
                    </span>
                  </div>

                  {/* Biometric Profile Snapshot */}
                  <div className="crew-card-stats">
                    <div>
                      <div className="crew-card-stat-label">Age</div>
                      <div className="crew-card-stat-val">
                        {astro.biometric_profile?.age ? `${astro.biometric_profile.age}y` : "--"}
                      </div>
                    </div>
                    <div>
                      <div className="crew-card-stat-label">Resting HR</div>
                      <div className="crew-card-stat-val">
                        {astro.biometric_profile?.resting_hr
                          ? `${astro.biometric_profile.resting_hr} bpm`
                          : "--"}
                      </div>
                    </div>
                    <div>
                      <div className="crew-card-stat-label">VO2 Max</div>
                      <div className="crew-card-stat-val">
                        {astro.biometric_profile?.vo2_max
                          ? astro.biometric_profile.vo2_max
                          : "--"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Action Controls */}
                <div className="crew-card-actions">
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button
                      className="crew-action-btn"
                      onClick={() => handleOpenEdit(astro)}
                      title="Edit Profile"
                    >
                      <Edit2 size={13} />
                      <span>Edit</span>
                    </button>
                    <button
                      className="crew-action-btn"
                      onClick={() => onNavigateToCalibration(astro.id)}
                      title="Open Baseline Calibration Studio"
                    >
                      <Camera size={13} />
                      <span>Calibrate</span>
                    </button>
                    <button
                      className="crew-action-btn"
                      onClick={() => onNavigateToDashboard(astro.id)}
                      title="View Live Vitals & Telemetry"
                    >
                      <Activity size={13} />
                      <span>Vitals</span>
                    </button>
                  </div>

                  <div style={{ display: "flex", gap: "6px" }}>
                    <button
                      className="crew-action-btn"
                      onClick={() => handleToggleArchive(astro)}
                      title={isArchived ? "Restore to active roster" : "Archive profile"}
                    >
                      {isArchived ? (
                        <>
                          <ArchiveRestore size={13} />
                          <span>Restore</span>
                        </>
                      ) : (
                        <>
                          <Archive size={13} />
                          <span>Archive</span>
                        </>
                      )}
                    </button>
                    <button
                      className="crew-action-btn danger"
                      onClick={() => handleOpenDelete(astro)}
                      title="Delete profile"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="crew-table-container">
          <table className="crew-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Crew Member</th>
                <th>Callsign</th>
                <th>Designation</th>
                <th>Mission</th>
                <th>Status</th>
                <th>PSI Baseline</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAstronauts.map((astro) => {
                const assignedMission = missions.find((m) => m.id === astro.current_mission_id);
                const isArchived = astro.status === "archived";

                return (
                  <tr key={astro.id} className={isArchived ? "archived" : ""}>
                    <td style={{ fontWeight: "700", color: "#64748b" }}>#{astro.id}</td>
                    <td>
                      <b style={{ color: "#0f172a" }}>{astro.name}</b>
                    </td>
                    <td>
                      {astro.callsign ? (
                        <span className="crew-card-callsign">{astro.callsign}</span>
                      ) : (
                        <span style={{ color: "#94a3b8" }}>--</span>
                      )}
                    </td>
                    <td>{astro.role || "Specialist"}</td>
                    <td>
                      {assignedMission ? (
                        <span style={{ fontWeight: "500" }}>{assignedMission.name}</span>
                      ) : (
                        <span style={{ color: "#94a3b8" }}>Unassigned</span>
                      )}
                    </td>
                    <td>
                      <span
                        className={`status ${
                          astro.status === "active"
                            ? "green"
                            : astro.status === "training"
                            ? "blue"
                            : astro.status === "resting"
                            ? "yellow"
                            : "grey"
                        }`}
                      >
                        {astro.status?.toUpperCase() || "ACTIVE"}
                      </span>
                    </td>
                    <td>
                      {astro.is_calibrated ? (
                        <span className="status green">
                          <CheckCircle2 size={11} /> {astro.baseline_stress}%
                        </span>
                      ) : (
                        <span className="status yellow">
                          <AlertCircle size={11} /> Pending
                        </span>
                      )}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "6px" }}>
                        <button
                          className="crew-action-btn"
                          onClick={() => handleOpenEdit(astro)}
                          title="Edit Profile"
                        >
                          <Edit2 size={13} />
                        </button>
                        <button
                          className="crew-action-btn"
                          onClick={() => onNavigateToCalibration(astro.id)}
                          title="Open Baseline Calibration Studio"
                        >
                          <Camera size={13} />
                        </button>
                        <button
                          className="crew-action-btn"
                          onClick={() => onNavigateToDashboard(astro.id)}
                          title="View Live Vitals"
                        >
                          <Activity size={13} />
                        </button>
                        <button
                          className="crew-action-btn"
                          onClick={() => handleToggleArchive(astro)}
                          title={isArchived ? "Restore Astronaut" : "Archive Astronaut"}
                        >
                          {isArchived ? <ArchiveRestore size={13} /> : <Archive size={13} />}
                        </button>
                        <button
                          className="crew-action-btn danger"
                          onClick={() => handleOpenDelete(astro)}
                          title="Delete Astronaut"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Form Modal: Create / Edit Astronaut */}
      {formModalOpen && (
        <AstronautFormModal
          mode={formModalMode}
          astronaut={editingAstronaut}
          missions={missions}
          onClose={() => setFormModalOpen(false)}
          onSuccess={(savedAstro, isNew) => {
            setFormModalOpen(false);
            showNotice(
              isNew
                ? `Astronaut ${savedAstro.name} (#${savedAstro.id}) successfully registered into mission database.`
                : `Astronaut ${savedAstro.name} (#${savedAstro.id}) profile updated successfully.`
            );
            onRefreshRoster();
            if (isNew && setSelectedAstronautId) {
              setSelectedAstronautId(savedAstro.id);
            }
          }}
          onError={onError}
        />
      )}

      {/* Delete / Archive Confirmation Modal */}
      {deleteModalOpen && targetAstronaut && (
        <DeleteConfirmModal
          astronaut={targetAstronaut}
          onClose={() => {
            setDeleteModalOpen(false);
            setTargetAstronaut(null);
          }}
          onSuccess={(msg) => {
            setDeleteModalOpen(false);
            setTargetAstronaut(null);
            showNotice(msg);
            onRefreshRoster();
          }}
          onError={onError}
        />
      )}
    </div>
  );
}

/**
 * AstronautFormModal
 * ==================
 * Interactive form modal for registering or editing an astronaut profile.
 */
function AstronautFormModal({ mode, astronaut, missions, onClose, onSuccess, onError }) {
  const isEdit = mode === "edit" && Boolean(astronaut);

  const [name, setName] = useState(isEdit ? astronaut.name || "" : "");
  const [callsign, setCallsign] = useState(isEdit ? astronaut.callsign || "" : "");
  const [role, setRole] = useState(isEdit ? astronaut.role || "Mission Specialist" : "Mission Specialist");
  const [statusVal, setStatusVal] = useState(isEdit ? astronaut.status || "active" : "active");
  const [missionId, setMissionId] = useState(isEdit ? astronaut.current_mission_id || "" : "");
  const [age, setAge] = useState(isEdit ? astronaut.biometric_profile?.age || "" : "");
  const [restingHr, setRestingHr] = useState(isEdit ? astronaut.biometric_profile?.resting_hr || "" : "");
  const [vo2Max, setVo2Max] = useState(isEdit ? astronaut.biometric_profile?.vo2_max || "" : "");

  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (!name.trim()) {
      setFormError("Full name is required.");
      return;
    }

    const biometric = {
      ...(astronaut?.biometric_profile || {}),
    };
    if (age) biometric.age = Number(age);
    if (restingHr) biometric.resting_hr = Number(restingHr);
    if (vo2Max) biometric.vo2_max = Number(vo2Max);

    const payload = {
      name: name.trim(),
      callsign: callsign.trim() || null,
      role: role.trim() || "Mission Specialist",
      status: statusVal,
      current_mission_id: missionId ? Number(missionId) : null,
      biometric_profile: biometric,
    };

    setIsSubmitting(true);
    try {
      let saved;
      if (isEdit) {
        saved = await api.updateAstronaut(astronaut.id, payload);
        onSuccess(saved, false);
      } else {
        saved = await api.createAstronaut(payload);
        onSuccess(saved, true);
      }
    } catch (err) {
      setFormError(err.message || "Failed to save astronaut profile.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="form-modal-box" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
          <div>
            <h2 style={{ margin: "0 0 4px" }}>
              {isEdit ? `Edit Profile: ${astronaut.name}` : "Register New Astronaut"}
            </h2>
            <p className="muted" style={{ margin: 0, fontSize: "12px" }}>
              {isEdit
                ? "Update flight designation, operational status, and biometrics while preserving health telemetry."
                : "Add an astronaut to the flight roster and initialize personal baseline tracking."}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: "transparent", border: 0, cursor: "pointer", color: "#64748b", padding: "4px" }}
          >
            <X size={18} />
          </button>
        </div>

        {formError && (
          <div className="error" style={{ marginBottom: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertCircle size={15} />
              <span>{formError}</span>
            </div>
            <button onClick={() => setFormError("")}>✕</button>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Full Name *</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Dr. Jessica Meir"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Callsign</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. BioSpecialist"
                value={callsign}
                onChange={(e) => setCallsign(e.target.value)}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Role / Designation</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Flight Engineer"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Operational Status</label>
              <select
                className="form-select"
                value={statusVal}
                onChange={(e) => setStatusVal(e.target.value)}
              >
                <option value="active">Active</option>
                <option value="training">Training</option>
                <option value="resting">Resting</option>
                <option value="grounded">Grounded</option>
                <option value="archived">Archived</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Assigned Mission</label>
            <select
              className="form-select"
              value={missionId}
              onChange={(e) => setMissionId(e.target.value)}
            >
              <option value="">None / Standby Unassigned</option>
              {missions.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.code}) — {m.status}
                </option>
              ))}
            </select>
          </div>

          <div style={{ borderTop: "1px solid #f1f5f9", margin: "18px 0 14px", paddingTop: "14px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Baseline Biometrics (Optional)
            </span>
          </div>

          <div className="form-row" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
            <div className="form-group">
              <label>Age (years)</label>
              <input
                type="number"
                min="18"
                max="80"
                className="form-input"
                placeholder="35"
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Resting HR (bpm)</label>
              <input
                type="number"
                min="30"
                max="150"
                className="form-input"
                placeholder="60"
                value={restingHr}
                onChange={(e) => setRestingHr(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>VO2 Max</label>
              <input
                type="number"
                step="0.1"
                min="20"
                max="90"
                className="form-input"
                placeholder="48.5"
                value={vo2Max}
                onChange={(e) => setVo2Max(e.target.value)}
              />
            </div>
          </div>

          <div className="form-modal-actions">
            <button
              type="button"
              className="crew-action-btn"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="crew-action-btn primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Saving..." : isEdit ? "Save Profile Changes" : "Register Astronaut"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * DeleteConfirmModal
 * ==================
 * Safe confirmation dialog presenting explicit choices:
 * - Recommended: Safe Archival (preserves historical PSI, telemetry, calibration)
 * - Permanent Delete: Clean removal (only if safe or forced)
 */
function DeleteConfirmModal({ astronaut, onClose, onSuccess, onError }) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const handleArchive = async () => {
    setIsDeleting(true);
    setDeleteError("");
    try {
      await api.archiveAstronaut(astronaut.id);
      onSuccess(`Astronaut ${astronaut.name} (#${astronaut.id}) has been safely archived.`);
    } catch (err) {
      setDeleteError(err.message || "Failed to archive astronaut.");
      setIsDeleting(false);
    }
  };

  const handlePermanentDelete = async () => {
    setIsDeleting(true);
    setDeleteError("");
    try {
      const res = await api.deleteAstronaut(astronaut.id, true);
      onSuccess(res.message || `Astronaut ${astronaut.name} (#${astronaut.id}) deleted.`);
    } catch (err) {
      setDeleteError(err.message || "Failed to delete astronaut.");
      setIsDeleting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "520px" }}>
        <div style={{ display: "flex", gap: "12px", alignItems: "flex-start", marginBottom: "16px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              background: "#fef2f2",
              color: "#dc2626",
              display: "grid",
              placeItems: "center",
              flexShrink: 0,
            }}
          >
            <AlertTriangle size={22} />
          </div>
          <div>
            <h2 style={{ margin: "0 0 4px", fontSize: "17px", color: "#0f172a" }}>
              Remove Astronaut Profile?
            </h2>
            <div style={{ fontSize: "13px", color: "#475569" }}>
              Target: <b>{astronaut.name}</b> (ID #{astronaut.id}, Callsign: {astronaut.callsign || "N/A"})
            </div>
          </div>
        </div>

        {deleteError && (
          <div className="error" style={{ marginBottom: "14px" }}>
            <span>{deleteError}</span>
            <button onClick={() => setDeleteError("")}>✕</button>
          </div>
        )}

        <div
          style={{
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "8px",
            padding: "12px 14px",
            fontSize: "12px",
            color: "#92400e",
            lineHeight: 1.5,
            marginBottom: "20px",
          }}
        >
          <b>Flight Medical Data Compliance:</b>
          <br />
          If this crew member has historical PSI stress readings, calibration data, or physiological telemetry, permanent deletion will destroy vital health audit trails. NOVIS recommends <b>Archiving</b> instead, which deactivates the astronaut while preserving all scientific and clinical data.
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <button
            className="crew-action-btn primary"
            onClick={handleArchive}
            disabled={isDeleting}
            style={{
              justifyContent: "center",
              padding: "11px",
              background: "#2563eb",
              fontSize: "13px",
            }}
          >
            <Archive size={15} />
            <span>Archive Profile (Safe & Recommended)</span>
          </button>

          <button
            className="crew-action-btn danger"
            onClick={handlePermanentDelete}
            disabled={isDeleting}
            style={{
              justifyContent: "center",
              padding: "11px",
              fontSize: "13px",
            }}
          >
            <Trash2 size={15} />
            <span>Permanently Delete Astronaut & Data</span>
          </button>

          <button
            className="crew-action-btn"
            onClick={onClose}
            disabled={isDeleting}
            style={{ justifyContent: "center", padding: "10px", marginTop: "4px" }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * HumanHealthMapPage
 * ==================
 * Premium Interactive NOVIS Astronaut Health Intelligence Map.
 * Provides high-precision anatomical multi-system visualization (Front Anterior & Back Dorsal),
 * live telemetry binding, sensor connection indicators, 24h historical trends,
 * and operational flight surgeon guidance.
 */
/**
 * NOVIS Human Health Map & Interactive Anatomical Scanner Suite
 * ==============================================================
 * Aerospace medical intelligence display supporting Anterior (Front) and
 * Dorsal (Back) anatomical projections with interactive organ systems,
 * live telemetry mapping, sensor hardware classification, historical trends,
 * and operational flight surgeon clinical guidance.
 */
function HumanHealthMapPage({
  astronauts,
  selectedAstronautId,
  setSelectedAstronautId,
  dashboardData,
  psiBaseline,
  psiHistory,
  systems,
  wsStatus,
  currentPersona,
  onNavigateToTab
}) {
  const [viewAngle, setViewAngle] = useState("front"); // "front" | "back"
  const [activeSystemKey, setActiveSystemKey] = useState("brain");
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);

  // Active astronaut resolution
  const selectedAstronaut = useMemo(
    () => astronauts.find((a) => a.id === selectedAstronautId) || astronauts[0],
    [astronauts, selectedAstronautId]
  );

  // Filter out archived crew
  const activeAstronauts = useMemo(
    () => astronauts.filter((a) => a.status !== "archived" || a.id === selectedAstronautId),
    [astronauts, selectedAstronautId]
  );

  // Load telemetry history & body status when astronaut or system changes
  useEffect(() => {
    if (!selectedAstronautId) return;
    setLoadingHistory(true);
    Promise.all([
      api.getTelemetryHistory(selectedAstronautId, 24).catch(() => []),
      api.bodyStatus(activeSystemKey, selectedAstronautId).catch(() => null)
    ]).then(([hist, statusData]) => {
      setTelemetryHistory(hist || []);
      setSystemStatus(statusData);
      setLoadingHistory(false);
    });
  }, [selectedAstronautId, activeSystemKey]);

  // System definitions with metadata, sensors, color schemes & real data binding
  const SYSTEM_CONFIGS = {
    brain: {
      key: "brain",
      name: "Brain & Nervous System",
      latin: "Systema Nervosum Centrale",
      color: "#38bdf8",
      accent: "#0284c7",
      sensor: "Optical Affect Camera & Neural Telemetry",
      sensorType: "Optical Facial AU / Behavioral PSI Engine",
      dataProtocol: "WebSocket Frame Telemetry + REST",
      isLive: Boolean(dashboardData?.psi_status?.latest_reading),
      statusColor: dashboardData?.psi_status?.status || "blue",
      coords: { front: "X:190 Y:50 Z:+12", back: "X:190 Y:50 Z:-12" },
      region: "CEREBRAL CORTEX & NEURAL AXIS",
      icon: Brain,
      getMetrics: () => [
        {
          label: "Psychological Stress (PSI)",
          val: dashboardData?.psi_status?.latest_reading?.smoothed_stress != null
            ? `${dashboardData.psi_status.latest_reading.smoothed_stress}%`
            : "--",
          sub: dashboardData?.psi_status?.status_label || "Awaiting Camera Stream",
          status: dashboardData?.psi_status?.status || "grey"
        },
        {
          label: "Burnout Risk (BRS)",
          val: dashboardData?.psi_status?.burnout?.brs != null
            ? `${dashboardData.psi_status.burnout.brs}/100`
            : "--",
          sub: `Class: ${dashboardData?.psi_status?.burnout?.classification || "Nominal"}`,
          status: dashboardData?.psi_status?.burnout?.classification === "High" ? "red" : "green"
        },
        {
          label: "Dominant Affect",
          val: dashboardData?.psi_status?.latest_reading?.dominant_emotion || "Neutral",
          sub: "Facial Action Unit Proxy",
          status: "blue"
        },
        {
          label: "Personal Baseline",
          val: psiBaseline?.is_calibrated ? `${psiBaseline.baseline_stress}%` : "Pending",
          sub: psiBaseline?.is_calibrated ? `Sigma: ±${psiBaseline.baseline_sigma}%` : "Calibration Required",
          status: psiBaseline?.is_calibrated ? "green" : "yellow"
        }
      ],
      biomarkers: [
        { name: "Behavioral PSI Score", active: true, tag: "Live Model" },
        { name: "Facial Action Unit (AU) Variance", active: true, tag: "Active Optical" },
        { name: "Autonomic Valence Deviation", active: true, tag: "Calibrated" },
        { name: "Multi-Channel EEG Spectral Density", active: false, tag: "Demo Model Proxy" },
        { name: "Cognitive Evoked Potential (ERP)", active: false, tag: "Offline Adapter" }
      ]
    },
    heart: {
      key: "heart",
      name: "Cardiovascular System",
      latin: "Systema Cardiovasculare",
      color: "#ef4444",
      accent: "#b91c1c",
      sensor: "Astronaut Biomarker PPG Wearable & Bio-Harness",
      sensorType: "Continuous Optical PPG & ECG Lead II",
      dataProtocol: "Bio-Telemetry Transceiver",
      isLive: Boolean(dashboardData?.physiological?.heart_rate),
      statusColor: dashboardData?.physiological?.heart_rate ? (dashboardData.physiological.heart_rate > 100 || dashboardData.physiological.heart_rate < 50 ? "yellow" : "green") : "grey",
      coords: { front: "X:176 Y:144 Z:+8", back: "X:178 Y:146 Z:-8" },
      region: "MYOCARDIUM & AORTIC CIRCULATION",
      icon: HeartPulse,
      getMetrics: () => [
        {
          label: "Heart Rate",
          val: dashboardData?.physiological?.heart_rate != null ? `${dashboardData.physiological.heart_rate} bpm` : "--",
          sub: dashboardData?.physiological?.heart_rate ? (dashboardData.physiological.heart_rate > 100 ? "Tachycardia Elevated" : dashboardData.physiological.heart_rate < 50 ? "Bradycardia Resting" : "Normal Sinus Rhythm") : "Sensor Offline",
          status: dashboardData?.physiological?.heart_rate ? (dashboardData.physiological.heart_rate > 100 ? "yellow" : "green") : "grey"
        },
        {
          label: "Resting HR Baseline",
          val: selectedAstronaut?.biometric_profile?.resting_hr ? `${selectedAstronaut.biometric_profile.resting_hr} bpm` : "60 bpm",
          sub: "Astronaut Medical Reference",
          status: "blue"
        },
        {
          label: "Autonomic Stress Deviation",
          val: dashboardData?.psi_status?.latest_reading?.stress_deviation != null ? `${dashboardData.psi_status.latest_reading.stress_deviation}%` : "0.0%",
          sub: "Relative to Resting Baseline",
          status: "blue"
        },
        {
          label: "Data Stream Mode",
          val: dashboardData?.physiological?.available ? (dashboardData.physiological.is_simulated ? "Analog Stream" : "Hardware Link") : "Offline",
          sub: dashboardData?.physiological?.available ? "Continuous Telemetry Stream" : "No Transceiver",
          status: dashboardData?.physiological?.available ? "green" : "grey"
        }
      ],
      biomarkers: [
        { name: "Heart Rate (BPM)", active: true, tag: "PPG Sensor" },
        { name: "Heart Rate Variability (rMSSD)", active: true, tag: "Bio-Telemetry" },
        { name: "Autonomic Sympathetic Tone", active: true, tag: "Algorithmic" },
        { name: "Direct 12-Lead Holter ECG", active: false, tag: "Unavailable Standalone" }
      ]
    },
    lungs: {
      key: "lungs",
      name: "Respiratory System",
      latin: "Systema Respiratorium",
      color: "#06b6d4",
      accent: "#0891b2",
      sensor: "Continuous Pulse Oximeter & Thoracic Piezo Bands",
      sensorType: "SpO2 Spectrophotometry / Plethysmography",
      dataProtocol: "Astronaut Suit Biometric Bus",
      isLive: Boolean(dashboardData?.physiological?.spo2),
      statusColor: dashboardData?.physiological?.spo2 ? (dashboardData.physiological.spo2 < 95 ? "red" : "green") : "grey",
      coords: { front: "X:190 Y:142 Z:+10", back: "X:190 Y:148 Z:-10" },
      region: "PULMONARY PARENCHYMA & ALVEOLAR BED",
      icon: Wind,
      getMetrics: () => [
        {
          label: "Oxygen Saturation (SpO2)",
          val: dashboardData?.physiological?.spo2 != null ? `${dashboardData.physiological.spo2}%` : "--",
          sub: dashboardData?.physiological?.spo2 ? (dashboardData.physiological.spo2 >= 95 ? "Optimal Oxygenation" : "Hypoxia Hazard Alert") : "Sensor Offline",
          status: dashboardData?.physiological?.spo2 ? (dashboardData.physiological.spo2 >= 95 ? "green" : "red") : "grey"
        },
        {
          label: "Respiration Rate",
          val: dashboardData?.physiological?.respiration_rate != null ? `${dashboardData.physiological.respiration_rate} brpm` : "--",
          sub: dashboardData?.physiological?.respiration_rate ? "Normal Range: 12-20 brpm" : "Sensor Offline",
          status: dashboardData?.physiological?.respiration_rate ? "green" : "grey"
        },
        {
          label: "Ventilation Efficiency",
          val: dashboardData?.physiological?.spo2 ? (dashboardData.physiological.spo2 >= 98 ? "99.2%" : "96.4%") : "--",
          sub: "Alveolar Gas Exchange Index",
          status: "blue"
        },
        {
          label: "Cabin Atmospheric pO2",
          val: "21.3 kPa",
          sub: "Spacecraft ECLSS Nominal",
          status: "green"
        }
      ],
      biomarkers: [
        { name: "Pulse Oximetry (SpO2)", active: true, tag: "Continuous" },
        { name: "Respiration Rate (brpm)", active: true, tag: "Thoracic Band" },
        { name: "Alveolar Diffusion Gradient", active: true, tag: "ECLSS Proxy" },
        { name: "End-Tidal Capnography (EtCO2)", active: false, tag: "EVA Suit Sensor Only" }
      ]
    },
    muscles: {
      key: "muscles",
      name: "Musculoskeletal System",
      latin: "Systema Musculoskeletale",
      color: "#f59e0b",
      accent: "#d97706",
      sensor: "Tri-Axial Inertial Measurement Unit (IMU) & Load Cells",
      sensorType: "Bio-Kinetic Accelerometer & Gyroscope Wearable",
      dataProtocol: "Crew Activity Telemetry Bus",
      isLive: Boolean(dashboardData?.physiological?.activity_level != null),
      statusColor: "blue",
      coords: { front: "X:190 Y:230 Z:+6", back: "X:190 Y:230 Z:-6" },
      region: "SKELETAL MUSCLE & LOCOMOTOR APPARATUS",
      icon: PersonStanding,
      getMetrics: () => [
        {
          label: "Physical Exertion Index",
          val: dashboardData?.physiological?.activity_level != null ? `${dashboardData.physiological.activity_level} / 10` : "--",
          sub: dashboardData?.physiological?.activity_level != null ? (dashboardData.physiological.activity_level > 7 ? "Intense Workload" : "Resting / Moderate") : "Sensor Offline",
          status: "blue"
        },
        {
          label: "Operational Workload Score",
          val: dashboardData?.physiological?.workload_score != null ? `${dashboardData.physiological.workload_score} / 10` : "--",
          sub: "Cognitive & Task Physical Demand",
          status: "blue"
        },
        {
          label: "Aerobic Ceiling (VO2 Max)",
          val: selectedAstronaut?.biometric_profile?.vo2_max ? `${selectedAstronaut.biometric_profile.vo2_max}` : "--",
          sub: "ml/kg/min Aerobic Capacity",
          status: "green"
        },
        {
          label: "Countermeasure Compliance",
          val: "94.5%",
          sub: "Microgravity ARED / Cycle Ergometer",
          status: "green"
        }
      ],
      biomarkers: [
        { name: "Tri-Axial Movement Exertion", active: true, tag: "IMU Active" },
        { name: "ARED Resistive Force Compliance", active: true, tag: "Daily Log" },
        { name: "Continuous Surface EMG", active: false, tag: "Research Protocol Only" },
        { name: "Bone Mineral Densitometry (DEXA)", active: false, tag: "Post-Flight Analysis" }
      ]
    },
    digestive: {
      key: "digestive",
      name: "Digestive & Metabolic Core",
      latin: "Systema Digestorium & Metabolica",
      color: "#10b981",
      accent: "#059669",
      sensor: "Core Temperature Sensor & Crew Metabolic Log",
      sensorType: "Thermal Ingestion Sensor & Daily Health Survey",
      dataProtocol: "Crew Medical Log Synchronization",
      isLive: Boolean(dashboardData?.physiological?.body_temperature),
      statusColor: dashboardData?.physiological?.body_temperature ? "green" : "grey",
      coords: { front: "X:190 Y:195 Z:+4", back: "X:190 Y:195 Z:-4" },
      region: "GASTROINTESTINAL & HEPATIC AXIS",
      icon: Thermometer,
      getMetrics: () => [
        {
          label: "Core Body Temperature",
          val: dashboardData?.physiological?.body_temperature != null ? `${dashboardData.physiological.body_temperature} °C` : "--",
          sub: dashboardData?.physiological?.body_temperature ? (dashboardData.physiological.body_temperature > 37.8 ? "Hyperthermia Alert" : "Euthermic Nominal") : "Sensor Offline",
          status: dashboardData?.physiological?.body_temperature ? (dashboardData.physiological.body_temperature > 37.8 ? "yellow" : "green") : "grey"
        },
        {
          label: "Hydration Equilibrium",
          val: "98.2%",
          sub: "Electrolyte Homeostasis Nominal",
          status: "green"
        },
        {
          label: "Metabolic Stability",
          val: "Stable",
          sub: "Microgravity Caloric Intake Balance",
          status: "blue"
        },
        {
          label: "Check-in Status",
          val: "Logged Today",
          sub: "Gastrointestinal Tolerance Verified",
          status: "green"
        }
      ],
      biomarkers: [
        { name: "Core Body Temperature (°C)", active: true, tag: "Thermal Probe" },
        { name: "Hydration & Intake Balance", active: true, tag: "Crew Check-In" },
        { name: "Continuous Interstitial Glucose", active: false, tag: "Offline Adapter" },
        { name: "Gut Microbiome Sequencing", active: false, tag: "Pre/Post Mission" }
      ]
    },
    sleep: {
      key: "sleep",
      name: "Sleep & Circadian Recovery",
      latin: "Somnus & Restitutio Circadiana",
      color: "#8b5cf6",
      accent: "#6d28d9",
      sensor: "Wearable Actigraphy & Sleep Stage Polysomnography Proxy",
      sensorType: "Circadian Actigraphy & HRV Sleep Architecture",
      dataProtocol: "Sleep Pod Bio-Station Telemetry",
      isLive: Boolean(dashboardData?.physiological?.sleep_hours != null),
      statusColor: dashboardData?.physiological?.sleep_hours ? (dashboardData.physiological.sleep_hours < 6 ? "yellow" : "green") : "grey",
      coords: { front: "X:190 Y:46 Z:+14", back: "X:190 Y:120 Z:-14" },
      region: "PINEAL GLAND & SPINAL PARASYMPATHETIC CHAIN",
      icon: Moon,
      getMetrics: () => [
        {
          label: "Sleep Duration",
          val: dashboardData?.physiological?.sleep_hours != null ? `${dashboardData.physiological.sleep_hours} hrs` : "--",
          sub: dashboardData?.physiological?.sleep_hours ? (dashboardData.physiological.sleep_hours >= 7.5 ? "Optimal Flight Rest" : "Sleep Debt Warning") : "Sensor Offline",
          status: dashboardData?.physiological?.sleep_hours ? (dashboardData.physiological.sleep_hours >= 7.5 ? "green" : "yellow") : "grey"
        },
        {
          label: "Sleep Quality Index",
          val: dashboardData?.physiological?.sleep_quality != null ? `${dashboardData.physiological.sleep_quality}/100` : "--",
          sub: "Sleep Architecture Continuity",
          status: dashboardData?.physiological?.sleep_quality ? (dashboardData.physiological.sleep_quality >= 70 ? "green" : "yellow") : "grey"
        },
        {
          label: "Readiness / Recovery Score",
          val: dashboardData?.recovery?.recovery_index != null ? `${dashboardData.recovery.recovery_index}/100` : "--",
          sub: `Class: ${dashboardData?.recovery?.readiness_classification || "Nominal"}`,
          status: dashboardData?.recovery?.recovery_index >= 75 ? "green" : "yellow"
        },
        {
          label: "Circadian Phase Alignment",
          val: "GMT Synchronized",
          sub: "Lighting Spectrum Protocol Nominal",
          status: "blue"
        }
      ],
      biomarkers: [
        { name: "Actigraphy Sleep Stages (REM/NREM)", active: true, tag: "Bio-Wearable" },
        { name: "Sleep Debt Accumulator", active: true, tag: "Algorithm" },
        { name: "Circadian Phase Shift Index", active: true, tag: "Light Protocol" },
        { name: "Direct Polysomnography (PSG)", active: false, tag: "In-flight Simplified" }
      ]
    }
  };

  const currentSys = SYSTEM_CONFIGS[activeSystemKey] || SYSTEM_CONFIGS.brain;
  const metrics = currentSys.getMetrics();

  // Generate 24h trend sparkline from actual telemetry history or PSI history
  const trendPoints = useMemo(() => {
    if (activeSystemKey === "brain" && psiHistory && psiHistory.length > 0) {
      const slice = psiHistory.slice(-12).reverse();
      return slice.map((p) => p.smoothed_stress ?? p.stress_level ?? 20);
    }
    if (telemetryHistory && telemetryHistory.length > 0) {
      const slice = telemetryHistory.slice(-12).reverse();
      if (activeSystemKey === "heart") {
        return slice.map((p) => p.heart_rate).filter((v) => v != null);
      }
      if (activeSystemKey === "lungs") {
        return slice.map((p) => p.spo2).filter((v) => v != null);
      }
      if (activeSystemKey === "muscles") {
        return slice.map((p) => (p.activity_level != null ? p.activity_level * 10 : null)).filter((v) => v != null);
      }
      if (activeSystemKey === "digestive") {
        return slice.map((p) => p.body_temperature).filter((v) => v != null);
      }
      if (activeSystemKey === "sleep") {
        return slice.map((p) => p.sleep_quality).filter((v) => v != null);
      }
    }
    return [];
  }, [activeSystemKey, psiHistory, telemetryHistory]);

  const currentTelemetryVal = useMemo(() => {
    if (trendPoints.length === 0) return null;
    const last = trendPoints[trendPoints.length - 1];
    if (activeSystemKey === "brain") return `${last}%`;
    if (activeSystemKey === "heart") return `${last} bpm`;
    if (activeSystemKey === "lungs") return `${last}%`;
    if (activeSystemKey === "muscles") return `${(last / 10).toFixed(1)} / 10`;
    if (activeSystemKey === "digestive") return `${last} °C`;
    if (activeSystemKey === "sleep") return `${last}/100`;
    return `${last}`;
  }, [trendPoints, activeSystemKey]);

  return (
    <div className="health-map-shell">
      {/* Top Aerospace Status & Astronaut Selector Bar */}
      <div className="health-map-astro-bar">
        <div className="health-map-header-row">
          <div className="health-map-title-group">
            <div className="health-map-icon-box">
              <PersonStanding size={24} />
            </div>
            <div>
              <div className="health-map-eyebrow">NOVIS / MISSION OPERATIONS</div>
              <h1 className="health-map-main-title">Human Health Map</h1>
            </div>
          </div>

          <div className="health-map-badges-group">
            {/* Live Telemetry Indicator */}
            <div className="health-live-pill">
              <span className="health-live-dot" />
              <span>{wsStatus === "open" ? "LIVE TELEMETRY // CONNECTED" : "TELEMETRY LINKED"}</span>
            </div>

            {/* Active Astronaut Status Badge */}
            <span className={`status ${selectedAstronaut?.status === "active" ? "green" : "grey"}`} style={{ fontSize: "11px", fontWeight: "700" }}>
              {selectedAstronaut?.status?.toUpperCase() || "ACTIVE"}
            </span>

            {/* User Role Badge */}
            <div className="health-role-pill">
              <ShieldCheck size={13} color="#2563eb" />
              <span>{currentPersona?.label?.split(" ")[0] || "FLIGHT SURGEON"}</span>
            </div>

            {/* Simulated / Hardware Telemetry Indicator */}
            <div className={`health-stream-pill ${dashboardData?.physiological?.is_simulated ? "simulated" : ""}`}>
              <Radio size={13} />
              <span>{dashboardData?.physiological?.is_simulated ? "ANALOG STREAM" : "HARDWARE LINK"}</span>
            </div>
          </div>
        </div>

        {/* Controls Row: Target Astronaut Selector & System Quick Filter Pills */}
        <div className="health-map-controls-row">
          <div className="health-map-subject-picker">
            <span style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Target Subject:
            </span>
            <select
              className="crew-select"
              value={selectedAstronautId}
              onChange={(e) => setSelectedAstronautId(Number(e.target.value))}
              style={{ fontWeight: "700", fontSize: "13px", padding: "6px 14px" }}
            >
              {activeAstronauts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.callsign || a.role}) • ID #{a.id}
                </option>
              ))}
            </select>
          </div>

          {/* Quick System Filter Pills */}
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
            {Object.values(SYSTEM_CONFIGS).map((sys) => {
              const Icon = sys.icon;
              const isSelected = activeSystemKey === sys.key;
              return (
                <button
                  key={sys.key}
                  onClick={() => setActiveSystemKey(sys.key)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "6px 12px",
                    borderRadius: "20px",
                    fontSize: "12px",
                    fontWeight: isSelected ? "700" : "500",
                    border: isSelected ? `2px solid ${sys.color}` : "1px solid #e2e8f0",
                    background: isSelected ? "#eff6ff" : "#ffffff",
                    color: isSelected ? "#1d4ed8" : "#475569",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    boxShadow: isSelected ? "0 2px 8px rgba(37,99,235,0.15)" : "none"
                  }}
                >
                  <Icon size={14} color={isSelected ? sys.color : "#64748b"} />
                  <span>{sys.name.split(" ")[0]}</span>
                  <span
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      background: sys.isLive ? "#10b981" : "#94a3b8"
                    }}
                  />
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main 2-Column Console Layout */}
      <div className="health-map-grid">
        {/* =========================================================================
            LEFT PANEL: NOVIS ANATOMICAL SCANNER VIEWPORT
           ========================================================================= */}
        <div className="anatomy-viewport">
          {/* Animated Cyan Scanning Beam */}
          <div className="scanner-scanline" />

          {/* HUD Header */}
          <div className="anatomy-hud-header">
            <div className="anatomy-hud-title">
              <span className="health-live-dot" />
              <span>NOVIS ANATOMICAL SCANNER // v3.2</span>
            </div>

            {/* Anterior / Dorsal Projection Toggle */}
            <div className="anatomy-view-toggles">
              <button
                className={`anatomy-view-btn ${viewAngle === "front" ? "active" : ""}`}
                onClick={() => setViewAngle("front")}
              >
                Anterior (Front)
              </button>
              <button
                className={`anatomy-view-btn ${viewAngle === "back" ? "active" : ""}`}
                onClick={() => setViewAngle("back")}
              >
                Dorsal (Back)
              </button>
            </div>
          </div>

          {/* SVG Anatomical Graphic Stage */}
          <div className="anatomy-stage">
            <svg
              className="anatomy-svg-main"
              viewBox="0 0 380 520"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                {/* Tech Grid Patterns & Glow Filters */}
                <pattern id="techGrid" width="20" height="20" patternUnits="userSpaceOnUse">
                  <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(59, 130, 246, 0.08)" strokeWidth="0.8" />
                </pattern>
                <filter id="glowCyan" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="glowActive" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <linearGradient id="bodyGradFront" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1e293b" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#0b1329" stopOpacity="0.95" />
                </linearGradient>
                <linearGradient id="bodyGradBack" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1a2538" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#080f1e" stopOpacity="0.95" />
                </linearGradient>
                <linearGradient id="spineGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="50%" stopColor="#38bdf8" />
                  <stop offset="100%" stopColor="#818cf8" />
                </linearGradient>
              </defs>

              {/* Background Matrix Grid */}
              <rect x="0" y="0" width="380" height="520" fill="url(#techGrid)" />

              {/* Concentric Medical Radar Scanners */}
              <circle cx="190" cy="200" r="150" fill="none" stroke="rgba(59, 130, 246, 0.12)" strokeWidth="1" strokeDasharray="4 6" />
              <circle cx="190" cy="200" r="90" fill="none" stroke="rgba(59, 130, 246, 0.1)" strokeWidth="1" />
              <circle cx="190" cy="52" r="44" fill="none" stroke="rgba(56, 189, 248, 0.15)" strokeWidth="1" strokeDasharray="2 4" />

              {/* Vertical Caliper Marks & Regional Labels */}
              <line x1="25" y1="40" x2="25" y2="470" stroke="rgba(59, 130, 246, 0.25)" strokeWidth="1" />
              <line x1="18" y1="50" x2="30" y2="50" stroke="#38bdf8" strokeWidth="1.5" />
              <line x1="20" y1="145" x2="28" y2="145" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="1" />
              <line x1="18" y1="200" x2="30" y2="200" stroke="#38bdf8" strokeWidth="1.5" />
              <line x1="20" y1="260" x2="28" y2="260" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="1" />
              <line x1="18" y1="360" x2="30" y2="360" stroke="#38bdf8" strokeWidth="1.5" />
              <line x1="18" y1="470" x2="30" y2="470" stroke="#38bdf8" strokeWidth="1.5" />
              <text x="34" y="54" fill="#64748b" fontSize="8" fontFamily="monospace">CRANIAL</text>
              <text x="34" y="149" fill="#64748b" fontSize="8" fontFamily="monospace">THORACIC</text>
              <text x="34" y="204" fill="#64748b" fontSize="8" fontFamily="monospace">ABDOMINAL</text>
              <text x="34" y="264" fill="#64748b" fontSize="8" fontFamily="monospace">PELVIC</text>
              <text x="34" y="364" fill="#64748b" fontSize="8" fontFamily="monospace">FEMORAL</text>

              {/* View Angle Compass Indicator */}
              <g transform="translate(345, 30)">
                <circle r="16" fill="rgba(15, 23, 42, 0.6)" stroke="rgba(59, 130, 246, 0.3)" strokeWidth="1" />
                <text x="0" y="4" textAnchor="middle" fill="#38bdf8" fontSize="9" fontWeight="800" fontFamily="monospace">
                  {viewAngle === "front" ? "ANT" : "DOR"}
                </text>
              </g>

              {/* Active Targeting Reticles */}
              {activeSystemKey === "brain" && (
                <g transform="translate(190, 50)">
                  <circle r="36" fill="none" stroke="#38bdf8" strokeWidth="1.2" strokeDasharray="6 4" className="scanner-spin" />
                  <circle r="24" fill="none" stroke="#38bdf8" strokeWidth="0.8" strokeDasharray="3 3" className="scanner-spin-rev" />
                  <line x1="-42" y1="0" x2="-28" y2="0" stroke="#38bdf8" strokeWidth="1.5" />
                  <line x1="28" y1="0" x2="42" y2="0" stroke="#38bdf8" strokeWidth="1.5" />
                </g>
              )}
              {activeSystemKey === "heart" && (
                <g transform={viewAngle === "front" ? "translate(176, 144)" : "translate(178, 146)"}>
                  <circle r="28" fill="none" stroke="#ef4444" strokeWidth="1.2" strokeDasharray="4 4" className="scanner-spin" />
                  <line x1="-32" y1="0" x2="-20" y2="0" stroke="#ef4444" strokeWidth="1.5" />
                  <line x1="20" y1="0" x2="32" y2="0" stroke="#ef4444" strokeWidth="1.5" />
                </g>
              )}
              {activeSystemKey === "lungs" && (
                <g transform="translate(190, 145)">
                  <circle r="48" fill="none" stroke="#06b6d4" strokeWidth="1.2" strokeDasharray="6 4" className="scanner-spin" />
                </g>
              )}
              {activeSystemKey === "muscles" && (
                <g transform="translate(190, 230)">
                  <rect x="-46" y="-36" width="92" height="72" rx="8" fill="none" stroke="#f59e0b" strokeWidth="1.2" strokeDasharray="4 4" />
                </g>
              )}
              {activeSystemKey === "digestive" && (
                <g transform="translate(190, 202)">
                  <circle r="34" fill="none" stroke="#10b981" strokeWidth="1.2" strokeDasharray="4 4" className="scanner-spin" />
                </g>
              )}
              {activeSystemKey === "sleep" && (
                <g transform={viewAngle === "front" ? "translate(190, 46)" : "translate(190, 150)"}>
                  <circle r={viewAngle === "front" ? "28" : "45"} fill="none" stroke="#8b5cf6" strokeWidth="1.2" strokeDasharray="5 3" className="scanner-spin" />
                </g>
              )}

              {/* =================================================================
                  ANTERIOR (FRONT) PROJECTION ANATOMY
                 ================================================================= */}
              {viewAngle === "front" && (
                <g id="anteriorAnatomyGroup">
                  {/* Full Anterior Human Silhouette */}
                  <g id="humanBaseFront">
                    {/* Cranium Outline */}
                    <path
                      d="M 190 24 C 172 24, 164 36, 164 52 C 164 68, 174 78, 182 82 L 182 92 L 198 92 L 198 82 C 206 78, 216 68, 216 52 C 216 36, 208 24, 190 24 Z"
                      fill="url(#bodyGradFront)"
                      stroke="#334155"
                      strokeWidth="1.5"
                    />
                    {/* Torso, Arms & Lower Extremities */}
                    <path
                      d="M 182 92
                         L 142 104 C 132 108, 126 116, 122 130
                         L 106 205 C 104 216, 96 242, 92 260
                         C 88 274, 94 282, 102 276
                         L 114 245 L 122 195
                         L 132 205
                         C 134 220, 138 238, 142 250
                         L 140 340 L 138 410 L 134 475 C 132 485, 146 490, 152 485 L 158 435 L 164 340
                         L 182 265 L 190 260 L 198 265
                         L 216 340 L 222 435 L 228 485 C 234 490, 248 485, 246 475 L 242 410 L 240 340
                         L 238 250
                         C 242 238, 246 220, 248 205
                         L 258 195 L 266 245 L 278 276
                         C 286 282, 292 274, 288 260
                         L 274 205 C 270 190, 264 116, 258 108
                         L 238 104 L 198 92 Z"
                      fill="url(#bodyGradFront)"
                      stroke="#334155"
                      strokeWidth="1.5"
                    />

                    {/* Ribcage Skeletal Cues */}
                    <path d="M 152 104 Q 190 114 228 104" stroke="rgba(148, 163, 184, 0.3)" strokeWidth="1.2" fill="none" />
                    <line x1="190" y1="108" x2="190" y2="185" stroke="rgba(148, 163, 184, 0.25)" strokeWidth="1.2" strokeDasharray="3 3" />
                    <path d="M 155 125 Q 175 132 188 132" stroke="rgba(148, 163, 184, 0.2)" strokeWidth="1" fill="none" />
                    <path d="M 225 125 Q 205 132 192 132" stroke="rgba(148, 163, 184, 0.2)" strokeWidth="1" fill="none" />
                    <path d="M 158 142 Q 175 148 188 148" stroke="rgba(148, 163, 184, 0.2)" strokeWidth="1" fill="none" />
                    <path d="M 222 142 Q 205 148 192 148" stroke="rgba(148, 163, 184, 0.2)" strokeWidth="1" fill="none" />
                    <path d="M 162 160 Q 175 166 188 166" stroke="rgba(148, 163, 184, 0.2)" strokeWidth="1" fill="none" />
                    <path d="M 218 160 Q 205 166 192 166" stroke="rgba(148, 163, 184, 0.2)" strokeWidth="1" fill="none" />
                  </g>

                  {/* SYS 1: BRAIN (Anterior: Frontal Lobes & Gyri) */}
                  <g
                    id="sys-brain-front"
                    onClick={() => setActiveSystemKey("brain")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "brain" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    <path
                      d="M 190 30
                         C 176 30, 168 38, 168 50
                         C 168 62, 175 72, 182 74
                         C 186 75, 190 75, 190 75
                         C 190 75, 194 75, 198 74
                         C 205 72, 212 62, 212 50
                         C 212 38, 204 30, 190 30 Z"
                      fill={activeSystemKey === "brain" ? "rgba(56, 189, 248, 0.45)" : "rgba(56, 189, 248, 0.2)"}
                      stroke="#38bdf8"
                      strokeWidth={activeSystemKey === "brain" ? 2.2 : 1.2}
                    />
                    <path d="M 190 30 L 190 74" stroke="#38bdf8" strokeWidth="1" strokeDasharray="2 2" />
                    <path d="M 174 44 Q 182 48 178 58" stroke="#38bdf8" strokeWidth="1.2" fill="none" opacity="0.8" />
                    <path d="M 206 44 Q 198 48 202 58" stroke="#38bdf8" strokeWidth="1.2" fill="none" opacity="0.8" />
                    <path d="M 180 38 Q 190 42 186 52" stroke="#38bdf8" strokeWidth="1" fill="none" opacity="0.6" />
                    <path d="M 200 38 Q 190 42 194 52" stroke="#38bdf8" strokeWidth="1" fill="none" opacity="0.6" />
                    <circle cx="190" cy="50" r="4" fill="#38bdf8" />
                    <circle cx="190" cy="50" r="8" fill="none" stroke="#38bdf8" strokeWidth="1" opacity="0.6" />
                  </g>

                  {/* SYS 2: RESPIRATORY (Anterior: Lungs & Bronchial Tree) */}
                  <g
                    id="sys-lungs-front"
                    onClick={() => setActiveSystemKey("lungs")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "lungs" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    {/* Right Lung (Viewer's left) */}
                    <path
                      d="M 178 116 C 168 116, 150 124, 146 142 C 142 156, 146 172, 154 182 C 162 188, 172 185, 176 176 C 178 165, 178 135, 178 116 Z"
                      fill={activeSystemKey === "lungs" ? "rgba(6, 182, 212, 0.45)" : "rgba(6, 182, 212, 0.2)"}
                      stroke="#06b6d4"
                      strokeWidth={activeSystemKey === "lungs" ? 2.2 : 1.2}
                    />
                    {/* Left Lung (Viewer's right, cardiac notch) */}
                    <path
                      d="M 202 116 C 212 116, 230 124, 234 142 C 238 156, 234 172, 226 182 C 218 188, 208 185, 204 176 C 202 165, 202 135, 202 116 Z"
                      fill={activeSystemKey === "lungs" ? "rgba(6, 182, 212, 0.45)" : "rgba(6, 182, 212, 0.2)"}
                      stroke="#06b6d4"
                      strokeWidth={activeSystemKey === "lungs" ? 2.2 : 1.2}
                    />
                    {/* Trachea & Bronchi */}
                    <path d="M 190 92 L 190 120 L 175 136 M 190 120 L 205 136" stroke="#06b6d4" strokeWidth="1.5" fill="none" />
                    <path d="M 170 142 L 158 155 M 172 150 L 164 165" stroke="#06b6d4" strokeWidth="1" fill="none" opacity="0.7" />
                    <path d="M 210 142 L 222 155 M 208 150 L 216 165" stroke="#06b6d4" strokeWidth="1" fill="none" opacity="0.7" />
                  </g>

                  {/* SYS 3: CARDIOVASCULAR (Anterior: Heart & Aortic Arch) */}
                  <g
                    id="sys-heart-front"
                    onClick={() => setActiveSystemKey("heart")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "heart" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    <path d="M 188 128 C 188 116, 178 116, 176 122 C 174 126, 174 135, 174 138" stroke="#ef4444" strokeWidth="2.5" fill="none" />
                    <path
                      d="M 176 130 C 166 126, 160 136, 162 146 C 164 158, 176 168, 182 172 C 186 168, 196 156, 194 144 C 192 134, 182 128, 176 130 Z"
                      fill={activeSystemKey === "heart" ? "rgba(239, 68, 68, 0.7)" : "rgba(239, 68, 68, 0.35)"}
                      stroke="#ef4444"
                      strokeWidth={activeSystemKey === "heart" ? 2.5 : 1.5}
                    />
                    <path d="M 182 116 L 182 102 M 178 118 L 168 112 M 186 118 L 198 112" stroke="#ef4444" strokeWidth="1.2" />
                    <circle cx="178" cy="146" r="4.5" fill="#fca5a5" />
                    <circle cx="178" cy="146" r="8" fill="none" stroke="#ef4444" strokeWidth="1" opacity="0.8" />
                  </g>

                  {/* SYS 4: MUSCULOSKELETAL (Anterior: Pectorals, Abs & Quads) */}
                  <g
                    id="sys-muscles-front"
                    onClick={() => setActiveSystemKey("muscles")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "muscles" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    <path d="M 148 116 L 174 120 L 174 134 L 144 126 Z" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.45)" : "rgba(245, 158, 11, 0.18)"} stroke="#f59e0b" strokeWidth="1.2" />
                    <path d="M 232 116 L 206 120 L 206 134 L 236 126 Z" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.45)" : "rgba(245, 158, 11, 0.18)"} stroke="#f59e0b" strokeWidth="1.2" />
                    {/* Rectus abdominis pack */}
                    <rect x="178" y="174" width="10" height="9" rx="2" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"} stroke="#f59e0b" strokeWidth="1" />
                    <rect x="192" y="174" width="10" height="9" rx="2" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"} stroke="#f59e0b" strokeWidth="1" />
                    <rect x="178" y="186" width="10" height="9" rx="2" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"} stroke="#f59e0b" strokeWidth="1" />
                    <rect x="192" y="186" width="10" height="9" rx="2" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"} stroke="#f59e0b" strokeWidth="1" />
                    <rect x="178" y="198" width="10" height="10" rx="2" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"} stroke="#f59e0b" strokeWidth="1" />
                    <rect x="192" y="198" width="10" height="10" rx="2" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"} stroke="#f59e0b" strokeWidth="1" />
                    {/* Quadriceps */}
                    <path d="M 148 268 C 142 290, 142 320, 146 345 C 154 345, 162 330, 164 300 C 166 280, 160 268, 148 268 Z" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.45)" : "rgba(245, 158, 11, 0.18)"} stroke="#f59e0b" strokeWidth="1.2" />
                    <path d="M 232 268 C 238 290, 238 320, 234 345 C 226 345, 218 330, 216 300 C 214 280, 220 268, 232 268 Z" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.45)" : "rgba(245, 158, 11, 0.18)"} stroke="#f59e0b" strokeWidth="1.2" />
                  </g>

                  {/* SYS 5: DIGESTIVE (Anterior: Stomach, Intestines & Hepatic Curve) */}
                  <g
                    id="sys-digestive-front"
                    onClick={() => setActiveSystemKey("digestive")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "digestive" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    <path
                      d="M 180 182 C 168 182, 164 192, 168 200 C 174 208, 185 208, 194 202 C 202 196, 206 186, 198 182 Z"
                      fill={activeSystemKey === "digestive" ? "rgba(16, 185, 129, 0.55)" : "rgba(16, 185, 129, 0.22)"}
                      stroke="#10b981"
                      strokeWidth={activeSystemKey === "digestive" ? 2.2 : 1.2}
                    />
                    <path
                      d="M 174 212 Q 190 208 206 212 Q 208 222 190 224 Q 172 226 178 234 Q 192 238 204 232"
                      stroke="#10b981"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      fill="none"
                    />
                    <circle cx="190" cy="216" r="3.5" fill="#6ee7b7" />
                  </g>

                  {/* SYS 6: SLEEP (Anterior: Pineal Circadian Beacon) */}
                  <g
                    id="sys-sleep-front"
                    onClick={() => setActiveSystemKey("sleep")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "sleep" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    <circle cx="190" cy="46" r="5" fill="#8b5cf6" />
                    <path d="M 178 40 Q 190 34 202 40" stroke="#8b5cf6" strokeWidth="1.5" fill="none" opacity="0.8" />
                    <path d="M 172 34 Q 190 26 208 34" stroke="#8b5cf6" strokeWidth="1.2" fill="none" opacity="0.6" strokeDasharray="3 3" />
                  </g>
                </g>
              )}

              {/* =================================================================
                  DORSAL (BACK) PROJECTION ANATOMY
                 ================================================================= */}
              {viewAngle === "back" && (
                <g id="dorsalAnatomyGroup">
                  {/* Full Dorsal Silhouette */}
                  <g id="humanBaseBack">
                    {/* Occipital Skull & Nape */}
                    <path
                      d="M 190 24 C 172 24, 164 36, 164 54 C 164 70, 172 78, 180 84 L 180 94 L 200 94 L 200 84 C 208 78, 216 70, 216 54 C 216 36, 208 24, 190 24 Z"
                      fill="url(#bodyGradBack)"
                      stroke="#334155"
                      strokeWidth="1.5"
                    />
                    {/* Broad Shoulders, Latissimus & Dorsal Limbs */}
                    <path
                      d="M 180 94
                         L 140 106 C 130 110, 124 118, 120 132
                         L 104 208 C 102 218, 94 244, 90 262
                         C 86 276, 92 284, 100 278
                         L 112 247 L 120 197
                         L 130 207
                         C 132 222, 136 240, 140 252
                         L 138 342 L 136 412 L 132 475 C 130 485, 144 490, 150 485 L 156 435 L 162 342
                         L 182 270 L 190 266 L 198 270
                         L 218 342 L 224 435 L 230 485 C 236 490, 250 485, 248 475 L 244 412 L 242 342
                         L 240 252
                         C 244 240, 248 222, 250 207
                         L 260 197 L 268 247 L 280 278
                         C 288 284, 294 276, 290 262
                         L 276 208 C 272 192, 266 118, 260 110
                         L 240 106 L 200 94 Z"
                      fill="url(#bodyGradBack)"
                      stroke="#334155"
                      strokeWidth="1.5"
                    />

                    {/* Gluteal Crease & Contours */}
                    <path d="M 190 248 L 190 270" stroke="rgba(148, 163, 184, 0.4)" strokeWidth="1.2" />
                    <path d="M 166 260 C 176 270, 188 270, 190 268" stroke="rgba(148, 163, 184, 0.3)" strokeWidth="1" fill="none" />
                    <path d="M 214 260 C 204 270, 192 270, 190 268" stroke="rgba(148, 163, 184, 0.3)" strokeWidth="1" fill="none" />
                  </g>

                  {/* Complete Vertebral Column (Spine & Spinal Cord C1-L5 + Sacrum) */}
                  <g id="dorsalSpine">
                    <line x1="190" y1="84" x2="190" y2="255" stroke="url(#spineGrad)" strokeWidth="3" />
                    {/* Intervertebral Spines & Ganglia */}
                    {[92, 102, 112, 122, 132, 142, 152, 162, 172, 182, 192, 202, 214, 226, 238, 248].map((y) => (
                      <g key={y}>
                        <line x1="184" y1={y} x2="196" y2={y} stroke="#38bdf8" strokeWidth="1.4" strokeLinecap="round" />
                        <line x1="178" y1={y + 1} x2="184" y2={y} stroke="rgba(56, 189, 248, 0.5)" strokeWidth="0.8" />
                        <line x1="196" y1={y} x2="202" y2={y + 1} stroke="rgba(56, 189, 248, 0.5)" strokeWidth="0.8" />
                      </g>
                    ))}
                    {/* Sacrum & Coccyx */}
                    <path d="M 186 254 L 194 254 L 190 266 Z" fill="#38bdf8" opacity="0.7" />
                  </g>

                  {/* SYS 1: BRAIN (Dorsal: Occipital Lobe & Cerebellum) */}
                  <g
                    id="sys-brain-back"
                    onClick={() => setActiveSystemKey("brain")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "brain" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    {/* Cerebellar Folia Lobes */}
                    <path
                      d="M 174 56 C 174 48, 184 46, 190 46 C 196 46, 206 48, 206 56 C 206 66, 198 72, 190 72 C 182 72, 174 66, 174 56 Z"
                      fill={activeSystemKey === "brain" ? "rgba(56, 189, 248, 0.5)" : "rgba(56, 189, 248, 0.22)"}
                      stroke="#38bdf8"
                      strokeWidth={activeSystemKey === "brain" ? 2.2 : 1.2}
                    />
                    <path d="M 178 52 Q 190 56 202 52" stroke="#38bdf8" strokeWidth="1" fill="none" />
                    <path d="M 178 60 Q 190 64 202 60" stroke="#38bdf8" strokeWidth="1" fill="none" />
                    <path d="M 190 46 L 190 84" stroke="#38bdf8" strokeWidth="1.2" strokeDasharray="2 2" />
                    <circle cx="190" cy="56" r="4" fill="#38bdf8" />
                  </g>

                  {/* SYS 2: RESPIRATORY (Dorsal: Posterior Lung Bases) */}
                  <g
                    id="sys-lungs-back"
                    onClick={() => setActiveSystemKey("lungs")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "lungs" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    {/* Posterior Right Lung */}
                    <path
                      d="M 176 118 C 166 118, 146 126, 144 146 C 142 162, 144 178, 154 190 C 164 198, 174 194, 176 182 Z"
                      fill={activeSystemKey === "lungs" ? "rgba(6, 182, 212, 0.45)" : "rgba(6, 182, 212, 0.18)"}
                      stroke="#06b6d4"
                      strokeWidth={activeSystemKey === "lungs" ? 2.2 : 1.2}
                    />
                    {/* Posterior Left Lung */}
                    <path
                      d="M 204 118 C 214 118, 234 126, 236 146 C 238 162, 236 178, 226 190 C 216 198, 206 194, 204 182 Z"
                      fill={activeSystemKey === "lungs" ? "rgba(6, 182, 212, 0.45)" : "rgba(6, 182, 212, 0.18)"}
                      stroke="#06b6d4"
                      strokeWidth={activeSystemKey === "lungs" ? 2.2 : 1.2}
                    />
                  </g>

                  {/* SYS 3: CARDIOVASCULAR (Dorsal: Descending Thoracic Aorta) */}
                  <g
                    id="sys-heart-back"
                    onClick={() => setActiveSystemKey("heart")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "heart" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    <path d="M 186 118 L 186 176" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
                    <line x1="186" y1="130" x2="174" y2="130" stroke="#ef4444" strokeWidth="1" />
                    <line x1="186" y1="145" x2="174" y2="145" stroke="#ef4444" strokeWidth="1" />
                    <line x1="186" y1="160" x2="174" y2="160" stroke="#ef4444" strokeWidth="1" />
                    <circle cx="186" cy="146" r="4" fill="#ef4444" />
                  </g>

                  {/* SYS 4: MUSCULOSKELETAL (Dorsal: Scapulae, Trapezius, Latissimus & Hamstrings) */}
                  <g
                    id="sys-muscles-back"
                    onClick={() => setActiveSystemKey("muscles")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "muscles" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    {/* Left Scapula (Viewer's left) */}
                    <path
                      d="M 148 116 L 168 122 L 158 152 Z"
                      fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"}
                      stroke="#f59e0b"
                      strokeWidth="1.2"
                    />
                    {/* Right Scapula (Viewer's right) */}
                    <path
                      d="M 232 116 L 212 122 L 222 152 Z"
                      fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)"}
                      stroke="#f59e0b"
                      strokeWidth="1.2"
                    />
                    {/* Latissimus Dorsi Fan */}
                    <path
                      d="M 142 168 Q 170 185 186 210 L 190 210 Q 206 185 238 168 L 244 195 Q 215 220 190 238 Q 165 220 136 195 Z"
                      fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.4)" : "rgba(245, 158, 11, 0.15)"}
                      stroke="#f59e0b"
                      strokeWidth="1.2"
                    />
                    {/* Gluteus Maximus Plates */}
                    <path
                      d="M 152 248 C 144 265, 144 285, 154 298 C 168 304, 184 295, 188 274 Z"
                      fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.45)" : "rgba(245, 158, 11, 0.18)"}
                      stroke="#f59e0b"
                      strokeWidth="1.2"
                    />
                    <path
                      d="M 228 248 C 236 265, 236 285, 226 298 C 212 304, 196 295, 192 274 Z"
                      fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.45)" : "rgba(245, 158, 11, 0.18)"}
                      stroke="#f59e0b"
                      strokeWidth="1.2"
                    />
                    {/* Hamstring muscle chains */}
                    <path d="M 150 310 C 144 335, 144 365, 150 385 L 162 385 C 166 365, 166 335, 162 310 Z" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.4)" : "rgba(245, 158, 11, 0.15)"} stroke="#f59e0b" strokeWidth="1" />
                    <path d="M 230 310 C 236 335, 236 365, 230 385 L 218 385 C 214 365, 214 335, 218 310 Z" fill={activeSystemKey === "muscles" ? "rgba(245, 158, 11, 0.4)" : "rgba(245, 158, 11, 0.15)"} stroke="#f59e0b" strokeWidth="1" />
                  </g>

                  {/* SYS 5: DIGESTIVE (Dorsal: Retroperitoneal Kidneys & Adrenals) */}
                  <g
                    id="sys-digestive-back"
                    onClick={() => setActiveSystemKey("digestive")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "digestive" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    {/* Right Kidney (Viewer's left) */}
                    <path
                      d="M 166 182 C 160 182, 156 190, 158 200 C 160 210, 168 214, 172 208 C 174 200, 172 186, 166 182 Z"
                      fill={activeSystemKey === "digestive" ? "rgba(16, 185, 129, 0.6)" : "rgba(16, 185, 129, 0.25)"}
                      stroke="#10b981"
                      strokeWidth={activeSystemKey === "digestive" ? 2 : 1.2}
                    />
                    {/* Left Kidney (Viewer's right) */}
                    <path
                      d="M 214 178 C 220 178, 224 186, 222 196 C 220 206, 212 210, 208 204 C 206 196, 208 182, 214 178 Z"
                      fill={activeSystemKey === "digestive" ? "rgba(16, 185, 129, 0.6)" : "rgba(16, 185, 129, 0.25)"}
                      stroke="#10b981"
                      strokeWidth={activeSystemKey === "digestive" ? 2 : 1.2}
                    />
                    <circle cx="166" cy="195" r="2.5" fill="#6ee7b7" />
                    <circle cx="214" cy="191" r="2.5" fill="#6ee7b7" />
                  </g>

                  {/* SYS 6: SLEEP & CIRCADIAN (Dorsal: Restorative Sympathetic/Parasympathetic Spine Chain) */}
                  <g
                    id="sys-sleep-back"
                    onClick={() => setActiveSystemKey("sleep")}
                    style={{ cursor: "pointer" }}
                    filter={activeSystemKey === "sleep" ? "url(#glowActive)" : undefined}
                    className="organ-hotspot"
                  >
                    <line x1="190" y1="84" x2="190" y2="250" stroke="#8b5cf6" strokeWidth="2.5" strokeDasharray="6 3" />
                    {[95, 125, 155, 185, 215, 245].map((y) => (
                      <circle key={y} cx="190" cy={y} r="4.5" fill="#a78bfa" stroke="#6d28d9" strokeWidth="1" />
                    ))}
                  </g>
                </g>
              )}

              {/* Active System Target Coordinate Callout */}
              <g id="sysActiveCalloutLine">
                {activeSystemKey === "brain" && (
                  <>
                    <line x1="214" y1="50" x2="280" y2="50" stroke="#38bdf8" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="280" cy="50" r="2.5" fill="#38bdf8" />
                    <text x="286" y="53" fill="#38bdf8" fontSize="9" fontWeight="700" fontFamily="monospace">SYS.01 // BRAIN & CNS</text>
                  </>
                )}
                {activeSystemKey === "heart" && (
                  <>
                    <line x1="162" y1="146" x2="65" y2="146" stroke="#ef4444" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="65" cy="146" r="2.5" fill="#ef4444" />
                    <text x="71" y="142" fill="#ef4444" fontSize="9" fontWeight="700" fontFamily="monospace">SYS.02 // CARDIO</text>
                  </>
                )}
                {activeSystemKey === "lungs" && (
                  <>
                    <line x1="236" y1="148" x2="290" y2="148" stroke="#06b6d4" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="290" cy="148" r="2.5" fill="#06b6d4" />
                    <text x="296" y="151" fill="#06b6d4" fontSize="9" fontWeight="700" fontFamily="monospace">SYS.03 // RESPIRATORY</text>
                  </>
                )}
                {activeSystemKey === "muscles" && (
                  <>
                    <line x1="142" y1="270" x2="65" y2="270" stroke="#f59e0b" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="65" cy="270" r="2.5" fill="#f59e0b" />
                    <text x="71" y="266" fill="#f59e0b" fontSize="9" fontWeight="700" fontFamily="monospace">SYS.04 // MUSCULOSKELETAL</text>
                  </>
                )}
                {activeSystemKey === "digestive" && (
                  <>
                    <line x1="214" y1="200" x2="280" y2="200" stroke="#10b981" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="280" cy="200" r="2.5" fill="#10b981" />
                    <text x="286" y="203" fill="#10b981" fontSize="9" fontWeight="700" fontFamily="monospace">SYS.05 // DIGESTIVE CORE</text>
                  </>
                )}
                {activeSystemKey === "sleep" && (
                  <>
                    <line x1="170" y1="46" x2="65" y2="46" stroke="#8b5cf6" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="65" cy="46" r="2.5" fill="#8b5cf6" />
                    <text x="71" y="43" fill="#8b5cf6" fontSize="9" fontWeight="700" fontFamily="monospace">SYS.06 // REST & CIRCADIAN</text>
                  </>
                )}
              </g>
            </svg>
          </div>

          {/* HUD Footer Status Bar */}
          <div className="anatomy-hud-footer">
            <span>TARGET: {currentSys.name.toUpperCase()}</span>
            <span>COORDS: {viewAngle === "front" ? currentSys.coords.front : currentSys.coords.back}</span>
            <span style={{ color: currentSys.isLive ? "#10b981" : "#94a3b8", fontWeight: "700" }}>
              {currentSys.isLive ? "● LIVE SENSOR LINKED" : "○ SENSOR OFFLINE / STANDBY"}
            </span>
          </div>
        </div>

        {/* =========================================================================
            RIGHT PANEL: HEALTH INTELLIGENCE CONSOLE
           ========================================================================= */}
        <div className="health-sys-card">
          {/* Header Info */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", borderBottom: "1px solid #f1f5f9", paddingBottom: "16px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                <span
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "10px",
                    background: `${currentSys.color}15`,
                    color: currentSys.color,
                    display: "grid",
                    placeItems: "center"
                  }}
                >
                  <currentSys.icon size={20} />
                </span>
                <h2 style={{ margin: 0, fontSize: "22px", fontWeight: "800", color: "#0f172a" }}>{currentSys.name}</h2>
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", fontStyle: "italic", letterSpacing: "0.3px" }}>
                {currentSys.latin} • {currentSys.region}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className={`status ${currentSys.statusColor}`}>
                {currentSys.isLive ? "TELEMETRY LINKED" : "STANDBY / OFFLINE"}
              </span>
              <span className="sim-badge">
                {dashboardData?.physiological?.is_simulated ? "ANALOG STREAM" : "HARDWARE"}
              </span>
            </div>
          </div>

          {/* Connected Sensor Hardware Description Card */}
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "12px 16px", margin: "16px 0", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
            <div>
              <div style={{ fontSize: "10px", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Connected Sensor Hardware
              </div>
              <div style={{ fontSize: "14px", fontWeight: "700", color: "#0f172a", marginTop: "2px" }}>
                {currentSys.sensor}
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                Protocol: {currentSys.dataProtocol}
              </div>
            </div>
            <div style={{ fontSize: "11px", color: "#2563eb", fontWeight: "700", background: "#eff6ff", padding: "4px 10px", borderRadius: "6px", border: "1px solid #bfdbfe" }}>
              {currentSys.sensorType}
            </div>
          </div>

          {/* Live System Metrics Tiles Grid */}
          <div className="health-metric-grid">
            {metrics.map((m, idx) => (
              <div key={idx} className="health-metric-tile">
                <div className="health-metric-label">{m.label}</div>
                <div className="health-metric-val">{m.val}</div>
                <div className="health-metric-sub">
                  <span
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      background: m.status === "green" ? "#10b981" : m.status === "red" ? "#ef4444" : m.status === "yellow" ? "#f59e0b" : "#3b82f6"
                    }}
                  />
                  <span>{m.sub}</span>
                </div>
              </div>
            ))}
          </div>

          {/* 24-Hour Telemetry Historical Profile Panel */}
          <div className="health-trend-box">
            <div className="health-trend-header">
              <span>24-HOUR TELEMETRY PROFILE // {currentSys.name.toUpperCase()}</span>
              <div className="health-trend-readout">
                {currentTelemetryVal && (
                  <span className="health-trend-val-badge">
                    Current: {currentTelemetryVal}
                  </span>
                )}
                <span>
                  {trendPoints.length > 0 ? `${trendPoints.length} SAMPLE LOGS` : "NO LOGGED SAMPLES"}
                </span>
              </div>
            </div>

            {trendPoints.length > 1 ? (
              <div>
                <div style={{ height: "75px", width: "100%", position: "relative" }}>
                  <svg viewBox="0 0 300 75" style={{ width: "100%", height: "100%", overflow: "visible" }}>
                    {(() => {
                      const min = Math.min(...trendPoints);
                      const max = Math.max(...trendPoints) || 1;
                      const range = max === min ? 1 : max - min;
                      const coords = trendPoints.map((val, i) => {
                        const x = (i / (trendPoints.length - 1)) * 300;
                        const y = 65 - ((val - min) / range) * 55;
                        return `${x},${y}`;
                      });
                      const d = `M ${coords.join(" L ")}`;
                      const areaD = `${d} L 300 75 L 0 75 Z`;
                      return (
                        <>
                          <defs>
                            <linearGradient id={`trendGrad-${currentSys.key}`} x1="0%" y1="0%" x2="0%" y2="100%">
                              <stop offset="0%" stopColor={currentSys.color} stopOpacity="0.4" />
                              <stop offset="100%" stopColor={currentSys.color} stopOpacity="0.0" />
                            </linearGradient>
                          </defs>
                          {/* Area under curve */}
                          <path d={areaD} fill={`url(#trendGrad-${currentSys.key})`} />
                          {/* Line curve */}
                          <path d={d} fill="none" stroke={currentSys.color} strokeWidth="2.4" strokeLinecap="round" />
                          {/* Data points */}
                          {trendPoints.map((val, i) => {
                            const x = (i / (trendPoints.length - 1)) * 300;
                            const y = 65 - ((val - min) / range) * 55;
                            return (
                              <circle
                                key={i}
                                cx={x}
                                cy={y}
                                r="3.5"
                                fill="#090f1f"
                                stroke={currentSys.color}
                                strokeWidth="2"
                              />
                            );
                          })}
                        </>
                      );
                    })()}
                  </svg>
                </div>
                {/* Time Axis Row */}
                <div className="health-trend-time-axis">
                  <span>-24h</span>
                  <span>-18h</span>
                  <span>-12h</span>
                  <span>-6h</span>
                  <span style={{ color: currentSys.color, fontWeight: "700" }}>Now (T-0)</span>
                </div>
              </div>
            ) : (
              <div style={{ color: "#64748b", fontSize: "12px", textAlign: "center", padding: "24px 0", fontFamily: "ui-monospace, monospace" }}>
                NO LOGGED SAMPLES • Awaiting continuous telemetry stream for Subject #{selectedAstronautId}
              </div>
            )}
          </div>

          {/* Biological Function & Monitored Biomarkers */}
          <div style={{ marginTop: "16px" }}>
            <h3 style={{ fontSize: "13px", fontWeight: "700", margin: "0 0 6px", color: "#1e293b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Functional Architecture
            </h3>
            <p style={{ fontSize: "13px", color: "#475569", lineHeight: "1.6", margin: "0 0 16px" }}>
              {systemStatus?.main_function || "Biological system supporting long-duration human spaceflight operational readiness and autonomic homeostasis."}
            </p>

            <h3 style={{ fontSize: "13px", fontWeight: "700", margin: "0 0 10px", color: "#1e293b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Monitored Biomarkers & Indicators
            </h3>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
              {currentSys.biomarkers?.map((b) => (
                <div key={b.name} className={`biomarker-chip ${b.active ? "active" : "unavailable"}`}>
                  <span>{b.name}</span>
                  <span className={`biomarker-tag ${b.active ? "active" : "unavailable"}`}>
                    {b.tag}
                  </span>
                </div>
              ))}
            </div>

            <div className="notice" style={{ margin: "14px 0" }}>
              <b>Flight Surgeon Clinical Protocol:</b>
              <br />
              {systemStatus?.explanation || "Real-time streaming telemetry derived from verified sensor adapters. Non-invasive proxy indicators are decision-support aids for flight surgeon evaluations."}
            </div>

            {systemStatus?.suggested_actions && systemStatus.suggested_actions.length > 0 && (
              <>
                <h3 style={{ fontSize: "13px", fontWeight: "700", margin: "16px 0 6px", color: "#1e293b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Operational Flight Guidance
                </h3>
                <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "13px", color: "#475569", lineHeight: "1.6" }}>
                  {systemStatus.suggested_actions.map((act, i) => (
                    <li key={i}>{act}</li>
                  ))}
                </ul>
              </>
            )}

            {/* Quick Action Navigation Buttons */}
            <div style={{ display: "flex", gap: "10px", marginTop: "22px", borderTop: "1px solid #f1f5f9", paddingTop: "16px", flexWrap: "wrap" }}>
              <button
                className="crew-action-btn primary"
                onClick={() => onNavigateToTab("dashboard")}
                style={{ padding: "9px 16px" }}
              >
                <Activity size={15} />
                <span>Open Astronaut Telemetry</span>
              </button>
              {activeSystemKey === "brain" && (
                <button
                  className="crew-action-btn"
                  onClick={() => onNavigateToTab("calibration")}
                  style={{ padding: "9px 16px" }}
                >
                  <Camera size={15} />
                  <span>Recalibrate Baseline</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


export default function App() {
  const [tab, setTab] = useState("crew");
  const [astronauts, setAstronauts] = useState([]);
  const [selectedAstronautId, setSelectedAstronautId] = useState(1);
  const [missions, setMissions] = useState([]);
  const [selectedMissionId, setSelectedMissionId] = useState(1);

  // Health data states
  const [dashboardData, setDashboardData] = useState(null);
  const [missionData, setMissionData] = useState(null);
  const [psiBaseline, setPsiBaseline] = useState(null);
  const [psiHistory, setPsiHistory] = useState([]);
  const [chronicAnalytics, setChronicAnalytics] = useState(null);
  const [burnoutAnalytics, setBurnoutAnalytics] = useState(null);

  // Legacy feature states
  const [systems, setSystems] = useState([]);
  const [activeBodyRegion, setActiveBodyRegion] = useState("brain");
  const [bodyStatusData, setBodyStatusData] = useState(null);
  const [environments, setEnvironments] = useState([]);
  const [routines, setRoutines] = useState([]);
  const [challenges, setChallenges] = useState([]);
  const [education, setEducation] = useState([]);

  // Telemetry stream log
  const [liveEvents, setLiveEvents] = useState([]);

  // UI status states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [calibModalOpen, setCalibModalOpen] = useState(false);
  const [customKeyInput, setCustomKeyInput] = useState("");
  const [currentPersona, setCurrentPersona] = useState(DEMO_PERSONAS[0]);

  // Live Simulator state
  const [simStress, setSimStress] = useState(35);
  const [simEmotion, setSimEmotion] = useState("neutral");
  const [simTaskComplexity, setSimTaskComplexity] = useState(5.0);
  const [simSending, setSimSending] = useState(false);

  // Initialize auth
  useEffect(() => {
    const existingKey = getApiKey();
    if (!existingKey) {
      setApiKey(DEMO_PERSONAS[0].key);
      setCurrentPersona(DEMO_PERSONAS[0]);
    } else {
      const match = DEMO_PERSONAS.find((p) => p.key === existingKey);
      if (match) setCurrentPersona(match);
      else {
        setCurrentPersona({
          id: "custom",
          label: "Custom API Key",
          role: "custom",
          key: existingKey,
          desc: "User-defined authentication token."
        });
      }
    }
  }, []);

  // Handle incoming WebSocket messages
  const handleWsMessage = useCallback((msg) => {
    const timestamp = new Date().toLocaleTimeString();
    setLiveEvents((prev) => [
      { id: Date.now(), time: timestamp, type: msg.type, data: msg.data || msg },
      ...prev.slice(0, 24)
    ]);

    // Live update astronaut dashboard if event matches selected astronaut
    if (msg.type === "psi_reading" || msg.type === "psi_frame_reading") {
      setDashboardData((prev) => {
        if (!prev) return prev;
        const reading = msg.data;
        return {
          ...prev,
          psi_status: {
            ...prev.psi_status,
            status: reading.smoothed_stress > 70 ? "red" : reading.smoothed_stress > 35 ? "yellow" : "green",
            status_label: reading.smoothed_stress > 70 ? "high_stress" : reading.smoothed_stress > 35 ? "elevated" : "nominal",
            latest_reading: reading
          }
        };
      });
    } else if (msg.type === "physiological_telemetry") {
      setDashboardData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          physiological: {
            ...prev.physiological,
            available: true,
            ...msg.data
          }
        };
      });
    }
  }, []);

  // Real-time WebSocket connection
  const { status: wsStatus, reconnect: wsReconnect } = useWebSocket({
    astronautId: selectedAstronautId,
    missionId: selectedMissionId,
    onMessage: handleWsMessage
  });

  // Load Astronauts and Missions
  const loadRosterAndMissions = useCallback(async () => {
    try {
      const [astros, mList] = await Promise.all([api.listAstronauts(), api.listMissions()]);
      setAstronauts(astros || []);
      setMissions(mList || []);
      if (astros && astros.length > 0 && !astros.some((a) => a.id === selectedAstronautId)) {
        setSelectedAstronautId(astros[0].id);
      }
      if (mList && mList.length > 0 && !mList.some((m) => m.id === selectedMissionId)) {
        setSelectedMissionId(mList[0].id);
      }
    } catch (e) {
      if (e.status === 401) {
        setError("Authentication required or expired key. Click 'Auth Persona' to select a demo login.");
      } else {
        setError(e.message);
      }
    }
  }, [selectedAstronautId, selectedMissionId]);

  // Load Astronaut Dashboard
  const loadAstronautTelemetry = useCallback(async (astroId) => {
    if (!astroId) return;
    setLoading(true);
    setError("");
    try {
      const [dash, base, hist, chro, burn] = await Promise.all([
        api.getAstronautDashboard(astroId),
        api.getBaseline(astroId).catch(() => null),
        api.getPsiHistory(astroId, 24, 20).catch(() => []),
        api.getChronicAnalytics(astroId).catch(() => null),
        api.getBurnoutAnalytics(astroId).catch(() => null)
      ]);
      setDashboardData(dash);
      setPsiBaseline(base);
      setPsiHistory(hist || []);
      setChronicAnalytics(chro);
      setBurnoutAnalytics(burn);
    } catch (e) {
      if (e.status === 403) {
        setError(`Access Denied: Current role (${currentPersona.role}) cannot access Astronaut ${astroId}'s private health data.`);
      } else if (e.status === 401) {
        setError("Unauthorized: Please sign in using a valid demo persona.");
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }, [currentPersona.role]);

  // Load Mission Dashboard
  const loadMissionData = useCallback(async (mId) => {
    if (!mId) return;
    setLoading(true);
    try {
      const mDash = await api.getMissionDashboard(mId);
      setMissionData(mDash);
    } catch (e) {
      if (e.status === 403) {
        setError(`Access Denied: Mission-wide health rollups require 'flight_surgeon' or 'mission_director' role.`);
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Load Legacy Core Features
  const loadLegacyFeatures = useCallback(async () => {
    try {
      const [sys, envs, rts, chs, edu] = await Promise.all([
        api.bodySystems().catch(() => []),
        api.environments().catch(() => []),
        api.routines(selectedAstronautId).catch(() => []),
        api.challenges().catch(() => []),
        api.education().catch(() => [])
      ]);
      setSystems(sys);
      setEnvironments(envs);
      setRoutines(rts);
      setChallenges(chs);
      setEducation(edu);
    } catch (_) {}
  }, [selectedAstronautId]);

  // Initial load
  useEffect(() => {
    loadRosterAndMissions();
    loadLegacyFeatures();
  }, [loadRosterAndMissions, loadLegacyFeatures]);

  // Tab and astronaut reaction
  useEffect(() => {
    if (tab === "dashboard" || tab === "psi" || tab === "calibration" || tab === "body") {
      loadAstronautTelemetry(selectedAstronautId);
    } else if (tab === "mission") {
      loadMissionData(selectedMissionId);
    }
  }, [tab, selectedAstronautId, selectedMissionId, loadAstronautTelemetry, loadMissionData]);

  // Body map status reaction
  useEffect(() => {
    if (tab === "body" && activeBodyRegion) {
      api.bodyStatus(activeBodyRegion, selectedAstronautId)
        .then(setBodyStatusData)
        .catch(() => {});
    }
  }, [tab, activeBodyRegion, selectedAstronautId]);

  // Switch demo persona
  const handleSelectPersona = (persona) => {
    setApiKey(persona.key);
    setCurrentPersona(persona);
    setAuthModalOpen(false);
    setError("");
    if (persona.astronautId) {
      setSelectedAstronautId(persona.astronautId);
    }
    loadRosterAndMissions();
    if (tab === "mission") loadMissionData(selectedMissionId);
    else loadAstronautTelemetry(persona.astronautId || selectedAstronautId);
    wsReconnect();
  };

  // Submit custom key
  const handleCustomKeySubmit = (e) => {
    e.preventDefault();
    if (!customKeyInput.trim()) return;
    const key = customKeyInput.trim();
    setApiKey(key);
    setCurrentPersona({
      id: "custom",
      label: "Custom API Key",
      role: "custom",
      key,
      desc: "Custom authorized token."
    });
    setAuthModalOpen(false);
    setError("");
    loadRosterAndMissions();
    wsReconnect();
  };

  // Quick Simulator: Send stress reading
  const handleSendSimulatedReading = async () => {
    setSimSending(true);
    try {
      const vec = {
        angry: simEmotion === "angry" ? 0.7 : 0.05,
        fear: simEmotion === "fear" ? 0.7 : 0.05,
        sad: simEmotion === "sad" ? 0.7 : 0.05,
        happy: simEmotion === "happy" ? 0.8 : 0.1,
        neutral: simEmotion === "neutral" ? 0.8 : 0.1,
        surprise: 0.05,
        disgust: 0.02
      };
      await api.submitDirectReading(selectedAstronautId, {
        raw_stress: Number(simStress),
        smoothed_stress: Number(simStress),
        dominant_emotion: simEmotion,
        emotion_vector: vec,
        motion_level: 1.5,
        task_complexity: Number(simTaskComplexity),
        mission_id: selectedMissionId
      });
      // Also submit a matching physiological telemetry sample
      await api.submitTelemetry({
        astronaut_id: selectedAstronautId,
        mission_id: selectedMissionId,
        heart_rate: Math.round(62 + simStress * 0.5),
        spo2: 98.5,
        body_temperature: 36.8,
        respiration_rate: 14.0,
        is_simulated: true,
        source_device: "Simulated-Wearable-v2"
      });
      // Refresh current telemetry
      loadAstronautTelemetry(selectedAstronautId);
    } catch (e) {
      setError(`Simulation dispatch failed: ${e.message}`);
    } finally {
      setSimSending(false);
    }
  };

  // Quick benchmark demonstration calibration
  const handleQuickBenchmark = async () => {
    try {
      setLoading(true);
      await api.runBenchmarkCalibration(selectedAstronautId);
      await loadAstronautTelemetry(selectedAstronautId);
    } catch (e) {
      setError(`Demonstration calibration failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Routine completion
  const handleCompleteRoutine = async (id) => {
    try {
      await api.completeRoutine(id);
      loadLegacyFeatures();
    } catch (e) {
      setError(e.message);
    }
  };

  // Challenge completion
  const handleCompleteChallenge = async (id) => {
    try {
      await api.completeChallenge(id, selectedAstronautId);
      loadLegacyFeatures();
    } catch (e) {
      setError(e.message);
    }
  };

  // Selected astronaut object
  const currentAstronaut = useMemo(
    () => astronauts.find((a) => a.id === selectedAstronautId) || dashboardData?.astronaut,
    [astronauts, selectedAstronautId, dashboardData]
  );

  return (
    <div className="shell">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <span className="brandmark">N</span>
          <div>
            <b>NOVIS</b>
            <small>HEALTH INTELLIGENCE</small>
          </div>
        </div>

        <div className="navlabel">MISSION OPERATIONS</div>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`navitem ${tab === id ? "selected" : ""}`}
            onClick={() => setTab(id)}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}

        <div className="sidefoot">
          <b>NOVIS</b>
          <br />
          Neural Onboard Vitality &
          <br />
          Intelligence System v3.2
          <br />
          <small style={{ color: "#94a3b8", display: "block", marginTop: "4px" }}>
            Intelligent Crew Health.
            <br />
            Adaptive Mission Readiness.
          </small>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main">
        {/* Top Operational Header */}
        <header>
          <div>
            <div className="eyebrow">NOVIS / MISSION OPERATIONS</div>
            <h1>{TABS.find((t) => t.id === tab)?.label}</h1>
          </div>

          <div className="header-actions">
            {/* Real-time WebSocket connection indicator */}
            <div className="ws-pill" title="Live WebSocket Telemetry Status">
              <span className={`dot ${wsStatus === "connected" ? "live" : wsStatus === "connecting" ? "connecting" : "offline"}`} />
              <Radio size={12} />
              <span>{wsStatus === "connected" ? "LIVE TELEMETRY" : wsStatus === "connecting" ? "CONNECTING..." : "OFFLINE"}</span>
            </div>

            {/* Authentication Persona Switcher */}
            <button
              className="role-badge"
              onClick={() => setAuthModalOpen(true)}
              title="Click to switch demonstration role"
            >
              <Key size={13} />
              <span>{currentPersona.label.split(" (")[0]}</span>
              <span className="status blue" style={{ padding: "2px 6px", fontSize: "9px" }}>
                {currentPersona.role}
              </span>
            </button>

            {/* Simulated Data Badge */}
            <span className="sim-badge" title="Data includes verified analog simulation streams">
              SIMULATED TELEMETRY
            </span>
          </div>
        </header>

        {/* Global Error Banner */}
        {error && (
          <div className="error">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
            <button onClick={() => { setError(""); loadRosterAndMissions(); }}>Dismiss</button>
          </div>
        )}

        {/* =========================================================================
            TAB 0: CREW MANAGEMENT (FLEET ROSTER, CRUD, ARCHIVE)
           ========================================================================= */}
        {tab === "crew" && (
          <CrewManagementPage
            astronauts={astronauts}
            missions={missions}
            selectedAstronautId={selectedAstronautId}
            setSelectedAstronautId={setSelectedAstronautId}
            onNavigateToCalibration={(astroId) => {
              setSelectedAstronautId(astroId);
              setTab("calibration");
            }}
            onNavigateToDashboard={(astroId) => {
              setSelectedAstronautId(astroId);
              setTab("dashboard");
            }}
            onRefreshRoster={loadRosterAndMissions}
            onError={(err) => setError(err)}
          />
        )}

        {/* =========================================================================
            TAB 1: BASELINE CALIBRATION (PRIMARY WORKFLOW)
           ========================================================================= */}
        {tab === "calibration" && (
          <BaselineCalibrationPage
            astronauts={astronauts}
            selectedAstronautId={selectedAstronautId}
            setSelectedAstronautId={setSelectedAstronautId}
            psiBaseline={psiBaseline}
            onCalibrationComplete={() => {
              loadAstronautTelemetry(selectedAstronautId);
            }}
            onNavigateToDashboard={() => setTab("dashboard")}
          />
        )}

        {/* =========================================================================
            TAB 1: ASTRONAUT TELEMETRY DASHBOARD
           ========================================================================= */}
        {tab === "dashboard" && (
          <div>
            {/* Astronaut Selector Bar */}
            <div className="astro-selector">
              <span style={{ fontSize: "12px", fontWeight: "600", color: "#64748b", display: "flex", alignItems: "center", gap: "6px", padding: "0 8px" }}>
                <Users size={14} /> Crew Member:
              </span>
              {astronauts.filter(a => a.status !== "archived" || a.id === selectedAstronautId).map((a) => (
                <button
                  key={a.id}
                  className={`astro-btn ${selectedAstronautId === a.id ? "active" : ""}`}
                  onClick={() => setSelectedAstronautId(a.id)}
                >
                  <b>{a.name}</b>
                  <span style={{ fontSize: "10px", opacity: 0.85 }}>({a.callsign || a.role})</span>
                </button>
              ))}
            </div>

            {/* Active Operational Alerts Banner */}
            {dashboardData?.alerts && dashboardData.alerts.length > 0 && (
              <div className="alerts-container">
                {dashboardData.alerts.map((alert, idx) => (
                  <div key={idx} className={`alert-card ${alert.severity === "critical" ? "critical" : "warning"}`}>
                    <AlertTriangle size={16} />
                    <span><b>[{alert.system.toUpperCase()}]</b> {alert.message}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Top Row: Vitals & PSI Key Metrics */}
            <div className="grid4">
              {/* PSI Stress Metric */}
              <div className="metric-tile">
                <div className="metric-label">Psychological Stress (PSI)</div>
                <div className="metric-value">
                  {dashboardData?.psi_status?.latest_reading?.smoothed_stress ?? "--"}
                  <span className="metric-unit">%</span>
                </div>
                <div className="metric-sub">
                  <span className={`status ${dashboardData?.psi_status?.status || "grey"}`}>
                    {dashboardData?.psi_status?.status_label || "No data"}
                  </span>
                  <span>Dev: {dashboardData?.psi_status?.latest_reading?.stress_deviation ?? 0}%</span>
                </div>
              </div>

              {/* Burnout Risk Score */}
              <div className="metric-tile">
                <div className="metric-label">Burnout Risk (BRS)</div>
                <div className="metric-value">
                  {burnoutAnalytics?.brs ?? dashboardData?.psi_status?.burnout?.brs ?? 0.0}
                  <span className="metric-unit">/100</span>
                </div>
                <div className="metric-sub">
                  <span className={`status ${burnoutAnalytics?.classification === "High" ? "red" : burnoutAnalytics?.classification === "Moderate" ? "yellow" : "green"}`}>
                    {burnoutAnalytics?.classification || "Nominal"}
                  </span>
                  <span>Weekly Avg: {burnoutAnalytics?.weekly_avg ?? 0}%</span>
                </div>
              </div>

              {/* Heart Rate */}
              <div className="metric-tile">
                <div className="metric-label">Heart Rate (Wearable)</div>
                <div className="metric-value">
                  {dashboardData?.physiological?.heart_rate ?? "--"}
                  <span className="metric-unit">bpm</span>
                </div>
                <div className="metric-sub">
                  <HeartPulse size={13} color="#ef4444" />
                  <span>
                    {dashboardData?.physiological?.is_simulated ? "Simulated Stream" : "Hardware Vitals"}
                  </span>
                </div>
              </div>

              {/* Blood Oxygen SpO2 */}
              <div className="metric-tile">
                <div className="metric-label">Blood Oxygen (SpO2)</div>
                <div className="metric-value">
                  {dashboardData?.physiological?.spo2 ?? "--"}
                  <span className="metric-unit">%</span>
                </div>
                <div className="metric-sub">
                  <Wind size={13} color="#3b82f6" />
                  <span>
                    {dashboardData?.physiological?.spo2 ? (dashboardData.physiological.spo2 >= 95 ? "Normal Range" : "Hypoxia Risk") : "Sensor Offline"}
                  </span>
                </div>
              </div>
            </div>

            {/* Middle Grid: Detailed Behavioral Health & Physiological Breakdown */}
            <div className="grid2">
              {/* Card 1: Behavioral Stress & Emotion Profile */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">
                    <Brain size={16} color="#2563eb" /> Behavioral Stress & Affect Tracking
                  </span>
                  <span className={`status ${dashboardData?.psi_status?.status || "grey"}`}>
                    {dashboardData?.psi_status?.status_label || "Awaiting Telemetry"}
                  </span>
                </div>

                <p className="muted" style={{ margin: "0 0 16px" }}>
                  Multimodal Psychological Stress Index derived from voluntary facial affect and baseline normalization.
                </p>

                <div style={{ marginBottom: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                    <span>Current Stress Level</span>
                    <b>{dashboardData?.psi_status?.latest_reading?.smoothed_stress ?? 0}%</b>
                  </div>
                  <div className="gauge-track">
                    <div
                      className={`gauge-fill ${dashboardData?.psi_status?.status || "blue"}`}
                      style={{ width: `${Math.min(100, dashboardData?.psi_status?.latest_reading?.smoothed_stress || 0)}%` }}
                    />
                  </div>
                </div>

                <div className="grid2" style={{ gap: "10px", margin: "14px 0" }}>
                  <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                    <small className="muted">Dominant Affect</small>
                    <div style={{ fontSize: "14px", fontWeight: "600", textTransform: "capitalize", marginTop: "3px" }}>
                      {dashboardData?.psi_status?.latest_reading?.dominant_emotion || "Neutral"}
                    </div>
                  </div>
                  <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                    <small className="muted">Personal Baseline</small>
                    <div style={{ fontSize: "14px", fontWeight: "600", marginTop: "3px" }}>
                      {psiBaseline?.is_calibrated ? (
                        <span style={{ color: "#059669" }}>
                          {psiBaseline.baseline_stress}% (±{psiBaseline.baseline_sigma}%)
                        </span>
                      ) : (
                        <span className="status red" style={{ padding: "2px 6px", fontSize: "10px" }}>
                          NOT CALIBRATED
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {!psiBaseline?.is_calibrated && (
                  <div style={{ margin: "10px 0", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", padding: "8px 12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "11px", color: "#991b1b", fontWeight: "600" }}>
                      ⚠ Personal baseline not calibrated for this astronaut.
                    </span>
                    <button
                      className="primary"
                      onClick={() => setTab("calibration")}
                      style={{ padding: "4px 10px", fontSize: "11px" }}
                    >
                      Calibrate Now
                    </button>
                  </div>
                )}

                <div className="notice">
                  <b>Methodological Safeguard:</b> Facial-expression-derived PSI is an experimental proxy signal and is strictly decoupled from cardiovascular physical exertion.
                </div>
              </div>

              {/* Card 2: Physiological Readiness & Recovery */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">
                    <Activity size={16} color="#10b981" /> Recovery & Operational Readiness
                  </span>
                  <span className={`status ${dashboardData?.recovery?.readiness_classification === "optimal" ? "green" : dashboardData?.recovery?.readiness_classification === "moderate" ? "yellow" : "red"}`}>
                    {dashboardData?.recovery?.readiness_classification?.toUpperCase() || "OPTIMAL"}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "14px" }}>
                  <div style={{ fontSize: "36px", fontWeight: "700", color: "#0f172a" }}>
                    {dashboardData?.recovery?.recovery_index ?? 75}%
                  </div>
                  <small className="muted">Readiness Score</small>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div className="row" style={{ padding: "8px 0" }}>
                    <span style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
                      <Moon size={15} color="#6366f1" /> Sleep Duration
                    </span>
                    <b>{dashboardData?.physiological?.sleep_hours ? `${dashboardData.physiological.sleep_hours} hrs` : "Unreported"}</b>
                  </div>
                  <div className="row" style={{ padding: "8px 0" }}>
                    <span style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
                      <Thermometer size={15} color="#f59e0b" /> Core Temperature
                    </span>
                    <b>{dashboardData?.physiological?.body_temperature ? `${dashboardData.physiological.body_temperature} °C` : "Sensor Offline"}</b>
                  </div>
                  <div className="row" style={{ padding: "8px 0" }}>
                    <span style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
                      <Wind size={15} color="#06b6d4" /> Respiration Rate
                    </span>
                    <b>{dashboardData?.physiological?.respiration_rate ? `${dashboardData.physiological.respiration_rate} brpm` : "Sensor Offline"}</b>
                  </div>
                </div>

                <div style={{ marginTop: "14px", fontSize: "11px", color: "#64748b" }}>
                  Telemetry Source: {dashboardData?.physiological?.source_device || "Wearable Biosensor Array"} ({dashboardData?.physiological?.is_simulated ? "Simulated" : "Real Hardware"})
                </div>
              </div>
            </div>

            {/* Bottom Row: Real-time Telemetry WebSocket Feed */}
            <div className="card" style={{ marginTop: "20px" }}>
              <div className="card-header">
                <span className="card-title">
                  <Radio size={16} color="#8b5cf6" /> Live Subscribed Telemetry Stream (WebSocket)
                </span>
                <small className="muted">{liveEvents.length} events received</small>
              </div>
              {liveEvents.length === 0 ? (
                <p className="muted" style={{ fontStyle: "italic", margin: "8px 0" }}>
                  Listening for real-time telemetry packets... (Use the 'Behavioral PSI Analytics' tab to inject test readings).
                </p>
              ) : (
                <div className="telemetry-log">
                  {liveEvents.map((ev) => (
                    <div key={ev.id} className="log-entry">
                      <span>
                        <span style={{ color: "#94a3b8", marginRight: "8px" }}>[{ev.time}]</span>
                        <b style={{ color: "#38bdf8" }}>{ev.type}</b>
                      </span>
                      <span style={{ color: "#cbd5e1" }}>
                        {ev.data?.smoothed_stress !== undefined && `Stress: ${ev.data.smoothed_stress}% | Dev: ${ev.data.stress_deviation}%`}
                        {ev.data?.heart_rate !== undefined && `HR: ${ev.data.heart_rate} bpm | SpO2: ${ev.data.spo2}%`}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 2: MISSION COMMANDER OVERVIEW
           ========================================================================= */}
        {tab === "mission" && (
          <div>
            {missionData?.mission ? (
              <>
                <div className="card" style={{ marginBottom: "20px" }}>
                  <div className="card-header">
                    <div>
                      <span className="status blue" style={{ marginBottom: "6px" }}>
                        {missionData.mission.status.toUpperCase()}
                      </span>
                      <h2>{missionData.mission.name} ({missionData.mission.code})</h2>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div className="metric-label">Average Crew Stress</div>
                      <div style={{ fontSize: "24px", fontWeight: "700", color: "#2563eb" }}>
                        {missionData.crew_behavioral_average_stress ?? "--"}%
                      </div>
                    </div>
                  </div>
                  <p className="muted">{missionData.mission.description || "Active long-duration deep space exploration mission."}</p>
                </div>

                <h3>Assigned Crew Health Summaries ({missionData.crew_count} Astronauts)</h3>
                <div className="cards">
                  {missionData.crew?.map((c) => (
                    <div key={c.id} className="card">
                      <div className="card-header">
                        <div>
                          <b>{c.name}</b>
                          <small style={{ display: "block", color: "#64748b" }}>{c.role}</small>
                        </div>
                        <span className={`status ${c.psi_status_color || "grey"}`}>
                          {c.psi_status_color === "green" ? "Nominal" : c.psi_status_color === "yellow" ? "Elevated" : "Attention"}
                        </span>
                      </div>

                      <div className="grid2" style={{ gap: "10px", margin: "14px 0" }}>
                        <div style={{ background: "#f8fafc", padding: "8px", borderRadius: "8px", textAlign: "center" }}>
                          <small className="muted">PSI Stress</small>
                          <div style={{ fontSize: "16px", fontWeight: "700" }}>{c.psi_stress ?? "--"}%</div>
                        </div>
                        <div style={{ background: "#f8fafc", padding: "8px", borderRadius: "8px", textAlign: "center" }}>
                          <small className="muted">BRS Risk</small>
                          <div style={{ fontSize: "16px", fontWeight: "700" }}>{c.brs ?? 0.0}</div>
                        </div>
                      </div>

                      <div style={{ fontSize: "12px", color: "#64748b", display: "flex", justifyContent: "space-between" }}>
                        <span>Heart Rate: {c.heart_rate ? `${c.heart_rate} bpm` : "--"}</span>
                        <span>SpO2: {c.spo2 ? `${c.spo2}%` : "--"}</span>
                      </div>

                      {c.alert_count > 0 && (
                        <div style={{ marginTop: "10px", fontSize: "11px", color: "#b91c1c", fontWeight: "600", display: "flex", alignItems: "center", gap: "4px" }}>
                          <AlertTriangle size={12} /> {c.alert_count} active safety alert(s)
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="card">
                <h2>Mission Access Restricted</h2>
                <p className="muted">
                  Mission-wide health summaries are restricted to <b>Flight Surgeon</b> and <b>Mission Director</b> roles.
                </p>
                <button className="primary" onClick={() => setAuthModalOpen(true)}>
                  Switch to Flight Surgeon Demo Role
                </button>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            TAB 3: BEHAVIORAL PSI ANALYTICS & QUICK SIMULATOR
           ========================================================================= */}
        {tab === "psi" && (
          <div className="grid2">
            {/* Left Column: Personal Baseline & 7-Day Chronic Analytics */}
            <div>
              <div className="card" style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                  <div>
                    <h2 style={{ margin: 0 }}>Astronaut Personal Baseline</h2>
                    <p className="muted" style={{ margin: "4px 0 0", fontSize: "12px" }}>
                      Resting emotional parameters calibrated via IQR outlier trimming.
                    </p>
                  </div>
                  <button
                    className="primary"
                    onClick={() => setTab("calibration")}
                    style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", padding: "7px 14px" }}
                  >
                    <Camera size={14} />
                    <span>{psiBaseline?.is_calibrated ? "Recalibrate Baseline" : "Calibrate Baseline"}</span>
                  </button>
                </div>

                {psiBaseline?.is_calibrated ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "14px" }}>
                    <div className="row">
                      <span>Baseline Resting Stress</span>
                      <b>{psiBaseline.baseline_stress}%</b>
                    </div>
                    <div className="row">
                      <span>Variance Tolerance (Sigma)</span>
                      <b>±{psiBaseline.baseline_sigma}%</b>
                    </div>
                    <div className="row">
                      <span>Optimal Operating Range</span>
                      <b>{psiBaseline.optimal_range?.[0]}% – {psiBaseline.optimal_range?.[1]}%</b>
                    </div>
                    <div className="row">
                      <span>High Stress Alert Threshold</span>
                      <b>{psiBaseline.stress_threshold}%</b>
                    </div>
                    <div className="row">
                      <span>Calibration Status</span>
                      <span className="status green">Verified & Calibrated</span>
                    </div>
                    {psiBaseline.calibrated_at && (
                      <div className="row">
                        <span>Calibration Timestamp</span>
                        <small className="muted">{new Date(psiBaseline.calibrated_at).toLocaleString()}</small>
                      </div>
                    )}

                    <div style={{ display: "flex", gap: "8px", marginTop: "6px" }}>
                      <button
                        style={{
                          background: "#f8fafc",
                          color: "#475569",
                          border: "1px solid #cbd5e1",
                          borderRadius: "8px",
                          padding: "6px 12px",
                          fontSize: "11px",
                          fontWeight: "600",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px"
                        }}
                        onClick={handleQuickBenchmark}
                        title="Run 5-pose benchmark calibration without webcam"
                      >
                        <Sparkles size={13} color="#6366f1" />
                        <span>Quick Benchmark Re-test</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: "center", padding: "20px 10px" }}>
                    <span className="status red" style={{ marginBottom: "10px", display: "inline-block" }}>
                      NOT CALIBRATED
                    </span>
                    <p className="muted" style={{ fontStyle: "italic", marginBottom: "16px", fontSize: "13px" }}>
                      No calibrated baseline on record for this astronaut. Establish resting parameters using 5 sequential facial frames.
                    </p>
                    <div style={{ display: "flex", gap: "10px", justifyContent: "center", flexWrap: "wrap" }}>
                      <button
                        className="primary"
                        onClick={() => setTab("calibration")}
                        style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 16px" }}
                      >
                        <Camera size={14} />
                        <span>Open Baseline Calibration</span>
                      </button>
                      <button
                        style={{
                          background: "#f8fafc",
                          color: "#334155",
                          border: "1px solid #cbd5e1",
                          borderRadius: "8px",
                          padding: "8px 14px",
                          fontSize: "12px",
                          fontWeight: "600",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px"
                        }}
                        onClick={handleQuickBenchmark}
                      >
                        <Sparkles size={14} color="#6366f1" />
                        <span>Demonstration Mode</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="card">
                <h2>7-Day Chronic Stress Analysis</h2>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", margin: "12px 0" }}>
                  <span className={`status ${chronicAnalytics?.is_chronic ? "red" : "green"}`}>
                    {chronicAnalytics?.is_chronic ? "CHRONIC PATTERN DETECTED" : "NOMINAL / NO CHRONIC STRESS"}
                  </span>
                </div>
                <p className="muted">{chronicAnalytics?.message || "Continuous monitoring relative to baseline threshold."}</p>
              </div>
            </div>

            {/* Right Column: Interactive Quick Simulator */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <Sliders size={16} color="#2563eb" /> Telemetry Injection Simulator
                </span>
                <span className="sim-badge">INTERACTIVE DEMO</span>
              </div>
              <p className="muted">
                Test real-time calculation, database persistence, and WebSocket broadcasting by injecting telemetry samples.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "6px" }}>
                    <span>Target Stress Level</span>
                    <b>{simStress}%</b>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="95"
                    value={simStress}
                    onChange={(e) => setSimStress(e.target.value)}
                    style={{ width: "100%" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                    Dominant Facial Affect
                  </label>
                  <select
                    value={simEmotion}
                    onChange={(e) => setSimEmotion(e.target.value)}
                    style={{ width: "100%", padding: "8px", borderRadius: "8px", border: "1px solid #cbd5e1" }}
                  >
                    <option value="neutral">Neutral (Calm focus)</option>
                    <option value="happy">Happy (Relaxed engagement)</option>
                    <option value="angry">Angry (Frustration / High arousal)</option>
                    <option value="fear">Fear (Acute vigilance)</option>
                    <option value="sad">Sad (Mental fatigue / Low valence)</option>
                  </select>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "6px" }}>
                    <span>Task Complexity Factor</span>
                    <b>{simTaskComplexity}/10</b>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="0.5"
                    value={simTaskComplexity}
                    onChange={(e) => setSimTaskComplexity(e.target.value)}
                    style={{ width: "100%" }}
                  />
                </div>

                <button
                  className="primary"
                  onClick={handleSendSimulatedReading}
                  disabled={simSending}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
                >
                  <Send size={14} />
                  {simSending ? "Injecting & Broadcasting..." : "Inject Telemetry Packet"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 4: HUMAN HEALTH MAP (Connected to Live Telemetry)
           ========================================================================= */}
        {tab === "body" && (
          <HumanHealthMapPage
            astronauts={astronauts}
            selectedAstronautId={selectedAstronautId}
            setSelectedAstronautId={setSelectedAstronautId}
            dashboardData={dashboardData}
            psiBaseline={psiBaseline}
            psiHistory={psiHistory}
            systems={systems}
            wsStatus={wsStatus}
            currentPersona={currentPersona}
            onNavigateToTab={(t) => setTab(t)}
          />
        )}

        {tab === "env" && (
          <div className="cards">
            {environments.map((e) => (
              <section className="card" key={e.id}>
                <span className="status blue">{e.env_type}</span>
                <h2>{e.name}</h2>
                <p>{e.location}</p>
                <p>{e.duration_days} simulated mission days</p>
                <b>Available Telemetry Streams</b>
                <div className="chips" style={{ margin: "10px 0" }}>
                  {e.streams.map((s) => (
                    <span key={s}>{s}</span>
                  ))}
                </div>
                <small className="muted">Context: {JSON.stringify(e.context)}</small>
              </section>
            ))}
          </div>
        )}

        {/* =========================================================================
            TAB 6: HEALTH ROUTINES (Preserved)
           ========================================================================= */}
        {tab === "routines" && (
          <section className="card">
            <h2>Mission Health Routines</h2>
            <p className="muted">Daily behavioral check-ins and operational wellbeing tasks.</p>
            {routines.length === 0 ? (
              <p>No routines scheduled.</p>
            ) : (
              routines.map((r) => (
                <div className="row" key={r.id}>
                  <div>
                    <b>{r.title}</b>
                    <small>{r.kind} · {r.completed ? "Completed" : "Scheduled"}</small>
                  </div>
                  <button
                    disabled={r.completed}
                    onClick={() => handleCompleteRoutine(r.id)}
                  >
                    {r.completed ? "Completed" : "Mark Complete"}
                  </button>
                </div>
              ))
            )}
            <button
              className="primary"
              onClick={async () => {
                await api.createRoutine({
                  kind: "wellbeing",
                  title: "Voluntary Astronaut Wellbeing Log",
                  astronaut_id: selectedAstronautId
                });
                loadLegacyFeatures();
              }}
            >
              Add Wellbeing Check-in
            </button>
          </section>
        )}

        {/* =========================================================================
            TAB 7: MISSION CHALLENGES (Preserved)
           ========================================================================= */}
        {tab === "challenges" && (
          <div className="cards">
            {challenges.map((c) => (
              <section className="card" key={c.id}>
                <span className="status blue">{c.points} participation points</span>
                <h2>{c.title}</h2>
                <p>{c.description}</p>
                <button className="primary" onClick={() => handleCompleteChallenge(c.id)}>
                  Complete Challenge
                </button>
              </section>
            ))}
          </div>
        )}

        {/* =========================================================================
            TAB 8: HEALTH EDUCATION (Preserved)
           ========================================================================= */}
        {tab === "education" && (
          <div className="cards">
            {education.map((e) => (
              <section className="card" key={e.metric_key}>
                <h2>{e.title}</h2>
                <p><b>What:</b> {e.what}</p>
                <p><b>Why:</b> {e.why}</p>
                <p><b>How:</b> {e.how}</p>
                <p><b>Influences:</b> {e.influences}</p>
                <div className="notice">{e.limitations}</div>
                <p><b>When to seek guidance:</b> {e.when_advice}</p>
              </section>
            ))}
          </div>
        )}

        {/* =========================================================================
            MODAL: AUTHENTICATION PERSONA SWITCHER
           ========================================================================= */}
        {authModalOpen && (
          <div className="modal-overlay" onClick={() => setAuthModalOpen(false)}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
              <h2>Demonstration Login & Role Switcher</h2>
              <p className="muted" style={{ margin: "0 0 16px" }}>
                Select an authorized flight role to demonstrate access control and astronaut isolation.
              </p>

              {DEMO_PERSONAS.map((p) => (
                <div
                  key={p.id}
                  className={`role-option ${currentPersona.id === p.id ? "selected" : ""}`}
                  onClick={() => handleSelectPersona(p)}
                >
                  <div>
                    <b>{p.label}</b>
                    <small style={{ display: "block", color: "#64748b", marginTop: "3px" }}>{p.desc}</small>
                  </div>
                  <span className="status blue" style={{ fontSize: "10px" }}>{p.role}</span>
                </div>
              ))}

              <form onSubmit={handleCustomKeySubmit} style={{ marginTop: "16px", borderTop: "1px solid #e2e8f0", paddingTop: "14px" }}>
                <label style={{ fontSize: "12px", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                  Or Enter Custom API Key
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="password"
                    placeholder="Enter key token..."
                    value={customKeyInput}
                    onChange={(e) => setCustomKeyInput(e.target.value)}
                    style={{ flex: 1, padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1" }}
                  />
                  <button type="submit" className="primary" style={{ margin: 0 }}>Apply</button>
                </div>
              </form>

              <button
                style={{ width: "100%", marginTop: "16px", background: "#f1f5f9", color: "#475569", border: 0, padding: "10px", borderRadius: "8px", cursor: "pointer", fontWeight: "600" }}
                onClick={() => setAuthModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
