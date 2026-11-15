"""
ASTRA MIND — PSI Persistence & Behavioral Intelligence Service
==============================================================
Orchestrates the Phase 1 PSI algorithmic engine with the database repository.
Provides high-level business logic for astronaut calibration, frame analysis
persistence, trend evaluation, and behavioral risk scoring.

ETHICAL & CLINICAL CLARIFICATION:
- PSI outputs are experimental proxy signals.
- Facial-expression-derived PSI is NOT interpreted as definitive psychological stress.
- Keep facial-expression-derived PSI separate from physiological stress measurements.
- Do not automatically convert PSI into a clinical brain-health status.
- Preserves individual baseline privacy.
"""

import math
import statistics
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from .repository import PsiRepository
from .research_monitor import (
    ResearchStressMonitor,
    calculate_stress_from_emotions,
    calculate_emotional_stress,
    calculate_brs,
    classify_brs,
    detect_chronic_stress,
)
from .calibration import calculate_baseline_stress
from .emotion_analyzer import analyze_emotion_frame, detect_face_box, get_last_features

# In-memory registry of active monitor sessions per astronaut to maintain
# rolling smoothing windows and motion differencing state across frame streams
_active_monitors: Dict[int, ResearchStressMonitor] = {}


def get_active_monitor(astronaut_id: int, baseline_stress: float = 25.0, baseline_sigma: float = 5.0) -> ResearchStressMonitor:
    """Retrieve or initialize an active ResearchStressMonitor instance for an astronaut."""
    if astronaut_id not in _active_monitors:
        _active_monitors[astronaut_id] = ResearchStressMonitor(
            staff_baseline=baseline_stress,
            baseline_sigma=baseline_sigma,
        )
    return _active_monitors[astronaut_id]


def clear_active_monitor(astronaut_id: int) -> None:
    """Reset the in-memory monitor session for an astronaut."""
    _active_monitors.pop(astronaut_id, None)


class PsiService:
    """Service providing end-to-end PSI workflows integrated with persistent storage."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PsiRepository(db)

    # =========================================================================
    # BASELINE & CALIBRATION WORKFLOWS
    # =========================================================================

    def get_baseline(self, astronaut_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve astronaut baseline configuration."""
        rec = self.repo.get_baseline(astronaut_id)
        if not rec:
            return None
        return {
            "astronaut_id": rec.astronaut_id,
            "is_calibrated": rec.is_calibrated,
            "baseline_stress": rec.baseline_stress,
            "baseline_sigma": rec.baseline_sigma,
            "optimal_range": [rec.optimal_range_low, rec.optimal_range_high],
            "optimal_range_low": rec.optimal_range_low,
            "optimal_range_high": rec.optimal_range_high,
            "natural_angry": rec.natural_angry,
            "natural_sad": rec.natural_sad,
            "natural_fear": rec.natural_fear,
            "stress_threshold": rec.stress_threshold,
            "calibrated_at": rec.calibrated_at.isoformat() if rec.calibrated_at else None,
        }

    def calibrate_astronaut(
        self,
        astronaut_id: int,
        calibration_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Process 5-photo calibration results, compute IQR-trimmed baseline,
        persist baseline and calibration metadata to database.
        """
        if not isinstance(calibration_results, list):
            raise ValueError("calibration_results must be a list of photo analyses")

        # Compute resting emotional stress for each valid photo
        enriched_results = []
        for i, item in enumerate(calibration_results):
            emotions = item.get("emotions", {})
            is_valid = bool(item.get("valid", True)) and bool(emotions)
            calc_stress = None
            dominant = None
            if is_valid and isinstance(emotions, dict):
                calc_stress = calculate_emotional_stress(emotions)
                dominant = max(emotions, key=emotions.get) if emotions else None

            enriched_results.append({
                "photo_number": item.get("photo_number", i + 1),
                "pose_name": item.get("pose_name", f"pose_{i+1}"),
                "valid": is_valid,
                "emotions": emotions,
                "dominant_emotion": dominant,
                "calculated_stress": calc_stress,
            })

        # Calculate robust baseline with IQR trimming
        baseline_data = calculate_baseline_stress(enriched_results)

        # Update database baseline record
        self.repo.update_baseline(
            astronaut_id=astronaut_id,
            baseline_stress=baseline_data["baseline_stress"],
            baseline_sigma=baseline_data["baseline_sigma"],
            optimal_range_low=baseline_data["optimal_range"][0],
            optimal_range_high=baseline_data["optimal_range"][1],
            natural_angry=baseline_data.get("natural_angry", 0.0),
            natural_sad=baseline_data.get("natural_sad", 0.0),
            natural_fear=baseline_data.get("natural_fear", 0.0),
            is_calibrated=True,
        )

        # Persist calibration metadata (no personal images stored)
        self.repo.save_calibration_records(astronaut_id, enriched_results)

        # Reset in-memory session monitor to update baseline parameters
        clear_active_monitor(astronaut_id)

        return baseline_data

    # =========================================================================
    # LIVE FRAME INGESTION & READING PERSISTENCE
    # =========================================================================

    def process_and_persist_frame(
        self,
        astronaut_id: int,
        frame_bgr: Any,
        mission_id: Optional[int] = None,
        task_complexity: float = 5.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Ingest an OpenCV BGR frame, compute PSI metrics using the in-memory
        monitor session, and atomically persist the reading to database.
        """
        # Validate inputs
        if frame_bgr is None:
            raise ValueError("frame_bgr cannot be None")
        task_complexity = max(1.0, min(10.0, float(task_complexity)))

        baseline_rec = self.repo.get_or_create_baseline(astronaut_id)
        monitor = get_active_monitor(
            astronaut_id,
            baseline_stress=baseline_rec.baseline_stress,
            baseline_sigma=baseline_rec.baseline_sigma,
        )

        face_box = detect_face_box(frame_bgr)
        reading = monitor.process_frame(
            frame_bgr,
            staff_id=None,
            db=None,
            force=True,
            face_box=face_box,
            task_complexity=task_complexity,
        )

        if not reading:
            return None

        # Calculate deviation from baseline
        deviation = round(reading["smoothed_stress"] - baseline_rec.baseline_stress, 2)
        reading["stress_deviation"] = deviation
        reading["stress_trend"] = monitor.stress_trend

        # Persist to database
        db_reading = self.repo.save_reading(
            astronaut_id=astronaut_id,
            raw_stress=reading["raw_stress"],
            smoothed_stress=reading["smoothed_stress"],
            stress_deviation=deviation,
            stress_trend=reading["stress_trend"],
            dominant_emotion=reading["dominant_emotion"],
            emotion_vector=reading["emotion_vector"],
            motion_level=reading["motion_level"],
            motion_detected=reading["motion_detected"],
            mission_id=mission_id,
            mission_phase="nominal_operations",
            task_complexity=task_complexity,
            environmental_factor=1.0,
            risk_level=reading["risk_level"],
        )

        # Add visual overlay data for frontend
        reading["id"] = db_reading.id
        reading["face_box"] = face_box
        reading["expression"] = get_last_features()
        return reading

    def record_direct_reading(
        self,
        astronaut_id: int,
        raw_stress: float,
        smoothed_stress: float,
        dominant_emotion: str,
        emotion_vector: Dict[str, float],
        motion_level: float = 0.0,
        task_complexity: float = 5.0,
        mission_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Directly record and validate a calculated stress reading without frame processing."""
        # Validation checks
        if not (0.0 <= raw_stress <= 100.0) or math.isnan(raw_stress):
            raise ValueError(f"Invalid raw_stress: {raw_stress}")
        if not (0.0 <= smoothed_stress <= 100.0) or math.isnan(smoothed_stress):
            raise ValueError(f"Invalid smoothed_stress: {smoothed_stress}")
        if not isinstance(emotion_vector, dict) or not emotion_vector:
            raise ValueError("emotion_vector must be a non-empty dictionary")

        baseline_rec = self.repo.get_or_create_baseline(astronaut_id)
        deviation = round(smoothed_stress - baseline_rec.baseline_stress, 2)
        risk_level = "high" if smoothed_stress > baseline_rec.baseline_stress + 2 * baseline_rec.baseline_sigma else "low"

        rec = self.repo.save_reading(
            astronaut_id=astronaut_id,
            raw_stress=raw_stress,
            smoothed_stress=smoothed_stress,
            stress_deviation=deviation,
            dominant_emotion=dominant_emotion,
            emotion_vector=emotion_vector,
            motion_level=motion_level,
            task_complexity=task_complexity,
            mission_id=mission_id,
            risk_level=risk_level,
        )

        return {
            "id": rec.id,
            "astronaut_id": rec.astronaut_id,
            "raw_stress": rec.raw_stress,
            "smoothed_stress": rec.smoothed_stress,
            "stress_deviation": rec.stress_deviation,
            "dominant_emotion": rec.dominant_emotion,
            "risk_level": rec.risk_level,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
        }

    # =========================================================================
    # STATUS & RETRIEVAL WORKFLOWS
    # =========================================================================

    def get_astronaut_status(self, astronaut_id: int) -> Dict[str, Any]:
        """
        Provides current behavioral health telemetry status for an astronaut.
        Used by the health map (e.g. 'brain' body system).
        """
        baseline = self.repo.get_baseline(astronaut_id)
        latest = self.repo.get_latest_reading(astronaut_id)

        if not latest:
            return {
                "astronaut_id": astronaut_id,
                "status": "grey",
                "explanation": "No source PSI measurements recorded for this astronaut.",
                "measurements": [],
                "baseline": None,
            }

        # Status categorization (behavioral proxy indicator, not clinical status)
        base_val = baseline.baseline_stress if baseline else 25.0
        opt_high = baseline.optimal_range_high if baseline else 35.0
        threshold = baseline.stress_threshold if baseline else 70.0
        current_stress = latest.smoothed_stress

        if current_stress <= opt_high:
            status_color = "green"
            status_label = "nominal"
        elif current_stress <= threshold:
            status_color = "yellow"
            status_label = "elevated"
        else:
            status_color = "red"
            status_label = "high_stress"

        return {
            "astronaut_id": astronaut_id,
            "status": status_color,
            "status_label": status_label,
            "latest_reading": {
                "raw_stress": latest.raw_stress,
                "smoothed_stress": latest.smoothed_stress,
                "stress_deviation": latest.stress_deviation,
                "dominant_emotion": latest.dominant_emotion,
                "motion_level": latest.motion_level,
                "risk_level": latest.risk_level,
                "created_at": latest.created_at.isoformat() if latest.created_at else None,
            },
            "baseline": {
                "baseline_stress": base_val,
                "optimal_range": [baseline.optimal_range_low, baseline.optimal_range_high] if baseline else [15.0, 35.0],
                "stress_threshold": threshold,
                "is_calibrated": baseline.is_calibrated if baseline else False,
            },
            "measurements": [
                {"name": "PSI Stress Score", "value": latest.smoothed_stress, "unit": "%"},
                {"name": "Deviation from Baseline", "value": latest.stress_deviation, "unit": "%"},
                {"name": "Dominant Affect", "value": latest.dominant_emotion, "unit": ""},
                {"name": "Physical Motion", "value": latest.motion_level, "unit": "/10"},
            ],
            "explanation": "Psychological Stress Index derived from voluntary behavioral tracking.",
        }

    def get_reading_history(self, astronaut_id: int, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent historical readings for an astronaut."""
        readings = self.repo.get_readings_history(astronaut_id, hours=hours, limit=limit)
        return [
            {
                "id": r.id,
                "raw_stress": r.raw_stress,
                "smoothed_stress": r.smoothed_stress,
                "stress_deviation": r.stress_deviation,
                "stress_trend": r.stress_trend,
                "dominant_emotion": r.dominant_emotion,
                "motion_level": r.motion_level,
                "risk_level": r.risk_level,
                "task_complexity": r.task_complexity,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in readings
        ]

    # =========================================================================
    # ANALYTICS: BURNOUT & CHRONIC STRESS
    # =========================================================================

    def get_burnout_analytics(self, astronaut_id: int) -> Dict[str, Any]:
        """Compute Burnout Risk Score (BRS) over a 7-day window."""
        readings = self.repo.get_weekly_readings(astronaut_id, days=7)
        if not readings:
            return {
                "astronaut_id": astronaut_id,
                "brs": 0.0,
                "classification": "Low",
                "weekly_avg": 0.0,
                "variability": 0.0,
                "task_load": 0.0,
                "reading_count": 0,
            }

        scores = [r.smoothed_stress for r in readings]
        weekly_avg = round(statistics.mean(scores), 1)
        variability = round(statistics.stdev(scores), 1) if len(scores) > 1 else 0.0
        task_load = round(statistics.mean([r.task_complexity for r in readings]) * 10.0, 1)

        score = calculate_brs(weekly_avg, variability, task_load)
        classification = classify_brs(score)

        return {
            "astronaut_id": astronaut_id,
            "brs": score,
            "classification": classification,
            "weekly_avg": weekly_avg,
            "variability": variability,
            "task_load": task_load,
            "reading_count": len(scores),
        }

    def get_chronic_stress_analytics(self, astronaut_id: int) -> Dict[str, Any]:
        """Evaluate 7-day rolling chronic stress pattern."""
        baseline_rec = self.repo.get_baseline(astronaut_id)
        base_val = baseline_rec.baseline_stress if baseline_rec else 25.0

        daily_avgs = self.repo.get_daily_averages(astronaut_id, days=7)
        scores = [d["avg_stress"] for d in daily_avgs]
        is_chronic = detect_chronic_stress(scores, base_val)

        return {
            "astronaut_id": astronaut_id,
            "is_chronic": is_chronic,
            "baseline": base_val,
            "threshold": base_val + 15.0,
            "daily_averages": daily_avgs,
            "message": "Elevated stress sustained over 7 days" if is_chronic else "No chronic stress pattern detected",
        }
