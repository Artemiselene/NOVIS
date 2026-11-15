"""
ASTRA MIND — Physiological Telemetry APIs
=========================================
Endpoints for ingesting, validating, and retrieving physiological measurements:
- Heart rate (bpm)
- Blood oxygen saturation (SpO2 %)
- Core body temperature (°C)
- Respiration rate (brpm)
- Sleep duration & quality
- Activity level (physical exertion)
- Workload demand (operational)

STRICT SENSOR INTEGRITY RULES:
- Never fabricate missing sensor readings (fields are nullable).
- Store real and simulated measurements distinctly (is_simulated flag).
- Keep physical exertion strictly separate from psychological stress.
"""

from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from .db import get_db
from .models import PhysiologicalReading, Astronaut
from .schemas_phase3 import PhysiologicalCreate, PhysiologicalResponse
from .security import authenticate_user, enforce_astronaut_isolation
from .websocket_manager import ws_manager

router = APIRouter(prefix="/telemetry", tags=["Physiological Telemetry"])


def reading_to_dict(r: PhysiologicalReading) -> dict:
    return {
        "id": r.id,
        "astronaut_id": r.astronaut_id,
        "mission_id": r.mission_id,
        "heart_rate": r.heart_rate,
        "spo2": r.spo2,
        "body_temperature": r.body_temperature,
        "respiration_rate": r.respiration_rate,
        "sleep_hours": r.sleep_hours,
        "sleep_quality": r.sleep_quality,
        "activity_level": r.activity_level,
        "workload_score": r.workload_score,
        "is_simulated": r.is_simulated,
        "source_device": r.source_device,
        "created_at": r.created_at,
    }


@router.post("", response_model=PhysiologicalResponse, status_code=status.HTTP_201_CREATED)
async def submit_physiological_telemetry(
    payload: PhysiologicalCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """
    Ingest physiological measurements from wearable or simulated telemetry stream.
    Rejects fabricated data; non-connected sensors are recorded as None.
    """
    enforce_astronaut_isolation(payload.astronaut_id, user)

    astronaut = db.get(Astronaut, payload.astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {payload.astronaut_id} not found")

    reading = PhysiologicalReading(
        astronaut_id=payload.astronaut_id,
        mission_id=payload.mission_id or astronaut.current_mission_id,
        heart_rate=payload.heart_rate,
        spo2=payload.spo2,
        body_temperature=payload.body_temperature,
        respiration_rate=payload.respiration_rate,
        sleep_hours=payload.sleep_hours,
        sleep_quality=payload.sleep_quality,
        activity_level=payload.activity_level,
        workload_score=payload.workload_score,
        is_simulated=payload.is_simulated,
        source_device=payload.source_device,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Real-time WebSocket broadcast to subscribed mission controllers
    result_dict = reading_to_dict(reading)
    await ws_manager.broadcast_to_astronaut(payload.astronaut_id, {
        "type": "physiological_telemetry",
        "data": {**result_dict, "created_at": reading.created_at.isoformat()},
    })
    if reading.mission_id:
        await ws_manager.broadcast_to_mission(reading.mission_id, {
            "type": "crew_physiological_telemetry",
            "astronaut_id": payload.astronaut_id,
            "data": {**result_dict, "created_at": reading.created_at.isoformat()},
        })

    return result_dict


@router.get("/astronaut/{astronaut_id}/latest", response_model=Optional[PhysiologicalResponse])
def get_latest_physiological_telemetry(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Retrieve the latest physiological measurement set for an astronaut."""
    enforce_astronaut_isolation(astronaut_id, user)
    stmt = (
        select(PhysiologicalReading)
        .where(PhysiologicalReading.astronaut_id == astronaut_id)
        .order_by(desc(PhysiologicalReading.created_at))
        .limit(1)
    )
    reading = db.scalar(stmt)
    if not reading:
        return None
    return reading_to_dict(reading)


@router.get("/astronaut/{astronaut_id}/history", response_model=List[PhysiologicalResponse])
def get_physiological_history(
    astronaut_id: int,
    hours: Optional[int] = 24,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Retrieve historical physiological telemetry logs for an astronaut."""
    enforce_astronaut_isolation(astronaut_id, user)
    stmt = select(PhysiologicalReading).where(PhysiologicalReading.astronaut_id == astronaut_id)
    if hours is not None and hours > 0:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = stmt.where(PhysiologicalReading.created_at >= since)
    stmt = stmt.order_by(desc(PhysiologicalReading.created_at)).limit(limit)
    rows = db.scalars(stmt).all()
    return [reading_to_dict(r) for r in rows]
