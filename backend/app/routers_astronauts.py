"""
ASTRA MIND — Astronaut Management APIs
=======================================
CRUD endpoints for astronaut profiles and operational status.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    Astronaut, Mission, AstronautPsiBaseline,
    PsiStressReading, PhysiologicalReading, PsiCalibrationMetadata
)
from .schemas_phase3 import AstronautCreate, AstronautUpdate, AstronautResponse
from .security import authenticate_user, require_role, enforce_astronaut_isolation

router = APIRouter(prefix="/astronauts", tags=["Astronauts"])


def astronaut_to_dict(a: Astronaut, baseline: Optional[AstronautPsiBaseline] = None) -> dict:
    is_calibrated = bool(baseline.is_calibrated) if baseline else False
    baseline_stress = float(baseline.baseline_stress) if (baseline and baseline.is_calibrated) else None
    return {
        "id": a.id,
        "name": a.name,
        "callsign": a.callsign,
        "role": a.role,
        "status": a.status,
        "current_mission_id": a.current_mission_id,
        "biometric_profile": a.biometric_profile or {},
        "is_calibrated": is_calibrated,
        "baseline_stress": baseline_stress,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


@router.get("", response_model=List[AstronautResponse])
def list_astronauts(
    mission_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    include_archived: bool = True,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """List all registered astronauts with optional mission/status filtering and baseline indicators."""
    stmt = select(Astronaut).order_by(Astronaut.id)
    if mission_id is not None:
        stmt = stmt.where(Astronaut.current_mission_id == mission_id)
    if status_filter:
        stmt = stmt.where(Astronaut.status == status_filter)
    elif not include_archived:
        stmt = stmt.where(Astronaut.status != "archived")

    rows = db.scalars(stmt).all()

    # Bulk load baselines for calibration indicators
    astro_ids = [a.id for a in rows]
    baselines_map = {}
    if astro_ids:
        b_stmt = select(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id.in_(astro_ids))
        for b in db.scalars(b_stmt).all():
            baselines_map[b.astronaut_id] = b

    return [astronaut_to_dict(a, baselines_map.get(a.id)) for a in rows]


@router.post("", response_model=AstronautResponse, status_code=status.HTTP_201_CREATED)
def create_astronaut(
    payload: AstronautCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """Register a new astronaut into the mission system."""
    if payload.current_mission_id is not None:
        mission = db.get(Mission, payload.current_mission_id)
        if not mission:
            raise HTTPException(status_code=404, detail="Assigned mission not found")

    astronaut = Astronaut(
        name=payload.name.strip(),
        callsign=payload.callsign.strip() if payload.callsign else None,
        role=payload.role.strip() if payload.role else "Mission Specialist",
        status=payload.status,
        current_mission_id=payload.current_mission_id,
        biometric_profile=payload.biometric_profile,
    )
    db.add(astronaut)
    db.commit()
    db.refresh(astronaut)

    # Automatically create an uncalibrated baseline entry for the astronaut
    baseline = AstronautPsiBaseline(
        astronaut_id=astronaut.id,
        is_calibrated=False,
        baseline_stress=25.0,
        baseline_sigma=5.0,
        optimal_range_low=15.0,
        optimal_range_high=35.0,
        stress_threshold=70.0
    )
    db.add(baseline)
    db.commit()

    return astronaut_to_dict(astronaut, baseline)


@router.get("/{astronaut_id}", response_model=AstronautResponse)
def get_astronaut(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """Retrieve full profile details for a specific astronaut."""
    enforce_astronaut_isolation(astronaut_id, user)
    astronaut = db.get(Astronaut, astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found")

    baseline = db.scalar(select(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id == astronaut_id))
    return astronaut_to_dict(astronaut, baseline)


@router.put("/{astronaut_id}", response_model=AstronautResponse)
def update_astronaut(
    astronaut_id: int,
    payload: AstronautUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """Update astronaut metadata or mission status while preserving clinical history."""
    astronaut = db.get(Astronaut, astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found")

    if payload.current_mission_id is not None:
        if payload.current_mission_id > 0:
            mission = db.get(Mission, payload.current_mission_id)
            if not mission:
                raise HTTPException(status_code=404, detail="Assigned mission not found")
            astronaut.current_mission_id = payload.current_mission_id
        else:
            # Unassign mission
            astronaut.current_mission_id = None

    if payload.name is not None:
        astronaut.name = payload.name.strip()
    if payload.callsign is not None:
        astronaut.callsign = payload.callsign.strip() if payload.callsign else None
    if payload.role is not None:
        astronaut.role = payload.role.strip()
    if payload.status is not None:
        astronaut.status = payload.status
    if payload.biometric_profile is not None:
        astronaut.biometric_profile = payload.biometric_profile

    db.commit()
    db.refresh(astronaut)

    baseline = db.scalar(select(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id == astronaut_id))
    return astronaut_to_dict(astronaut, baseline)


@router.delete("/{astronaut_id}")
def delete_astronaut(
    astronaut_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """
    Safely delete or archive an astronaut profile.
    If historical PSI readings, baseline calibration, or physiological telemetry
    exist and force is False, the profile is archived rather than permanently deleted,
    preserving medical and flight telemetry integrity.
    """
    astronaut = db.get(Astronaut, astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found")

    # Check for historical telemetry/records
    psi_count = db.scalar(select(func.count(PsiStressReading.id)).where(PsiStressReading.astronaut_id == astronaut_id)) or 0
    physio_count = db.scalar(select(func.count(PhysiologicalReading.id)).where(PhysiologicalReading.astronaut_id == astronaut_id)) or 0
    calib_count = db.scalar(select(func.count(PsiCalibrationMetadata.id)).where(PsiCalibrationMetadata.astronaut_id == astronaut_id)) or 0
    baseline = db.scalar(select(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id == astronaut_id))
    has_history = (psi_count > 0) or (physio_count > 0) or (calib_count > 0) or bool(baseline and baseline.is_calibrated)

    if has_history and not force:
        astronaut.status = "archived"
        db.commit()
        return {
            "success": True,
            "action": "archived",
            "message": f"Astronaut {astronaut.name} (#{astronaut_id}) has historical health telemetry ({psi_count} PSI readings, {physio_count} vitals). Profile has been safely archived to preserve clinical history.",
            "astronaut_id": astronaut_id,
            "has_history": True,
        }

    # If no history or force=True: clean deletion
    if baseline:
        db.delete(baseline)
    # Remove metadata if force
    if force:
        db.execute(select(PsiCalibrationMetadata).where(PsiCalibrationMetadata.astronaut_id == astronaut_id))
    db.delete(astronaut)
    db.commit()
    return {
        "success": True,
        "action": "deleted",
        "message": f"Astronaut {astronaut.name} (#{astronaut_id}) has been removed.",
        "astronaut_id": astronaut_id,
        "has_history": False,
    }


@router.post("/{astronaut_id}/archive", response_model=AstronautResponse)
def archive_astronaut(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """Explicitly archive/deactivate an astronaut profile."""
    astronaut = db.get(Astronaut, astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found")
    astronaut.status = "archived"
    db.commit()
    db.refresh(astronaut)
    baseline = db.scalar(select(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id == astronaut_id))
    return astronaut_to_dict(astronaut, baseline)


@router.post("/{astronaut_id}/restore", response_model=AstronautResponse)
def restore_astronaut(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """Restore an archived astronaut to active status."""
    astronaut = db.get(Astronaut, astronaut_id)
    if not astronaut:
        raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found")
    astronaut.status = "active"
    db.commit()
    db.refresh(astronaut)
    baseline = db.scalar(select(AstronautPsiBaseline).where(AstronautPsiBaseline.astronaut_id == astronaut_id))
    return astronaut_to_dict(astronaut, baseline)
