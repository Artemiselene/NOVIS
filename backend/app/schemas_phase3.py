"""
ASTRA MIND — Phase 3 Pydantic Schemas
====================================
Data validation schemas for Astronauts, Missions, Physiological Telemetry,
PSI Monitoring, and Health Intelligence Dashboards.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# ASTRONAUT SCHEMAS
# =============================================================================
class AstronautCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    callsign: Optional[str] = Field(None, max_length=60)
    role: str = Field("Mission Specialist", max_length=60)
    status: str = Field("active", pattern="^(active|training|resting|grounded|archived|inactive)$")
    current_mission_id: Optional[int] = None
    biometric_profile: Dict[str, Any] = Field(default_factory=dict)


class AstronautUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    callsign: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|training|resting|grounded|archived|inactive)$")
    current_mission_id: Optional[int] = None
    biometric_profile: Optional[Dict[str, Any]] = None


class AstronautResponse(BaseModel):
    id: int
    name: str
    callsign: Optional[str] = None
    role: str
    status: str
    current_mission_id: Optional[int] = None
    biometric_profile: Dict[str, Any] = {}
    is_calibrated: bool = False
    baseline_stress: Optional[float] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# MISSION SCHEMAS
# =============================================================================
class MissionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    code: str = Field(..., min_length=2, max_length=32)
    status: str = Field("active", pattern="^(planned|active|completed|contingency)$")
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class MissionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(planned|active|completed|contingency)$")
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AssignAstronautRequest(BaseModel):
    astronaut_id: int


class MissionResponse(BaseModel):
    id: int
    name: str
    code: str
    status: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    crew_count: int = 0
    created_at: datetime


# =============================================================================
# PHYSIOLOGICAL TELEMETRY SCHEMAS
# =============================================================================
class PhysiologicalCreate(BaseModel):
    astronaut_id: int
    mission_id: Optional[int] = None
    heart_rate: Optional[float] = Field(None, ge=30.0, le=240.0)
    spo2: Optional[float] = Field(None, ge=50.0, le=100.0)
    body_temperature: Optional[float] = Field(None, ge=30.0, le=45.0)
    respiration_rate: Optional[float] = Field(None, ge=4.0, le=60.0)
    sleep_hours: Optional[float] = Field(None, ge=0.0, le=24.0)
    sleep_quality: Optional[float] = Field(None, ge=0.0, le=100.0)
    activity_level: Optional[float] = Field(None, ge=0.0, le=10.0)
    workload_score: Optional[float] = Field(None, ge=1.0, le=10.0)
    is_simulated: bool = True
    source_device: Optional[str] = None


class PhysiologicalResponse(BaseModel):
    id: int
    astronaut_id: int
    mission_id: Optional[int] = None
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    body_temperature: Optional[float] = None
    respiration_rate: Optional[float] = None
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[float] = None
    activity_level: Optional[float] = None
    workload_score: Optional[float] = None
    is_simulated: bool
    source_device: Optional[str] = None
    created_at: datetime


# =============================================================================
# PSI MONITORING & CALIBRATION SCHEMAS
# =============================================================================
class CalibrationPoseResult(BaseModel):
    photo_number: int
    pose_name: str
    valid: bool = True
    emotions: Dict[str, float]


class CalibrationFrameRequest(BaseModel):
    frame_base64: str
    pose_name: Optional[str] = "neutral"
    photo_number: Optional[int] = 1


class CalibrationSubmitRequest(BaseModel):
    poses: List[CalibrationPoseResult]


class CalibrationResponse(BaseModel):
    success: bool
    baseline_stress: float
    baseline_sigma: float
    optimal_range: List[float]
    natural_emotions: Dict[str, float] = {}
    valid_photos: int


class PsiDirectReadingCreate(BaseModel):
    raw_stress: float = Field(..., ge=0.0, le=100.0)
    smoothed_stress: float = Field(..., ge=0.0, le=100.0)
    dominant_emotion: str
    emotion_vector: Dict[str, float]
    motion_level: float = Field(0.0, ge=0.0, le=10.0)
    task_complexity: float = Field(5.0, ge=1.0, le=10.0)
    mission_id: Optional[int] = None


class PsiFrameRequest(BaseModel):
    frame_base64: str
    mission_id: Optional[int] = None
    task_complexity: float = Field(5.0, ge=1.0, le=10.0)


class PsiReadingResponse(BaseModel):
    id: int
    astronaut_id: int
    raw_stress: float
    smoothed_stress: float
    stress_deviation: float
    dominant_emotion: str
    risk_level: str
    created_at: Optional[str] = None


class PsiBaselineResponse(BaseModel):
    astronaut_id: int
    is_calibrated: bool
    baseline_stress: float
    baseline_sigma: float
    optimal_range: List[float]
    stress_threshold: float
    calibrated_at: Optional[str] = None


class BurnoutResponse(BaseModel):
    astronaut_id: int
    brs: float
    classification: str
    weekly_avg: float
    variability: float
    task_load: float = 0.0
    reading_count: int


class ChronicResponse(BaseModel):
    astronaut_id: int
    is_chronic: bool
    baseline: float
    threshold: float
    daily_averages: List[Dict[str, Any]]
    message: str


# =============================================================================
# DASHBOARD SCHEMAS
# =============================================================================
class DashboardOverview(BaseModel):
    astronaut: Dict[str, Any]
    mission: Optional[Dict[str, Any]] = None
    psi_status: Dict[str, Any]
    physiological: Dict[str, Any]
    recovery: Dict[str, Any]
    alerts: List[Dict[str, Any]]
