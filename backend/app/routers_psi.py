"""
ASTRA MIND — Psychological Stress Index (PSI) APIs
==================================================
REST endpoints for astronaut baseline calibration, live/direct reading ingestion,
historical trend querying, and behavioral analytics (BRS and chronic stress).

ETHICAL & CLINICAL CLARIFICATION:
- PSI outputs are voluntary experimental proxy indicators.
- Facial-expression-derived PSI is NOT interpreted as definitive psychological stress.
- Keep facial-expression-derived PSI separate from physiological stress measurements.
- Do not automatically convert PSI into a clinical brain-health status.
- Preserves individual baseline privacy.
"""

import base64
import logging
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .psi.service import PsiService
from .psi.calibration import decode_base64_frame
from .psi.emotion_analyzer import detect_face_box, analyze_emotion_frame
from .psi.research_monitor import calculate_stress_from_emotions
from .schemas_phase3 import (
    CalibrationSubmitRequest,
    CalibrationResponse,
    CalibrationFrameRequest,
    PsiDirectReadingCreate,
    PsiFrameRequest,
    PsiReadingResponse,
    PsiBaselineResponse,
    BurnoutResponse,
    ChronicResponse,
)
from .security import authenticate_user, enforce_astronaut_isolation
from .websocket_manager import ws_manager

logger = logging.getLogger("astra_mind.psi_router")

router = APIRouter(prefix="/psi", tags=["Psychological Stress Index (PSI)"])


@router.post("/calibrate/{astronaut_id}", response_model=CalibrationResponse)
def submit_calibration(
    astronaut_id: int,
    payload: CalibrationSubmitRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """
    Submit 5-pose neutral calibration data to establish astronaut personal baseline.
    Computes IQR-trimmed resting baseline stress and variance.
    """
    enforce_astronaut_isolation(astronaut_id, user)

    if not payload.poses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calibration requires at least one calibration pose record.",
        )

    poses_dict = [p.model_dump() if hasattr(p, "model_dump") else p.dict() for p in payload.poses]
    service = PsiService(db)

    try:
        baseline_data = service.calibrate_astronaut(astronaut_id, poses_dict)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "success": True,
        "baseline_stress": baseline_data["baseline_stress"],
        "baseline_sigma": baseline_data["baseline_sigma"],
        "optimal_range": baseline_data["optimal_range"],
        "natural_emotions": {
            "angry": baseline_data.get("natural_angry", 0.0),
            "sad": baseline_data.get("natural_sad", 0.0),
            "fear": baseline_data.get("natural_fear", 0.0),
        },
        "valid_photos": baseline_data.get("valid_photos", len(payload.poses)),
    }


@router.post("/calibrate/{astronaut_id}/analyze-frame")
def analyze_calibration_frame(
    astronaut_id: int,
    payload: CalibrationFrameRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """
    Transiently analyze a live webcam calibration frame in memory.
    Evaluates face presence, bounding box, lighting, and resting emotion vector.
    Never persists webcam imagery to disk.
    """
    enforce_astronaut_isolation(astronaut_id, user)

    frame_bgr = decode_base64_frame(payload.frame_base64)
    if frame_bgr is None:
        return {
            "valid": False,
            "face_detected": False,
            "quality": "unreadable",
            "error": "Unable to decode webcam frame.",
        }

    # Lighting check
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(np.mean(gray))
    if mean_brightness < 25.0:
        return {
            "valid": False,
            "face_detected": False,
            "quality": "too_dark",
            "error": "Lighting is too dark. Increase ambient light.",
            "mean_brightness": round(mean_brightness, 1),
        }
    if mean_brightness > 235.0:
        return {
            "valid": False,
            "face_detected": False,
            "quality": "washed_out",
            "error": "Lighting is overexposed or washed out.",
            "mean_brightness": round(mean_brightness, 1),
        }

    # Face detection
    face_box = detect_face_box(frame_bgr)
    if not face_box:
        return {
            "valid": False,
            "face_detected": False,
            "quality": "no_face",
            "error": "No face detected in camera view. Center your face in frame.",
            "mean_brightness": round(mean_brightness, 1),
        }

    if face_box["w"] < 40 or face_box["h"] < 40:
        return {
            "valid": False,
            "face_detected": True,
            "face_box": face_box,
            "quality": "too_small",
            "error": "Face too small / too far from camera. Move closer.",
            "mean_brightness": round(mean_brightness, 1),
        }

    # Emotion analysis
    emotions = analyze_emotion_frame(frame_bgr, face_box=face_box)
    if not emotions:
        return {
            "valid": False,
            "face_detected": True,
            "face_box": face_box,
            "quality": "analysis_failed",
            "error": "Could not extract facial expression features.",
            "mean_brightness": round(mean_brightness, 1),
        }

    calc_stress = calculate_stress_from_emotions(emotions, task_complexity=5.0, motion_level=0.0)
    dominant = max(emotions, key=emotions.get) if emotions else "neutral"

    return {
        "valid": True,
        "face_detected": True,
        "face_box": face_box,
        "quality": "good",
        "lighting": "adequate",
        "mean_brightness": round(mean_brightness, 1),
        "emotions": emotions,
        "dominant_emotion": dominant,
        "calculated_stress": calc_stress,
        "pose_name": payload.pose_name or "neutral",
        "photo_number": payload.photo_number or 1,
    }


@router.post("/calibrate/{astronaut_id}/benchmark", response_model=CalibrationResponse)
def run_benchmark_calibration(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """
    Execute standardized 5-pose demonstration calibration when physical webcam is unavailable.
    Applies the full IQR-trimmed baseline algorithm and persists to database.
    """
    enforce_astronaut_isolation(astronaut_id, user)
    service = PsiService(db)

    benchmark_poses = [
        {"photo_number": 1, "pose_name": "neutral_forward", "valid": True, "emotions": {"neutral": 0.85, "happy": 0.15, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}},
        {"photo_number": 2, "pose_name": "neutral_tilt_left", "valid": True, "emotions": {"neutral": 0.90, "happy": 0.10, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}},
        {"photo_number": 3, "pose_name": "neutral_tilt_right", "valid": True, "emotions": {"neutral": 0.88, "happy": 0.12, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}},
        {"photo_number": 4, "pose_name": "neutral_up", "valid": True, "emotions": {"neutral": 0.82, "happy": 0.18, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}},
        {"photo_number": 5, "pose_name": "neutral_down", "valid": True, "emotions": {"neutral": 0.86, "happy": 0.14, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}},
    ]

    baseline_data = service.calibrate_astronaut(astronaut_id, benchmark_poses)
    return {
        "success": True,
        "baseline_stress": baseline_data["baseline_stress"],
        "baseline_sigma": baseline_data["baseline_sigma"],
        "optimal_range": baseline_data["optimal_range"],
        "natural_emotions": {
            "angry": baseline_data.get("natural_angry", 0.0),
            "sad": baseline_data.get("natural_sad", 0.0),
            "fear": baseline_data.get("natural_fear", 0.0),
        },
        "valid_photos": baseline_data.get("valid_photos", 5),
    }


@router.get("/baseline/{astronaut_id}", response_model=PsiBaselineResponse)
def get_astronaut_baseline(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Retrieve personal baseline parameters for an astronaut."""
    enforce_astronaut_isolation(astronaut_id, user)
    service = PsiService(db)
    baseline = service.get_baseline(astronaut_id)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No baseline found for astronaut {astronaut_id}",
        )
    return baseline


@router.post("/process-frame/{astronaut_id}")
async def process_frame(
    astronaut_id: int,
    payload: PsiFrameRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """
    Ingest a base64-encoded webcam/video frame, run facial detection & PSI engine,
    and persist the resulting behavioral stress reading.
    """
    enforce_astronaut_isolation(astronaut_id, user)

    try:
        raw_b64 = payload.frame_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            raise ValueError("cv2.imdecode produced empty array")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image data: {str(e)}",
        )

    service = PsiService(db)
    try:
        reading = service.process_and_persist_frame(
            astronaut_id=astronaut_id,
            frame_bgr=frame_bgr,
            mission_id=payload.mission_id,
            task_complexity=payload.task_complexity,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not reading:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No face detected or unable to extract facial affect from frame.",
        )

    # Real-time WebSocket broadcasting
    await ws_manager.broadcast_to_astronaut(astronaut_id, {
        "type": "psi_frame_reading",
        "data": reading,
    })
    if payload.mission_id:
        await ws_manager.broadcast_to_mission(payload.mission_id, {
            "type": "crew_psi_frame_reading",
            "astronaut_id": astronaut_id,
            "data": reading,
        })

    return reading


@router.post("/readings/{astronaut_id}", response_model=PsiReadingResponse, status_code=status.HTTP_201_CREATED)
async def submit_direct_reading(
    astronaut_id: int,
    payload: PsiDirectReadingCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """
    Submit pre-calculated PSI readings (e.g. from edge client device or offline processing).
    Validates mathematical ranges and persists to flight records.
    """
    enforce_astronaut_isolation(astronaut_id, user)
    service = PsiService(db)

    try:
        reading = service.record_direct_reading(
            astronaut_id=astronaut_id,
            raw_stress=payload.raw_stress,
            smoothed_stress=payload.smoothed_stress,
            dominant_emotion=payload.dominant_emotion,
            emotion_vector=payload.emotion_vector,
            motion_level=payload.motion_level,
            task_complexity=payload.task_complexity,
            mission_id=payload.mission_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Real-time WebSocket broadcasting
    await ws_manager.broadcast_to_astronaut(astronaut_id, {
        "type": "psi_reading",
        "data": reading,
    })
    if payload.mission_id:
        await ws_manager.broadcast_to_mission(payload.mission_id, {
            "type": "crew_psi_reading",
            "astronaut_id": astronaut_id,
            "data": reading,
        })

    return reading


@router.get("/readings/{astronaut_id}/latest")
def get_latest_reading(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Retrieve the latest PSI telemetry and baseline summary for an astronaut."""
    enforce_astronaut_isolation(astronaut_id, user)
    service = PsiService(db)
    return service.get_astronaut_status(astronaut_id)


@router.get("/readings/{astronaut_id}/history", response_model=List[Dict[str, Any]])
def get_reading_history(
    astronaut_id: int,
    hours: int = 24,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Retrieve recent historical PSI readings for trend analysis."""
    enforce_astronaut_isolation(astronaut_id, user)
    service = PsiService(db)
    return service.get_reading_history(astronaut_id, hours=hours, limit=limit)


@router.get("/analytics/chronic/{astronaut_id}", response_model=ChronicResponse)
def get_chronic_stress_analytics(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Evaluate 7-day rolling chronic stress pattern relative to personal baseline."""
    enforce_astronaut_isolation(astronaut_id, user)
    service = PsiService(db)
    return service.get_chronic_stress_analytics(astronaut_id)


@router.get("/analytics/burnout/{astronaut_id}", response_model=BurnoutResponse)
def get_burnout_analytics(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Calculate Burnout Risk Score (BRS) combining 7-day stress, variance, and task load."""
    enforce_astronaut_isolation(astronaut_id, user)
    service = PsiService(db)
    return service.get_burnout_analytics(astronaut_id)
