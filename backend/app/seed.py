from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import BodySystem, HealthChallenge, HealthEducation, MissionEnvironment

BODY = [
 ("brain","Brain & nervous system","Coordinates cognition, sensory processing and nervous-system activity.",["eeg_features","reaction_time","cognitive_accuracy"],["Use the cognitive assessment to record performance; discuss persistent concerns with qualified medical staff."]),
 ("heart","Heart & cardiovascular","Circulates blood; heart rate and HRV are indirect cardiovascular/autonomic observations.",["heart_rate","hrv"],["Review trends against the astronaut's personal reference range."]),
 ("lungs","Respiratory system","Supports ventilation and gas exchange.",["respiration_rate"],["Review the available respiration trend; seek qualified review for concerning symptoms."]),
 ("muscles","Muscles & skeletal system","Supports movement, strength and musculoskeletal function.",["activity_level","exercise_sessions"],["Follow mission-approved exercise guidance and record recovery."]),
 ("digestive","Digestive system","Processes food and supports nutrient absorption.",["self_reported_digestive_wellbeing"],["Record symptoms or changes through the approved health check-in."]),
 ("sleep","Sleep & recovery","Sleep supports recovery, attention and well-being.",["sleep_duration","sleep_quality","fatigue_indicator"],["Review sleep patterns and maintain the mission's approved rest routine."]),
]
EDU = [
 ("heart_rate","Heart rate","Number of heart beats per minute.","Provides context about cardiovascular response and activity.","Typically measured by an optical or electrical sensor.","Exercise, posture, stress, illness, medication and measurement conditions.","A single value is not a diagnosis; compare trends and context.","Use approved medical guidance for persistent symptoms or concerning readings."),
 ("hrv","Heart rate variability","Variation in time intervals between successive heartbeats.","Can provide information about autonomic regulation and recovery.","Derived from suitable beat-to-beat intervals, often ECG or validated PPG.","Breathing, movement, sleep, age, illness and signal quality.","HRV is individual and should be interpreted against personal trends.","Discuss persistent changes or symptoms with qualified medical staff."),
 ("eda","Electrodermal activity","Changes in skin conductance associated with sweat-gland activity.","Can reflect sympathetic arousal but is not specific to stress.","Measured using skin electrodes.","Temperature, movement, hydration, electrode contact and arousal.","EDA alone cannot identify the cause of a change.","Interpret alongside context and other signals."),
 ("respiration","Respiration rate","Number of breaths per minute.","Provides context about breathing patterns.","Measured using a suitable respiratory sensor or derived signal.","Activity, posture, sleep, illness and measurement method.","A derived rate depends on signal quality.","Seek qualified review for persistent breathing difficulty."),
 ("eeg","EEG features","Electrical activity recorded at the scalp; this demo may use derived band features.","Can support research into brain activity and cognitive state.","Measured with EEG electrodes; this extension only displays supplied features.","Electrode contact, artifacts, task, sleep and processing method.","Band features do not directly diagnose stress or mental health.","Interpret only with validated methods and qualified expertise."),
 ("sleep","Sleep","Sleep duration, continuity and quality estimates.","Sleep patterns relate to recovery and daytime functioning.","May be estimated from actigraphy, sleep devices or sleep logs.","Schedule, light, workload, environment and device algorithm.","Consumer or simulated estimates are not clinical sleep diagnoses.","Discuss persistent sleep difficulties with qualified staff."),
 ("fatigue","Fatigue","A multi-signal indicator of possible reduced alertness or recovery.","Can support awareness of changing workload and recovery patterns.","Derived from available sleep, activity and self-report data.","Sleep, workload, health, activity and individual variation.","A prototype score is not a medical measurement.","Use mission procedures and seek human review when needed."),
 ("cognitive","Cognitive performance","Performance on tasks such as reaction time, attention and memory.","Can help track task performance over time.","Short standardized or consistently administered tasks.","Practice, motivation, workload, sleep and device latency.","Task scores are context-dependent and not a diagnosis.","Discuss persistent functional concerns with qualified staff."),
 ("mood","Mood","Self-reported emotional state at a given time.","Supports personal reflection and longitudinal well-being review.","Voluntary self-assessment.","Context, culture, timing and individual differences.","Mood is personal; do not infer it from facial expression alone.","Use available human support when desired or needed."),
 ("workload","Workload","Self-reported or task-derived estimate of perceived demand.","Can contextualize performance and recovery.","Self-report or defined task measures.","Task complexity, time pressure, team support and experience.","Workload scores depend on the chosen instrument.","Discuss sustained excessive workload with the appropriate team."),
 ("psi","PSI facial-behavior indicator","An experimental score derived from facial-expression model outputs.","May be explored as one optional behavioral signal.","Calculated from facial-expression estimates when camera data is available.","Lighting, camera angle, model bias, expression and context.","Not a validated measure of psychological stress or emotion truth.","Do not use alone for health decisions; prefer voluntary self-report and qualified review."),
]
CHALLENGES = [
 ("daily_checkin","Complete a well-being check-in","Record a voluntary mood and workload check-in.",10,"daily"),
 ("sleep_reflection","Review sleep routine","Review and record the previous sleep period.",10,"daily"),
 ("cognitive_check","Complete a cognitive task","Complete an optional short attention or reaction-time task.",10,"daily"),
 ("recovery_log","Log a recovery activity","Record a rest or recovery activity.",10,"daily"),
]

def seed(target_session=None):
    if target_session is not None:
        _populate(target_session)
        return
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _populate(db)

def _populate(db):
    if not db.scalars(select(BodySystem)).first():
        db.add_all([BodySystem(key=k,name=n,main_function=f,indicators=i,suggested_actions=a) for k,n,f,i,a in BODY])
    if not db.scalars(select(HealthChallenge)).first():
        db.add_all([HealthChallenge(code=c,title=t,description=d,points=p,kind=kind) for c,t,d,p,kind in CHALLENGES])
    if not db.scalars(select(HealthEducation)).first():
        db.add_all([HealthEducation(metric_key=x[0],title=x[1],what=x[2],why=x[3],how=x[4],influences=x[5],limitations=x[6],understand=x[6],when_advice=x[7]) for x in EDU])
    if not db.scalars(select(MissionEnvironment)).first():
        db.add_all([
          MissionEnvironment(mission_id=1,env_type="spacecraft",name="Deep-space transit",duration_days=180,location="Transit vehicle",context={"gravity":"microgravity (simulated)"},streams=["heart_rate","hrv","sleep","activity"]),
          MissionEnvironment(mission_id=1,env_type="station",name="Orbital research station",duration_days=30,location="Low Earth orbit (simulated)",context={"gravity":"microgravity (simulated)"},streams=["heart_rate","hrv","eda","sleep","activity"]),
          MissionEnvironment(mission_id=1,env_type="rover",name="Lunar surface traverse",duration_days=7,location="Lunar surface (simulated)",context={"gravity":"lunar (simulated)"},streams=["activity","sleep","mood"]),
          MissionEnvironment(mission_id=1,env_type="base",name="Lunar habitat",duration_days=90,location="Lunar base (simulated)",context={"gravity":"lunar (simulated)"},streams=["heart_rate","sleep","activity","mood"]),
        ])
    db.commit()

if __name__ == "__main__":
    seed()
