from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean, Text, JSON, UniqueConstraint, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def utcnow():
    return datetime.now(timezone.utc)

class MissionEnvironment(Base):
    __tablename__ = "mission_environments"
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    env_type: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    duration_days: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    streams: Mapped[list] = mapped_column(JSON, default=list)

class BodySystem(Base):
    __tablename__ = "body_systems"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    main_function: Mapped[str] = mapped_column(Text)
    indicators: Mapped[list] = mapped_column(JSON, default=list)
    suggested_actions: Mapped[list] = mapped_column(JSON, default=list)

class HealthRoutine(Base):
    __tablename__ = "health_routines"
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    astronaut_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(160))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reminder_minutes: Mapped[int] = mapped_column(Integer, default=10)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

class RoutineCompletion(Base):
    __tablename__ = "routine_completions"
    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(Integer, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class HealthChallenge(Base):
    __tablename__ = "health_challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer, default=10)
    kind: Mapped[str] = mapped_column(String(32), default="daily")

class AstronautAchievement(Base):
    __tablename__ = "astronaut_achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(Integer, index=True)
    challenge_id: Mapped[int] = mapped_column(Integer)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("astronaut_id", "challenge_id", name="uq_astronaut_challenge"),)

class HealthEducation(Base):
    __tablename__ = "health_education"
    id: Mapped[int] = mapped_column(primary_key=True)
    metric_key: Mapped[str] = mapped_column(String(60), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)
    how: Mapped[str] = mapped_column(Text)
    influences: Mapped[str] = mapped_column(Text)
    limitations: Mapped[str] = mapped_column(Text)
    understand: Mapped[str] = mapped_column(Text)
    when_advice: Mapped[str] = mapped_column(Text)

class AstronautPsiBaseline(Base):
    __tablename__ = "astronaut_psi_baselines"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    is_calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_stress: Mapped[float] = mapped_column(Float, default=25.0)
    baseline_sigma: Mapped[float] = mapped_column(Float, default=5.0)
    optimal_range_low: Mapped[float] = mapped_column(Float, default=15.0)
    optimal_range_high: Mapped[float] = mapped_column(Float, default=35.0)
    natural_angry: Mapped[float] = mapped_column(Float, default=0.0)
    natural_sad: Mapped[float] = mapped_column(Float, default=0.0)
    natural_fear: Mapped[float] = mapped_column(Float, default=0.0)
    stress_threshold: Mapped[float] = mapped_column(Float, default=70.0)
    calibrated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    readings: Mapped[list["PsiStressReading"]] = relationship(back_populates="baseline")
    calibration_records: Mapped[list["PsiCalibrationMetadata"]] = relationship(back_populates="baseline", cascade="all, delete-orphan")

class PsiStressReading(Base):
    __tablename__ = "psi_stress_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_id: Mapped[int | None] = mapped_column(ForeignKey("astronaut_psi_baselines.id", ondelete="SET NULL"), index=True, nullable=True)
    astronaut_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    mission_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    raw_stress: Mapped[float] = mapped_column(Float, nullable=False)
    smoothed_stress: Mapped[float] = mapped_column(Float, nullable=False)
    stress_deviation: Mapped[float] = mapped_column(Float, default=0.0)
    stress_trend: Mapped[str] = mapped_column(String(20), default="stable")
    dominant_emotion: Mapped[str] = mapped_column(String(20), nullable=False)
    emotion_vector: Mapped[dict] = mapped_column(JSON, default=dict)
    motion_level: Mapped[float] = mapped_column(Float, default=0.0)
    motion_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    mission_phase: Mapped[str] = mapped_column(String(60), default="nominal_operations")
    task_complexity: Mapped[float] = mapped_column(Float, default=5.0)
    environmental_factor: Mapped[float] = mapped_column(Float, default=1.0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    baseline: Mapped["AstronautPsiBaseline | None"] = relationship(back_populates="readings")

class PsiCalibrationMetadata(Base):
    __tablename__ = "psi_calibration_metadata"
    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey("astronaut_psi_baselines.id", ondelete="CASCADE"), index=True, nullable=False)
    astronaut_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    pose_name: Mapped[str] = mapped_column(String(32))
    photo_number: Mapped[int] = mapped_column(Integer)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    dominant_emotion: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emotions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    calculated_stress: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    baseline: Mapped["AstronautPsiBaseline"] = relationship(back_populates="calibration_records")

class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")  # planned, active, completed, contingency
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    astronauts: Mapped[list["Astronaut"]] = relationship(back_populates="current_mission")

class Astronaut(Base):
    __tablename__ = "astronauts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    callsign: Mapped[str | None] = mapped_column(String(60), nullable=True)
    role: Mapped[str] = mapped_column(String(60), default="Mission Specialist")  # Commander, Flight Engineer, Medical Officer, Specialist
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, training, resting, grounded
    current_mission_id: Mapped[int | None] = mapped_column(ForeignKey("missions.id", ondelete="SET NULL"), nullable=True, index=True)
    biometric_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    current_mission: Mapped["Mission | None"] = relationship(back_populates="astronauts")
    physiological_readings: Mapped[list["PhysiologicalReading"]] = relationship(back_populates="astronaut", cascade="all, delete-orphan")

class PhysiologicalReading(Base):
    __tablename__ = "physiological_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("astronauts.id", ondelete="CASCADE"), index=True, nullable=False)
    mission_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # bpm
    spo2: Mapped[float | None] = mapped_column(Float, nullable=True)  # percentage (e.g. 98.5)
    body_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)  # celsius (e.g. 36.8)
    respiration_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # breaths/min (e.g. 14.0)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)  # hours (e.g. 7.5)
    sleep_quality: Mapped[float | None] = mapped_column(Float, nullable=True)  # score 0-100
    activity_level: Mapped[float | None] = mapped_column(Float, nullable=True)  # physical exertion scale 0-10
    workload_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # operational demand 1-10
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)  # true if simulated, false if real hardware sensor
    source_device: Mapped[str | None] = mapped_column(String(80), nullable=True)  # e.g. BioHarness v4, CrewWatch
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    astronaut: Mapped["Astronaut"] = relationship(back_populates="physiological_readings")


