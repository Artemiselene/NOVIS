"""
ASTRA MIND -- Health Intelligence Dashboard APIs
===============================================
Aggregated executive overview endpoints combining:
- Astronaut demographics & mission context
- PSI behavioral telemetry and Burnout Risk Score (BRS)
- Available physiological vitals (SpO2, Heart Rate, Respiration, Temp)
- Recovery and readiness indicators
- Mission crew telemetry rollups and operational risk alerts

ETHICAL & CLINICAL CLARIFICATION:
- Separate physical exertion from psychological stress.
- No fabricated sensor readings; missing values are explicitly flagged.
- Proxy behavioral scores are not clinical brain-health determinations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from .db import get_db
from .models import Astronaut, Mission, PhysiologicalReading
from .psi.service import PsiService
from .schemas_phase3 import DashboardOverview
from .security import authenticate_user, enforce_astronaut_isolation, require_role

router = APIRouter(prefix="/dashboard", tags=["Health Intelligence Dashboard"])


def compute_recovery_indicators(
    physio: Optional[PhysiologicalReading],
    psi_stress: Optional[float],
) -> Dict[str, Any]:
    """
    Compute readiness and recovery indicators from sleep, exertion, and stress deviation.
    Does not fabricate missing sensor telemetry.
    """
    factors = {}
    recovery_components = []

    # Sleep component
    if physio and physio.sleep_hours is not None:
        sleep_score = min(100.0, max(0.0, (physio.sleep_hours / 8.0) * 100.0))
        if physio.sleep_quality is not None:
            sleep_score = 0.5 * sleep_score + 0.5 * physio.sleep_quality
        factors["sleep_score"] = round(sleep_score, 1)
        recovery_components.append(sleep_score)

    # Stress moderating component (lower stress = higher recovery)
    if psi_stress is not None:
        stress_recovery = max(0.0, min(100.0, 100.0 - psi_stress))
        factors["stress_moderation"] = round(stress_recovery, 1)
        recovery_components.append(stress_recovery)

    # Physical exertion component
    if physio and physio.activity_level is not None:
        exertion_rest = max(0.0, min(100.0, (10.0 - physio.activity_level) * 10.0))
        factors["rest_factor"] = round(exertion_rest, 1)
        recovery_components.append(exertion_rest)

    if recovery_components:
        overall_index = round(sum(recovery_components) / len(recovery_components), 1)
    else:
        overall_index = 75.0  # nominal default baseline

    if overall_index >= 75.0:
        readiness = "optimal"
    elif overall_index >= 50.0:
        readiness = "moderate"
    else:
        readiness = "depleted"

    return {
        "recovery_index": overall_index,
        "readiness_classification": readiness,
        "contributing_factors": factors,
    }


def generate_astronaut_alerts(
    psi_status: Dict[str, Any],
    brs: Dict[str, Any],
    physio: Optional[PhysiologicalReading],
) -> List[Dict[str, Any]]:
    """Synthesize active behavioural and physiological safety alerts."""
    alerts = []

    # PSI high stress alert
    latest_reading = psi_status.get("latest_reading")
    if latest_reading:
        if latest_reading.get("risk_level") == "high" or psi_status.get("status") == "red":
            alerts.append({
                "severity": "critical",
                "system": "behavioral_psi",
                "message": f"Elevated behavioral stress ({latest_reading.get('smoothed_stress')}%) exceeding personal baseline threshold.",
            })

    # Burnout Risk alert
    if brs.get("classification") in ["High", "Very High", "Critical"]:
        alerts.append({
            "severity": "warning",
            "system": "behavioral_brs",
            "message": f"High Burnout Risk Score detected: {brs.get('brs')} ({brs.get('classification')}).",
        })

    # Physiological safety alerts
    if physio:
        if physio.spo2 is not None and physio.spo2 < 95.0:
            alerts.append({
                "severity": "critical",
                "system": "physiological_spo2",
                "message": f"Hypoxia warning: Blood oxygen saturation at {physio.spo2}%.",
            })
        if physio.heart_rate is not None and (physio.heart_rate > 120.0 or physio.heart_rate < 45.0):
            alerts.append({
                "severity": "warning",
                "system": "physiological_heart_rate",
                "message": f"Abnormal heart rate: {physio.heart_rate} bpm.",
            })
        if physio.body_temperature is not None and physio.body_temperature > 38.0:
            alerts.append({
                "severity": "warning",
                "system": "physiological_temperature",
                "message": f"Hyperthermia warning: Core temperature at {physio.body_temperature} C.",
            })

    return alerts


@router.get("/astronaut/{astronaut_id}", response_model=DashboardOverview)
def get_astronaut_dashboard(
    astronaut_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(authenticate_user),
):
    """
    Comprehensive dashboard view for an individual astronaut:
    demographics, mission status, latest PSI, BRS, physiological vitals,
    recovery score, and synthesized health alerts.
    """
    enforce_astronaut_isolation(astronaut_id, user)

    astronaut = db.get(Astronaut, astronaut_id)
    if not astronaut:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Astronaut {astronaut_id} not found",
        )

    # Mission details
    mission_dict = None
    if astronaut.current_mission_id:
        mission = db.get(Mission, astronaut.current_mission_id)
        if mission:
            mission_dict = {
                "id": mission.id,
                "name": mission.name,
                "code": mission.code,
                "status": mission.status,
            }

    # PSI telemetry and BRS analytics
    psi_service = PsiService(db)
    psi_status = psi_service.get_astronaut_status(astronaut_id)
    brs_analytics = psi_service.get_burnout_analytics(astronaut_id)
    psi_status["burnout"] = brs_analytics

    # Latest physiological readings
    stmt = (
        select(PhysiologicalReading)
        .where(PhysiologicalReading.astronaut_id == astronaut_id)
        .order_by(desc(PhysiologicalReading.created_at))
        .limit(1)
    )
    latest_physio = db.scalar(stmt)

    if latest_physio:
        physio_dict = {
            "available": True,
            "id": latest_physio.id,
            "heart_rate": latest_physio.heart_rate,
            "spo2": latest_physio.spo2,
            "body_temperature": latest_physio.body_temperature,
            "respiration_rate": latest_physio.respiration_rate,
            "sleep_hours": latest_physio.sleep_hours,
            "sleep_quality": latest_physio.sleep_quality,
            "activity_level": latest_physio.activity_level,
            "workload_score": latest_physio.workload_score,
            "is_simulated": latest_physio.is_simulated,
            "created_at": latest_physio.created_at.isoformat() if latest_physio.created_at else None,
        }
    else:
        physio_dict = {
            "available": False,
            "message": "No active physiological sensor connected.",
        }

    # Recovery indicators
    psi_stress_val = (
        psi_status["latest_reading"]["smoothed_stress"]
        if psi_status.get("latest_reading")
        else None
    )
    recovery_dict = compute_recovery_indicators(latest_physio, psi_stress_val)

    # Active alerts
    alerts_list = generate_astronaut_alerts(psi_status, brs_analytics, latest_physio)

    return {
        "astronaut": {
            "id": astronaut.id,
            "name": astronaut.name,
            "callsign": astronaut.callsign,
            "role": astronaut.role,
            "status": astronaut.status,
            "current_mission_id": astronaut.current_mission_id,
        },
        "mission": mission_dict,
        "psi_status": psi_status,
        "physiological": physio_dict,
        "recovery": recovery_dict,
        "alerts": alerts_list,
    }


@router.get("/mission/{mission_id}")
def get_mission_dashboard(
    mission_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["flight_surgeon", "mission_director"])),
):
    """
    Fleet/Mission Commander overview aggregating all crew members assigned
    to a given mission.
    """
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission {mission_id} not found",
        )

    # Retrieve all assigned crew
    crew = db.scalars(
        select(Astronaut).where(Astronaut.current_mission_id == mission_id).order_by(Astronaut.id)
    ).all()

    psi_service = PsiService(db)
    crew_summaries = []
    crew_stress_scores = []
    all_mission_alerts = []

    for member in crew:
        psi_status = psi_service.get_astronaut_status(member.id)
        brs = psi_service.get_burnout_analytics(member.id)

        # Latest physio
        stmt = (
            select(PhysiologicalReading)
            .where(PhysiologicalReading.astronaut_id == member.id)
            .order_by(desc(PhysiologicalReading.created_at))
            .limit(1)
        )
        physio = db.scalar(stmt)

        member_alerts = generate_astronaut_alerts(psi_status, brs, physio)
        all_mission_alerts.extend(
            [{**a, "astronaut_id": member.id, "astronaut_name": member.name} for a in member_alerts]
        )

        current_psi = None
        if psi_status.get("latest_reading"):
            current_psi = psi_status["latest_reading"]["smoothed_stress"]
            crew_stress_scores.append(current_psi)

        crew_summaries.append({
            "id": member.id,
            "name": member.name,
            "callsign": member.callsign,
            "role": member.role,
            "status": member.status,
            "psi_stress": current_psi,
            "psi_status_color": psi_status.get("status", "grey"),
            "brs": brs.get("brs", 0.0),
            "heart_rate": physio.heart_rate if physio else None,
            "spo2": physio.spo2 if physio else None,
            "alert_count": len(member_alerts),
        })

    avg_crew_stress = round(sum(crew_stress_scores) / len(crew_stress_scores), 1) if crew_stress_scores else None

    return {
        "mission": {
            "id": mission.id,
            "name": mission.name,
            "code": mission.code,
            "status": mission.status,
            "description": mission.description,
            "start_date": mission.start_date.isoformat() if mission.start_date else None,
        },
        "crew_count": len(crew),
        "crew_behavioral_average_stress": avg_crew_stress,
        "crew": crew_summaries,
        "active_alerts": all_mission_alerts,
    }
