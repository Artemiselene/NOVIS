"""
ASTRA MIND — PSI Database Repository
=====================================
Encapsulates all database persistence and retrieval operations for the
Psychological Stress Index (PSI) behavioral health intelligence engine.

Key Principles:
- Strict Astronaut Isolation: Every query and transaction is explicitly
  scoped to astronaut_id to prevent multi-astronaut data leakage.
- Transaction Safety: Manages sessions and atomic commits/rollbacks.
- Privacy Preservation: No raw biometric image data is persisted.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete, desc, func
from sqlalchemy.orm import Session

from app.models import AstronautPsiBaseline, PsiStressReading, PsiCalibrationMetadata


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PsiRepository:
    """Repository managing persistence for PSI baselines, readings, and calibration records."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # BASELINE OPERATIONS
    # =========================================================================

    def get_baseline(self, astronaut_id: int) -> Optional[AstronautPsiBaseline]:
        """Retrieve baseline record for an astronaut, or None if not registered."""
        stmt = select(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id == astronaut_id)
        return self.db.scalar(stmt)

    def get_or_create_baseline(
        self,
        astronaut_id: int,
        default_baseline: float = 25.0,
        default_sigma: float = 5.0,
    ) -> AstronautPsiBaseline:
        """Retrieve existing baseline or create an uncalibrated default record."""
        baseline = self.get_baseline(astronaut_id)
        if not baseline:
            baseline = AstronautPsiBaseline(
                astronaut_id=astronaut_id,
                is_calibrated=False,
                baseline_stress=default_baseline,
                baseline_sigma=default_sigma,
                optimal_range_low=max(0.0, default_baseline - 0.8 * default_sigma),
                optimal_range_high=min(100.0, default_baseline + 1.5 * default_sigma),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.db.add(baseline)
            self.db.commit()
            self.db.refresh(baseline)
        return baseline

    def update_baseline(
        self,
        astronaut_id: int,
        baseline_stress: float,
        baseline_sigma: float,
        optimal_range_low: float,
        optimal_range_high: float,
        natural_angry: float = 0.0,
        natural_sad: float = 0.0,
        natural_fear: float = 0.0,
        stress_threshold: float = 70.0,
        is_calibrated: bool = True,
    ) -> AstronautPsiBaseline:
        """Update or create astronaut calibration baseline."""
        baseline = self.get_baseline(astronaut_id)
        now = utcnow()
        if not baseline:
            baseline = AstronautPsiBaseline(
                astronaut_id=astronaut_id,
                is_calibrated=is_calibrated,
                baseline_stress=baseline_stress,
                baseline_sigma=baseline_sigma,
                optimal_range_low=optimal_range_low,
                optimal_range_high=optimal_range_high,
                natural_angry=natural_angry,
                natural_sad=natural_sad,
                natural_fear=natural_fear,
                stress_threshold=stress_threshold,
                calibrated_at=now if is_calibrated else None,
                created_at=now,
                updated_at=now,
            )
            self.db.add(baseline)
        else:
            baseline.is_calibrated = is_calibrated
            baseline.baseline_stress = baseline_stress
            baseline.baseline_sigma = baseline_sigma
            baseline.optimal_range_low = optimal_range_low
            baseline.optimal_range_high = optimal_range_high
            baseline.natural_angry = natural_angry
            baseline.natural_sad = natural_sad
            baseline.natural_fear = natural_fear
            baseline.stress_threshold = stress_threshold
            if is_calibrated:
                baseline.calibrated_at = now
            baseline.updated_at = now

        self.db.commit()
        self.db.refresh(baseline)
        return baseline

    # =========================================================================
    # STRESS READING OPERATIONS
    # =========================================================================

    def save_reading(
        self,
        astronaut_id: int,
        raw_stress: float,
        smoothed_stress: float,
        dominant_emotion: str,
        emotion_vector: Dict[str, float],
        stress_deviation: float = 0.0,
        stress_trend: str = "stable",
        motion_level: float = 0.0,
        motion_detected: bool = False,
        mission_id: Optional[int] = None,
        mission_phase: str = "nominal_operations",
        task_complexity: float = 5.0,
        environmental_factor: float = 1.0,
        risk_level: str = "low",
        timestamp: Optional[datetime] = None,
    ) -> PsiStressReading:
        """Persist a live stress monitoring frame reading."""
        baseline = self.get_baseline(astronaut_id)
        baseline_id = baseline.id if baseline else None

        reading = PsiStressReading(
            baseline_id=baseline_id,
            astronaut_id=astronaut_id,
            mission_id=mission_id,
            raw_stress=float(raw_stress),
            smoothed_stress=float(smoothed_stress),
            stress_deviation=float(stress_deviation),
            stress_trend=str(stress_trend),
            dominant_emotion=str(dominant_emotion),
            emotion_vector=dict(emotion_vector),
            motion_level=float(motion_level),
            motion_detected=bool(motion_detected),
            mission_phase=str(mission_phase),
            task_complexity=float(task_complexity),
            environmental_factor=float(environmental_factor),
            risk_level=str(risk_level),
            created_at=timestamp or utcnow(),
        )
        self.db.add(reading)
        self.db.commit()
        self.db.refresh(reading)
        return reading

    def get_latest_reading(self, astronaut_id: int) -> Optional[PsiStressReading]:
        """Get the most recent stress reading for an astronaut."""
        stmt = (
            select(PsiStressReading)
            .where(PsiStressReading.astronaut_id == astronaut_id)
            .order_by(desc(PsiStressReading.created_at))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get_readings_history(
        self,
        astronaut_id: int,
        hours: Optional[int] = 24,
        limit: int = 200,
    ) -> List[PsiStressReading]:
        """
        Retrieve readings for an astronaut over a given hourly window,
        ordered from newest to oldest.
        """
        stmt = select(PsiStressReading).where(PsiStressReading.astronaut_id == astronaut_id)
        if hours is not None and hours > 0:
            since = utcnow() - timedelta(hours=hours)
            stmt = stmt.where(PsiStressReading.created_at >= since)
        stmt = stmt.order_by(desc(PsiStressReading.created_at)).limit(limit)
        return list(self.db.scalars(stmt).all())

    # =========================================================================
    # CALIBRATION METADATA OPERATIONS
    # =========================================================================

    def save_calibration_records(
        self,
        astronaut_id: int,
        records: List[Dict[str, Any]],
    ) -> List[PsiCalibrationMetadata]:
        """
        Save statistical calibration metadata for an astronaut's baseline photos.
        Does NOT store personal photos or image files.
        """
        baseline = self.get_or_create_baseline(astronaut_id)

        # Clear any prior calibration records for fresh calibration
        self.db.execute(
            delete(PsiCalibrationMetadata).where(
                PsiCalibrationMetadata.astronaut_id == astronaut_id
            )
        )

        saved = []
        for r in records:
            meta = PsiCalibrationMetadata(
                baseline_id=baseline.id,
                astronaut_id=astronaut_id,
                pose_name=r.get("pose_name", "unknown"),
                photo_number=int(r.get("photo_number", 1)),
                is_valid=bool(r.get("valid", True)),
                dominant_emotion=r.get("dominant_emotion"),
                emotions_json=r.get("emotions", {}),
                calculated_stress=float(r["calculated_stress"]) if r.get("calculated_stress") is not None else None,
                created_at=utcnow(),
            )
            self.db.add(meta)
            saved.append(meta)

        self.db.commit()
        for s in saved:
            self.db.refresh(s)
        return saved

    def get_calibration_records(self, astronaut_id: int) -> List[PsiCalibrationMetadata]:
        """Retrieve calibration pose records for an astronaut."""
        stmt = (
            select(PsiCalibrationMetadata)
            .where(PsiCalibrationMetadata.astronaut_id == astronaut_id)
            .order_by(PsiCalibrationMetadata.photo_number)
        )
        return list(self.db.scalars(stmt).all())

    # =========================================================================
    # ANALYTICS & ROLLING QUERIES
    # =========================================================================

    def get_weekly_readings(self, astronaut_id: int, days: int = 7) -> List[PsiStressReading]:
        """Retrieve all stress readings from the last N days for trend and BRS calculation."""
        since = utcnow() - timedelta(days=days)
        stmt = (
            select(PsiStressReading)
            .where(
                PsiStressReading.astronaut_id == astronaut_id,
                PsiStressReading.created_at >= since,
            )
            .order_by(PsiStressReading.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_daily_averages(self, astronaut_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Computes day-by-day average smoothed stress for chronic stress tracking.
        Groups by date (UTC).
        """
        readings = self.get_weekly_readings(astronaut_id, days=days)
        daily_buckets: Dict[str, List[float]] = {}
        for r in readings:
            day_str = r.created_at.strftime("%Y-%m-%d") if r.created_at else "unknown"
            daily_buckets.setdefault(day_str, []).append(r.smoothed_stress)

        return [
            {
                "date": d,
                "avg_stress": round(sum(scores) / len(scores), 1),
                "count": len(scores),
            }
            for d, scores in sorted(daily_buckets.items())
        ]

    def delete_astronaut_data(self, astronaut_id: int) -> bool:
        """Erase all PSI records for an astronaut (baseline, readings, calibration metadata)."""
        self.db.execute(
            delete(PsiStressReading).where(PsiStressReading.astronaut_id == astronaut_id)
        )
        self.db.execute(
            delete(PsiCalibrationMetadata).where(PsiCalibrationMetadata.astronaut_id == astronaut_id)
        )
        self.db.execute(
            delete(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id == astronaut_id)
        )
        self.db.commit()
        return True
