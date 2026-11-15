"""
ASTRA MIND — Psychological Stress Index (PSI) Behavioral Health Intelligence Engine
===================================================================================

IMPORTANT NOTICE & ETHICAL BOUNDARIES:
- PSI is an experimental behavioral-indicator score derived from facial-expression model outputs.
- PSI is NOT clinically validated as a diagnostic tool or medical protocol.
- Facial expressions are NOT interpreted as definitive psychological stress or emotion truth.
- Facial-expression-derived PSI is kept strictly separate from physiological measurements (ECG, HRV, respiration).
- PSI does NOT automatically convert into a clinical brain-health status.
- Personal baseline privacy is strictly preserved.
"""

from .research_monitor import (
    calculate_stress_from_emotions,
    calculate_emotional_stress,
    rebalance_emotions,
    ResearchStressMonitor,
    EMOTION_DIMENSIONS,
    STRESS_WEIGHTS,
    calculate_brs,
    classify_brs,
    detect_chronic_stress,
)
from .emotion_analyzer import (
    analyze_emotion_frame,
    analyze_emotion_image,
    detect_face_box,
    verify_face_against_photos,
    is_deepface_available,
    get_last_features,
)
from .calibration import (
    calculate_baseline_stress,
    decode_base64_frame,
)
from .repository import PsiRepository
from .service import PsiService, get_active_monitor, clear_active_monitor

__all__ = [
    "calculate_stress_from_emotions",
    "calculate_emotional_stress",
    "rebalance_emotions",
    "ResearchStressMonitor",
    "EMOTION_DIMENSIONS",
    "STRESS_WEIGHTS",
    "calculate_brs",
    "classify_brs",
    "detect_chronic_stress",
    "analyze_emotion_frame",
    "analyze_emotion_image",
    "detect_face_box",
    "verify_face_against_photos",
    "is_deepface_available",
    "get_last_features",
    "calculate_baseline_stress",
    "decode_base64_frame",
    "PsiRepository",
    "PsiService",
    "get_active_monitor",
    "clear_active_monitor",
]
