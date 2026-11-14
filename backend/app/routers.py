from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import (MissionEnvironment, BodySystem, HealthRoutine, RoutineCompletion,
                     HealthChallenge, AstronautAchievement, HealthEducation)
from .schemas import EnvironmentCreate, RoutineCreate, CompleteRoutine

router = APIRouter()

def env_dict(e):
    return {"id":e.id,"mission_id":e.mission_id,"env_type":e.env_type,"name":e.name,
            "duration_days":e.duration_days,"location":e.location,"context":e.context,"streams":e.streams}

@router.get("/environments")
def list_environments(db: Session = Depends(get_db)):
    return [env_dict(x) for x in db.scalars(select(MissionEnvironment).order_by(MissionEnvironment.id))]

@router.post("/environments", status_code=201)
def create_environment(payload: EnvironmentCreate, db: Session = Depends(get_db)):
    obj = MissionEnvironment(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return env_dict(obj)

@router.get("/environments/{env_id}")
def get_environment(env_id: int, db: Session = Depends(get_db)):
    obj = db.get(MissionEnvironment, env_id)
    if not obj: raise HTTPException(404, "Environment not found")
    return env_dict(obj)

@router.get("/body-systems")
def list_body_systems(db: Session = Depends(get_db)):
    return [{"key":x.key,"name":x.name,"main_function":x.main_function,"indicators":x.indicators} for x in db.scalars(select(BodySystem).order_by(BodySystem.id))]

@router.get("/body-systems/{key}/status")
def body_status(key: str, astronaut_id: int, db: Session = Depends(get_db)):
    obj = db.scalar(select(BodySystem).where(BodySystem.key == key))
    if not obj: raise HTTPException(404, "Body system not found")
    # No telemetry source is connected in this standalone extension.
    return {"system":obj.key,"name":obj.name,"main_function":obj.main_function,
            "indicators":obj.indicators,"measurements":[],"baseline_comparison":None,
            "trend":[],"status":"grey",
            "explanation":"No connected source measurements are available for this body system in this extension. Connect the host ASTRA MIND telemetry adapter to display readings.",
            "suggested_actions":obj.suggested_actions,"astronaut_id":astronaut_id}

@router.get("/routines")
def list_routines(astronaut_id: int | None = None, db: Session = Depends(get_db)):
    q = select(HealthRoutine).order_by(HealthRoutine.scheduled_at)
    if astronaut_id is not None: q = q.where(HealthRoutine.astronaut_id == astronaut_id)
    return [{"id":x.id,"mission_id":x.mission_id,"astronaut_id":x.astronaut_id,"kind":x.kind,
             "title":x.title,"scheduled_at":x.scheduled_at,"reminder_minutes":x.reminder_minutes,
             "simulated":x.simulated,"completed":x.completed} for x in db.scalars(q)]

@router.post("/routines", status_code=201)
def create_routine(payload: RoutineCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["scheduled_at"] = data["scheduled_at"] or datetime.now(timezone.utc)
    obj = HealthRoutine(**data)
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id":obj.id,"title":obj.title,"completed":obj.completed}

@router.post("/routines/{routine_id}/complete")
def complete_routine(routine_id: int, payload: CompleteRoutine, db: Session = Depends(get_db)):
    obj = db.get(HealthRoutine, routine_id)
    if not obj: raise HTTPException(404, "Routine not found")
    if not obj.completed:
        obj.completed = True
        db.add(RoutineCompletion(routine_id=routine_id, notes=payload.notes))
        db.commit()
    return {"ok":True,"routine_id":routine_id,"completed":True}

@router.get("/challenges")
def list_challenges(db: Session = Depends(get_db)):
    return [{"id":x.id,"code":x.code,"title":x.title,"description":x.description,"points":x.points,"kind":x.kind} for x in db.scalars(select(HealthChallenge))]

@router.get("/achievements/{astronaut_id}")
def achievements(astronaut_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(AstronautAchievement).where(AstronautAchievement.astronaut_id == astronaut_id))
    return [{"id":x.id,"challenge_id":x.challenge_id,"earned_at":x.earned_at} for x in rows]

@router.post("/challenges/{challenge_id}/complete/{astronaut_id}")
def complete_challenge(challenge_id: int, astronaut_id: int, db: Session = Depends(get_db)):
    challenge = db.get(HealthChallenge, challenge_id)
    if not challenge: raise HTTPException(404, "Challenge not found")
    existing = db.scalar(select(AstronautAchievement).where(
        AstronautAchievement.astronaut_id == astronaut_id,
        AstronautAchievement.challenge_id == challenge_id))
    if not existing:
        existing = AstronautAchievement(astronaut_id=astronaut_id, challenge_id=challenge_id)
        db.add(existing); db.commit(); db.refresh(existing)
    return {"ok":True,"astronaut_id":astronaut_id,"challenge_id":challenge_id,
            "points_awarded":challenge.points,"reason":"Participation completion; no health outcome is rewarded."}

@router.get("/education")
def education(db: Session = Depends(get_db)):
    return [{"metric_key":x.metric_key,"title":x.title,"what":x.what,"why":x.why,"how":x.how,
             "influences":x.influences,"limitations":x.limitations,"understand":x.understand,
             "when_advice":x.when_advice} for x in db.scalars(select(HealthEducation).order_by(HealthEducation.title))]
