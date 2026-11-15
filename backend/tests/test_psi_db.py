"""
ASTRA MIND — PSI Database Integration & Persistence Tests
==========================================================
Validates SQLAlchemy 2.0 ORM persistence, retrieval, astronaut isolation,
foreign key relationships, cascade behaviors, and error handling for:
- AstronautPsiBaseline
- PsiStressReading
- PsiCalibrationMetadata
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import AstronautPsiBaseline, PsiStressReading, PsiCalibrationMetadata
from app.psi.repository import PsiRepository
from app.psi.service import PsiService, clear_active_monitor


@pytest.fixture
def db_session():
    """In-memory SQLite database session isolated per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# 1. BASELINE PERSISTENCE & RETRIEVAL
# =============================================================================
class TestBaselinePersistence:

    def test_get_or_create_default_baseline(self, db_session):
        repo = PsiRepository(db_session)
        baseline = repo.get_or_create_baseline(astronaut_id=101)

        assert baseline is not None
        assert baseline.astronaut_id == 101
        assert baseline.is_calibrated is False
        assert baseline.baseline_stress == 25.0
        assert baseline.baseline_sigma == 5.0
        assert baseline.optimal_range_low == 21.0
        assert baseline.optimal_range_high == 32.5

    def test_update_baseline(self, db_session):
        repo = PsiRepository(db_session)
        updated = repo.update_baseline(
            astronaut_id=101,
            baseline_stress=30.0,
            baseline_sigma=4.5,
            optimal_range_low=26.4,
            optimal_range_high=36.75,
            natural_angry=2.0,
            natural_sad=3.0,
            natural_fear=1.5,
            is_calibrated=True,
        )

        assert updated.is_calibrated is True
        assert updated.baseline_stress == 30.0
        assert updated.baseline_sigma == 4.5
        assert updated.calibrated_at is not None

        # Verify query from database
        fetched = repo.get_baseline(astronaut_id=101)
        assert fetched.id == updated.id
        assert fetched.baseline_stress == 30.0


# =============================================================================
# 2. STRESS READING PERSISTENCE & HISTORY RETRIEVAL
# =============================================================================
class TestStressReadingPersistence:

    def test_save_and_retrieve_reading(self, db_session):
        repo = PsiRepository(db_session)
        emotions = {"angry": 5.0, "neutral": 80.0, "happy": 15.0}

        reading = repo.save_reading(
            astronaut_id=101,
            raw_stress=18.5,
            smoothed_stress=19.2,
            dominant_emotion="neutral",
            emotion_vector=emotions,
            stress_deviation=-5.8,
            motion_level=1.2,
            motion_detected=False,
            task_complexity=5.0,
            risk_level="low",
        )

        assert reading.id is not None
        assert reading.astronaut_id == 101
        assert reading.raw_stress == 18.5
        assert reading.smoothed_stress == 19.2
        assert reading.emotion_vector == emotions

        # Fetch latest reading
        latest = repo.get_latest_reading(astronaut_id=101)
        assert latest is not None
        assert latest.id == reading.id
        assert latest.dominant_emotion == "neutral"

    def test_history_hourly_window_filtering(self, db_session):
        repo = PsiRepository(db_session)
        now = datetime.now(timezone.utc)

        # Reading from 2 hours ago
        repo.save_reading(
            astronaut_id=101, raw_stress=20.0, smoothed_stress=20.0,
            dominant_emotion="neutral", emotion_vector={"neutral": 100},
            timestamp=now - timedelta(hours=2)
        )
        # Reading from 30 hours ago (outside 24h window)
        repo.save_reading(
            astronaut_id=101, raw_stress=45.0, smoothed_stress=45.0,
            dominant_emotion="angry", emotion_vector={"angry": 100},
            timestamp=now - timedelta(hours=30)
        )

        # 24h filter should return only 1 reading
        history_24h = repo.get_readings_history(astronaut_id=101, hours=24)
        assert len(history_24h) == 1
        assert history_24h[0].raw_stress == 20.0

        # All-time (hours=None) should return both
        history_all = repo.get_readings_history(astronaut_id=101, hours=None)
        assert len(history_all) == 2


# =============================================================================
# 3. CALIBRATION METADATA PERSISTENCE
# =============================================================================
class TestCalibrationMetadataPersistence:

    def test_save_and_retrieve_calibration_records(self, db_session):
        repo = PsiRepository(db_session)
        mock_records = [
            {"photo_number": 1, "pose_name": "neutral", "valid": True, "dominant_emotion": "neutral", "emotions": {"neutral": 90}, "calculated_stress": 8.0},
            {"photo_number": 2, "pose_name": "left", "valid": True, "dominant_emotion": "neutral", "emotions": {"neutral": 85}, "calculated_stress": 9.5},
            {"photo_number": 3, "pose_name": "right", "valid": True, "dominant_emotion": "neutral", "emotions": {"neutral": 88}, "calculated_stress": 8.5},
            {"photo_number": 4, "pose_name": "smile", "valid": True, "dominant_emotion": "happy", "emotions": {"happy": 80}, "calculated_stress": 2.1},
            {"photo_number": 5, "pose_name": "neutral_final", "valid": True, "dominant_emotion": "neutral", "emotions": {"neutral": 87}, "calculated_stress": 8.2},
        ]

        saved = repo.save_calibration_records(astronaut_id=101, records=mock_records)
        assert len(saved) == 5

        retrieved = repo.get_calibration_records(astronaut_id=101)
        assert len(retrieved) == 5
        assert [r.pose_name for r in retrieved] == ["neutral", "left", "right", "smile", "neutral_final"]
        assert all(r.is_valid for r in retrieved)


# =============================================================================
# 4. ASTRONAUT ISOLATION & PRIVACY
# =============================================================================
class TestAstronautIsolation:

    def test_strict_isolation_between_astronauts(self, db_session):
        repo = PsiRepository(db_session)

        # Setup Astronaut 1
        repo.update_baseline(astronaut_id=1, baseline_stress=20.0, baseline_sigma=4.0, optimal_range_low=16.8, optimal_range_high=26.0)
        repo.save_reading(astronaut_id=1, raw_stress=18.0, smoothed_stress=18.0, dominant_emotion="happy", emotion_vector={"happy": 80})

        # Setup Astronaut 2
        repo.update_baseline(astronaut_id=2, baseline_stress=45.0, baseline_sigma=7.0, optimal_range_low=39.4, optimal_range_high=55.5)
        repo.save_reading(astronaut_id=2, raw_stress=60.0, smoothed_stress=60.0, dominant_emotion="angry", emotion_vector={"angry": 70})

        # Verify Astronaut 1 sees only their data
        base_1 = repo.get_baseline(astronaut_id=1)
        readings_1 = repo.get_readings_history(astronaut_id=1)
        assert base_1.baseline_stress == 20.0
        assert len(readings_1) == 1
        assert readings_1[0].raw_stress == 18.0

        # Verify Astronaut 2 sees only their data
        base_2 = repo.get_baseline(astronaut_id=2)
        readings_2 = repo.get_readings_history(astronaut_id=2)
        assert base_2.baseline_stress == 45.0
        assert len(readings_2) == 1
        assert readings_2[0].raw_stress == 60.0

        # Deleting Astronaut 1 data leaves Astronaut 2 completely unaffected
        repo.delete_astronaut_data(astronaut_id=1)
        assert repo.get_baseline(astronaut_id=1) is None
        assert len(repo.get_readings_history(astronaut_id=1)) == 0
        assert repo.get_baseline(astronaut_id=2) is not None
        assert len(repo.get_readings_history(astronaut_id=2)) == 1


# =============================================================================
# 5. DATABASE RELATIONSHIPS & CASCADES
# =============================================================================
class TestDatabaseRelationships:

    def test_orm_relationships_and_cascade_delete(self, db_session):
        repo = PsiRepository(db_session)

        # Create baseline with readings and calibration metadata
        base = repo.update_baseline(astronaut_id=101, baseline_stress=25.0, baseline_sigma=5.0, optimal_range_low=21.0, optimal_range_high=32.5)
        repo.save_reading(astronaut_id=101, raw_stress=22.0, smoothed_stress=22.0, dominant_emotion="neutral", emotion_vector={"neutral": 100})
        repo.save_calibration_records(astronaut_id=101, records=[
            {"photo_number": 1, "pose_name": "neutral", "valid": True, "emotions": {"neutral": 100}, "calculated_stress": 5.0}
        ])

        # Test bidirectional ORM relationship access
        db_session.refresh(base)
        assert len(base.readings) == 1
        assert base.readings[0].raw_stress == 22.0
        assert base.readings[0].baseline.id == base.id

        assert len(base.calibration_records) == 1
        assert base.calibration_records[0].pose_name == "neutral"
        assert base.calibration_records[0].baseline.id == base.id

        # Delete baseline through session and verify cascade behavior
        db_session.delete(base)
        db_session.commit()

        # Calibration metadata deleted via cascade
        cal_count = db_session.scalar(select(PsiCalibrationMetadata).where(PsiCalibrationMetadata.astronaut_id == 101))
        assert cal_count is None

        # Reading persists with baseline_id set to NULL to preserve mission telemetry history
        reading = db_session.scalar(select(PsiStressReading).where(PsiStressReading.astronaut_id == 101))
        assert reading is not None
        assert reading.baseline_id is None


# =============================================================================
# 6. INVALID DATA & ERROR HANDLING
# =============================================================================
class TestInvalidDataHandling:

    def test_direct_reading_validation_failures(self, db_session):
        service = PsiService(db_session)

        # Negative stress
        with pytest.raises(ValueError, match="Invalid raw_stress"):
            service.record_direct_reading(astronaut_id=101, raw_stress=-5.0, smoothed_stress=10.0, dominant_emotion="neutral", emotion_vector={"neutral": 100})

        # Stress > 100
        with pytest.raises(ValueError, match="Invalid raw_stress"):
            service.record_direct_reading(astronaut_id=101, raw_stress=105.0, smoothed_stress=10.0, dominant_emotion="neutral", emotion_vector={"neutral": 100})

        # NaN stress
        with pytest.raises(ValueError, match="Invalid raw_stress"):
            service.record_direct_reading(astronaut_id=101, raw_stress=float("nan"), smoothed_stress=10.0, dominant_emotion="neutral", emotion_vector={"neutral": 100})

        # Empty emotion vector
        with pytest.raises(ValueError, match="emotion_vector"):
            service.record_direct_reading(astronaut_id=101, raw_stress=20.0, smoothed_stress=20.0, dominant_emotion="neutral", emotion_vector={})

    def test_calibrate_astronaut_invalid_inputs(self, db_session):
        service = PsiService(db_session)
        with pytest.raises(ValueError, match="list"):
            service.calibrate_astronaut(astronaut_id=101, calibration_results="not_a_list")

    def test_nonexistent_astronaut_status_returns_grey(self, db_session):
        service = PsiService(db_session)
        status = service.get_astronaut_status(astronaut_id=99999)
        assert status["status"] == "grey"
        assert status["measurements"] == []


# =============================================================================
# 7. SERVICE HIGH-LEVEL ANALYTICS WORKFLOWS
# =============================================================================
class TestServiceAnalyticsWorkflows:

    def test_service_calibrate_and_get_status(self, db_session):
        service = PsiService(db_session)
        mock_analyses = [
            {"photo_number": 1, "pose_name": "neutral", "valid": True, "emotions": {"neutral": 80, "happy": 10, "sad": 4, "angry": 2, "fear": 2, "disgust": 1, "surprise": 1}},
            {"photo_number": 2, "pose_name": "left", "valid": True, "emotions": {"neutral": 75, "happy": 12, "sad": 5, "angry": 3, "fear": 2, "disgust": 2, "surprise": 1}},
            {"photo_number": 3, "pose_name": "right", "valid": True, "emotions": {"neutral": 82, "happy": 8, "sad": 4, "angry": 2, "fear": 2, "disgust": 1, "surprise": 1}},
            {"photo_number": 4, "pose_name": "smile", "valid": True, "emotions": {"happy": 70, "neutral": 20, "sad": 3, "angry": 2, "fear": 2, "disgust": 1, "surprise": 2}},
            {"photo_number": 5, "pose_name": "neutral_final", "valid": True, "emotions": {"neutral": 78, "happy": 10, "sad": 4, "angry": 3, "fear": 2, "disgust": 2, "surprise": 1}},
        ]

        baseline = service.calibrate_astronaut(astronaut_id=101, calibration_results=mock_analyses)
        assert baseline["baseline_stress"] > 0
        assert baseline["baseline_sigma"] >= 2.0

        # Record nominal reading within optimal range
        service.record_direct_reading(astronaut_id=101, raw_stress=4.0, smoothed_stress=4.5, dominant_emotion="happy", emotion_vector={"happy": 80, "neutral": 20})
        status_nom = service.get_astronaut_status(astronaut_id=101)
        assert status_nom["status"] == "green"
        assert status_nom["status_label"] == "nominal"

        # Record elevated reading above optimal range high
        service.record_direct_reading(astronaut_id=101, raw_stress=25.0, smoothed_stress=22.0, dominant_emotion="angry", emotion_vector={"angry": 40, "neutral": 60})
        status_elev = service.get_astronaut_status(astronaut_id=101)
        assert status_elev["status"] == "yellow"
        assert status_elev["status_label"] == "elevated"

        # Record high stress reading above threshold (70.0)
        service.record_direct_reading(astronaut_id=101, raw_stress=85.0, smoothed_stress=78.0, dominant_emotion="fear", emotion_vector={"fear": 80, "neutral": 20})
        status_high = service.get_astronaut_status(astronaut_id=101)
        assert status_high["status"] == "red"
        assert status_high["status_label"] == "high_stress"

    def test_burnout_and_chronic_stress_detection(self, db_session):
        service = PsiService(db_session)
        now = datetime.now(timezone.utc)

        # Calibrate baseline = 25.0 (chronic threshold = 40.0)
        service.repo.update_baseline(astronaut_id=101, baseline_stress=25.0, baseline_sigma=5.0, optimal_range_low=21.0, optimal_range_high=32.5)

        # Simulate 7 days of high stress (> 40.0)
        for day in range(7):
            t = now - timedelta(days=6 - day)
            service.repo.save_reading(
                astronaut_id=101, raw_stress=55.0, smoothed_stress=52.0,
                dominant_emotion="angry", emotion_vector={"angry": 60, "neutral": 40},
                task_complexity=8.0, timestamp=t
            )

        # Verify Burnout Risk Score
        burnout = service.get_burnout_analytics(astronaut_id=101)
        assert burnout["reading_count"] == 7
        assert burnout["weekly_avg"] == 52.0
        assert burnout["brs"] >= 40.0

        # Verify Chronic Stress
        chronic = service.get_chronic_stress_analytics(astronaut_id=101)
        assert chronic["is_chronic"] is True
        assert chronic["threshold"] == 40.0
