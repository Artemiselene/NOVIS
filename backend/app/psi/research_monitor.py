"""
Research-Grade Stress Monitor — PSI v5 Final
All emotion detection calibrations preserved:
  - rebalance_emotions: tiers calibrated for real DeepFace output (neg_sum ~0.20)
  - Happy face correctly stays low-stress (HIF suppression)
  - Angry/sad/fear properly dominant when present
  - Personalized Z-score baseline headroom nudge

ETHICAL & SCIENTIFIC NOTICE:
  - PSI is an experimental behavioral health indicator based on computer vision affect estimates.
  - It is NOT clinically validated, does NOT measure definitive psychological stress,
    and must NEVER be used as a standalone diagnostic tool.
"""

import cv2
import numpy as np
from collections import deque
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from .emotion_analyzer import analyze_emotion_frame

# =============================================================================
# VALENCE-AROUSAL TABLE (Russell Circumplex Model)
# =============================================================================
EMOTION_DIMENSIONS = {
    'angry':    (0.83, -0.88),
    'fear':     (0.90, -0.85),
    'sad':      (0.32, -0.78),
    'disgust':  (0.55, -0.70),
    'surprise': (0.78,  0.10),
    'neutral':  (0.12,  0.00),
    'happy':    (0.62,  0.90),
}
STRESS_WEIGHTS = {
    e: round(A * max(0.0, -V), 3)
    for e, (A, V) in EMOTION_DIMENSIONS.items()
}

# =============================================================================
# NEUTRAL BIAS CORRECTION — CALIBRATED FOR REAL DEEPFACE OUTPUT
# =============================================================================
def rebalance_emotions(emotions: dict) -> dict:
    """
    Corrects DeepFace's chronic neutral inflation.

    ROOT CAUSE: DeepFace outputs neutral=65% on a genuine angry face.
    After normalization: angry~0.08, neg_sum~0.20, neutral~0.65.
    Previous tiers (0.45 / 0.25 / 0.12) never fired on real angry data.

    CALIBRATED tiers (verified against real DeepFace angry/sad/fear output):
      TIER 3 (neg_sum > 0.18): strong stress  -> heavy neutral suppression + big amplification
      TIER 2 (neg_sum > 0.10): moderate stress -> medium rebalance
      TIER 1 (neg_sum > 0.05): mild stress     -> light rebalance
      CALM   (neg_sum <= 0.05): no modification -> preserve calm/happy
    """
    emotions = emotions.copy()
    total = sum(emotions.values()) or 1.0
    for k in emotions:
        emotions[k] = emotions[k] / total

    neg_sum = sum(emotions.get(e, 0) for e in ['angry', 'fear', 'sad', 'disgust'])
    happy   = emotions.get('happy', 0)

    if neg_sum > 0.18:
        # Strong stress: heavy neutral suppression + big amplification
        emotions['neutral'] *= 0.22
        emotions['angry']   *= 3.00
        emotions['fear']    *= 2.20
        emotions['sad']     *= 1.60
        emotions['disgust'] *= 1.80
        if happy > 0.12:
            emotions['happy'] *= 0.65   # grimace/teeth guard
    elif neg_sum > 0.10:
        # Moderate stress
        emotions['neutral'] *= 0.45
        emotions['angry']   *= 2.00
        emotions['fear']    *= 1.70
        emotions['sad']     *= 1.35
        emotions['disgust'] *= 1.50
        if happy > 0.18:
            emotions['happy'] *= 0.80
    elif neg_sum > 0.05:
        # Mild stress
        emotions['neutral'] *= 0.70
        emotions['angry']   *= 1.40
        emotions['fear']    *= 1.25
        emotions['sad']     *= 1.15
    # else: calm/happy -> no modification

    total = sum(emotions.values()) or 1.0
    for k in emotions:
        emotions[k] /= total
    return emotions


# =============================================================================
# CALIBRATION STRESS (no baseline, no task, no motion)
# =============================================================================
def calculate_emotional_stress(emotions: dict) -> float:
    """
    Calibration-phase stress calculation (ACSI Steps 1-3).
    Reflects resting emotional affect without task/motion contamination.
    """
    emotions = rebalance_emotions(emotions)
    total = sum(emotions.values()) or 1.0
    happy_pct   = emotions.get('happy', 0)
    neutral_pct = emotions.get('neutral', 0)
    HIF = max(0.05, 1.0 - happy_pct * 0.75)
    NAS = 0.0
    for e, (A, V) in EMOTION_DIMENSIONS.items():
        p = emotions.get(e, 0)
        if V < 0:
            NAS += p * A * (abs(V) ** 1.35)
        else:
            NAS -= p * A * (abs(V) ** 1.05)
    high_arousal = sum(
        emotions.get(e, 0) * A
        for e, (A, V) in EMOTION_DIMENSIONS.items() if V < -0.5
    )
    ABST = 1.0 + (high_arousal ** 1.2) * 1.4
    NIF   = max(0.35, 1.0 - neutral_pct * 0.50)
    floor = max(0.0, 1.0 - happy_pct - neutral_pct) * 0.07
    E = max(floor, NAS * HIF * ABST) * 125.0 * NIF
    return round(min(100.0, max(0.0, E)), 4)


# =============================================================================
# LIVE PSI FORMULA (PSI v5)
# =============================================================================
def calculate_stress_from_emotions(
    emotions: dict,
    task_complexity: float = 5.0,
    motion_level: float = 0.0,
    baseline: Optional[float] = None,
    baseline_sigma: Optional[float] = None,
) -> float:
    """
    PSI v5 — Psychological Stress Index.
    Applies rebalance_emotions first, then computes multi-factor stress score.
    """
    emotions = rebalance_emotions(emotions)

    happy_pct   = emotions.get('happy',   0)
    neutral_pct = emotions.get('neutral', 0)

    HIF = max(0.05, 1.0 - happy_pct * 0.80)
    NIF = max(0.50, 1.0 - neutral_pct * 0.35)

    NAS = 0.0
    for e, (A, V) in EMOTION_DIMENSIONS.items():
        p = emotions.get(e, 0)
        if V < 0:
            NAS += p * A * (abs(V) ** 1.35)
        else:
            NAS -= p * A * (abs(V) ** 1.05)

    ABST = 1.0 + 0.85 * sum(
        emotions.get(e, 0) * A
        for e, (A, V) in EMOTION_DIMENSIONS.items() if V < -0.5
    )

    floor = max(0.0, 1.0 - happy_pct - neutral_pct) * 0.07
    E = max(floor, NAS * HIF * ABST) * 125.0 * NIF
    E = max(0.0, E)

    T = max(0.0, (task_complexity - 5.0)) * 3.5 * HIF * 0.55
    M = motion_level * 1.2 * HIF

    raw = min(100.0, max(0.0, E + T + M))

    if baseline is not None and baseline_sigma is not None and baseline_sigma > 0:
        if raw > baseline:
            Z        = (raw - baseline) / max(baseline_sigma, 1.0)
            headroom = max(0.0, (90.0 - raw) / 90.0)
            nudge    = min(12.0, Z * 2.5) * headroom
            final    = min(100.0, raw + nudge)
        else:
            final = raw
    else:
        final = raw

    return round(min(100.0, max(0.0, final)), 2)


# =============================================================================
# BURNOUT RISK SCORE (BRS) & CHRONIC STRESS
# =============================================================================
def calculate_brs(weekly_avg: float, variability: float, task_load: float) -> float:
    """
    Burnout Risk Score:
    BRS = 0.5 * weekly_avg + 0.3 * variability + 0.2 * task_load
    """
    return round(min(100.0, 0.5 * weekly_avg + 0.3 * variability + 0.2 * task_load), 1)


def classify_brs(score: float) -> str:
    """Classify BRS into risk tiers."""
    if score < 30.0:
        return "Low"
    elif score < 50.0:
        return "Moderate"
    elif score < 70.0:
        return "High"
    return "Burnout Risk"


def detect_chronic_stress(daily_averages: List[float], baseline: float) -> bool:
    """
    Chronic stress detection:
    Fires when daily average > baseline + 15.0 for 7 consecutive days.
    """
    threshold = baseline + 15.0
    if len(daily_averages) < 7:
        return False
    return all(d > threshold for d in daily_averages[-7:])


# =============================================================================
# MONITOR CLASS
# =============================================================================
class ResearchStressMonitor:

    def __init__(
        self,
        staff_baseline: float = 25.0,
        stress_threshold: float = 70.0,
        baseline_sigma: float = 5.0,
        sampling_mode: str = 'research'
    ):
        self.baseline        = float(staff_baseline)
        self.stress_threshold = float(stress_threshold)
        self.baseline_sigma  = max(float(baseline_sigma), 1.0)
        self.stress_window   = deque(maxlen=10)
        self.motion_history  = deque(maxlen=10)
        self.prev_frame      = None
        self.last_analysis_time = 0.0
        self.stress_trend    = 'stable'

    def detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self.prev_frame is None:
            self.prev_frame = gray
            return 0.0, False
        delta  = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        self.motion_history.append(float(np.mean(thresh)))
        self.prev_frame = gray
        avg = float(np.mean(self.motion_history))
        return round(min(10.0, avg / 10.0), 2), avg > 10

    def apply_smoothing(self, value: float) -> float:
        self.stress_window.append(value)
        return round(float(np.mean(self.stress_window)), 2)

    def process_frame(self, frame, staff_id=None, db=None, force=False, face_box=None, task_complexity=5.0):
        motion_level, motion_detected = self.detect_motion(frame)
        emotions = analyze_emotion_frame(frame, face_box=face_box)
        if not emotions:
            return None

        dominant_emotion = max(emotions, key=lambda k: emotions.get(k, 0))

        task_name = ''
        if db and staff_id:
            try:
                task_complexity = db.get_active_task_complexity(staff_id)
                task_name       = db.get_active_task_name(staff_id)
            except Exception:
                pass

        raw      = calculate_stress_from_emotions(
            emotions,
            task_complexity=task_complexity,
            motion_level=motion_level,
            baseline=self.baseline,
            baseline_sigma=self.baseline_sigma,
        )
        smoothed = self.apply_smoothing(raw)

        return {
            'timestamp':        datetime.now().isoformat(),
            'raw_stress':       raw,
            'smoothed_stress':  smoothed,
            'emotion_vector':   emotions,
            'dominant_emotion': dominant_emotion,
            'motion_level':     motion_level,
            'motion_detected':  motion_detected,
            'task_type':        task_name,
            'task_complexity':  task_complexity,
            'risk_level': 'high' if smoothed > self.baseline + 2 * self.baseline_sigma else 'low',
        }
