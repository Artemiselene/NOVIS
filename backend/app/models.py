from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
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
