from datetime import datetime
from pydantic import BaseModel, Field

class EnvironmentCreate(BaseModel):
    mission_id: int
    env_type: str = Field(pattern="^(spacecraft|station|rover|base)$")
    name: str
    duration_days: int = 0
    location: str | None = None
    context: dict = {}
    streams: list[str] = []

class RoutineCreate(BaseModel):
    mission_id: int | None = None
    astronaut_id: int | None = None
    kind: str
    title: str
    scheduled_at: datetime | None = None
    reminder_minutes: int = 10

class CompleteRoutine(BaseModel):
    notes: str | None = None

class BodyStatus(BaseModel):
    system: str
    name: str
    main_function: str
    indicators: list[str]
    measurements: list[dict]
    baseline_comparison: dict | None
    trend: list[dict]
    status: str
    explanation: str
    suggested_actions: list[str]
