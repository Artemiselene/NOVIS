"""
ASTRA MIND -- Mission Management & Monitoring APIs
=================================================
Endpoints for creating missions, assigning crew, tracking mission status,
and summarizing crew behavioral & physiological readiness.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .db import get_db
from .models import Mission, Astronaut, MissionEnvironment
from .schemas_phase3 import (
    MissionCreate, MissionUpdate, MissionResponse, AssignAstronautRequest
)
from .security import authenticate_user, require_role
from .psi.service import PsiService

router = APIRouter(prefix="/missions", tags=["Missions"])


def mission_to_dict(m: Mission) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "code": m.code,
        "status": m.status,
        "description": m.description,
        "start_date": m.start_date,
        "end_date": m.end_date,
        "crew_count": len(m.astronauts) if m.astronauts else 0,
        "created_at": m.created_at,
    }


@router.get("", response_model=List[MissionResponse])
def list_missions(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """List missions with optional status filter."""
    stmt = select(Mission).order_by(Mission.id)
    if status_filter:
        stmt = stmt.where(Mission.status == status_filter)
    rows = db.scalars(stmt).all()
    return [mission_to_dict(m) for m in rows]


@router.post("", response_model=MissionResponse, status_code=status.HTTP_201_CREATED)
def create_mission(
    payload: MissionCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """Create a new mission definition."""
    existing = db.scalar(select(Mission).where(Mission.code == payload.code))
    if existing:
        raise HTTPException(status_code=400, detail=f"Mission with code '{payload.code}' already exists")

    mission = Mission(
        name=payload.name,
        code=payload.code,
        status=payload.status,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission_to_dict(mission)


@router.get("/{mission_id}", response_model=MissionResponse)
def get_mission(
    mission_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Get mission details by ID."""
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    return mission_to_dict(mission)


@router.put("/{mission_id}", response_model=MissionResponse)
def update_mission(
    mission_id: int,
    payload: MissionUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """Update mission operational status or dates."""
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")

    if payload.code is not None and payload.code != mission.code:
        duplicate = db.scalar(select(Mission).where(Mission.code == payload.code))
        if duplicate:
            raise HTTPException(status_code=400, detail=f"Mission code '{payload.code}' already in use")
        mission.code = payload.code

    if payload.name is not None:
        mission.name = payload.name
    if payload.status is not None:
        mission.status = payload.status
    if payload.description is not None:
        mission.description = payload.description
    if payload.start_date is not None:
        mission.start_date = payload.start_date
    if payload.end_date is not None:
        mission.end_date = payload.end_date

    db.commit()
    db.refresh(mission)
    return mission_to_dict(mission)


@router.post("/{mission_id}/assign")
def assign_astronaut_to_mission(
    mission_id: int,
    payload: AssignAstronautRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """Assign an astronaut to a mission."""
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")

    astronaut = db.get(Astronaut, payload.astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {payload.astronaut_id} not found")

    astronaut.current_mission_id = mission_id
    db.commit()
    return {
        "success": True,
        "message": f"Astronaut {astronaut.name} ({astronaut.id}) assigned to mission {mission.name} ({mission_id}).",
        "mission_id": mission_id,
        "astronaut_id": astronaut.id,
    }


@router.get("/{mission_id}/summary")
def get_mission_monitoring_summary(
    mission_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """
    Retrieve mission behavioral & physiological monitoring summaries for all assigned crew.
    """
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")

    crew = db.scalars(select(Astronaut).where(Astronaut.current_mission_id == mission_id)).all()
    psi_service = PsiService(db)

    crew_summaries = []
    for a in crew:
        status_info = psi_service.get_astronaut_status(a.id)
        burnout = psi_service.get_burnout_analytics(a.id)
        crew_summaries.append({
            "astronaut_id": a.id,
            "name": a.name,
            "callsign": a.callsign,
            "role": a.role,
            "status": a.status,
            "psi_status": status_info["status"],
            "smoothed_stress": status_info.get("latest_reading", {}).get("smoothed_stress") if status_info.get("latest_reading") else None,
            "brs": burnout["brs"],
            "burnout_classification": burnout["classification"],
        })

    env = db.scalar(select(MissionEnvironment).where(MissionEnvironment.mission_id == mission_id))

    return {
        "mission_id": mission.id,
        "name": mission.name,
        "code": mission.code,
        "status": mission.status,
        "environment": {
            "type": env.env_type if env else "unknown",
            "location": env.location if env else "simulated",
            "duration_days": env.duration_days if env else 0,
        } if env else None,
        "crew_count": len(crew),
        "crew": crew_summaries,
    }
