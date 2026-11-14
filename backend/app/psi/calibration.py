"""
Calibration & Personal Baseline Calculation — PSI Engine
=========================================================
Implements the exact statistical calibration and outlier-removal methodology
from the original PSI platform.

Mathematical Baseline Model:
  1. Per-photo resting stress:
     S_i = calculate_stress_from_emotions(photo_i, task_complexity=5.0, motion_level=0.0)
     (Evaluated under neutral context without task or motion bias)
  2. IQR-trimmed mean:
     mu = mean(S_i in [Q1, Q3])  (robust against lighting changes / eye blinks)
  3. Personal variability:
     sigma = max(std(S_i), 2.0)  (enforces safe variability floor)
  4. Natural facial expressiveness adjustment:
     Compensates for naturally furrowed brows or expressive resting features.
  5. Asymmetric optimal functioning range:
     optimal_low  = max(0.0, baseline - 0.8 * sigma)
     optimal_high = min(100.0, baseline + 1.5 * sigma)

ETHICAL & PRIVACY NOTICE:
  - Preserves individual baseline privacy.
  - Personal photographs are analyzed transiently in memory.
  - Does NOT store personal image files or biographical HR records.
"""

import io
import base64
import numpy as np
from typing import List, Dict, Optional, Any
from PIL import Image

from .research_monitor import calculate_stress_from_emotions, calculate_emotional_stress


def decode_base64_frame(image_data: str) -> Optional[np.ndarray]:
    """
    Safely decode a base64-encoded image string into a BGR numpy array (OpenCV format)
    in memory without persisting personal files to disk.
    """
    try:
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        # Convert RGB PIL Image to BGR numpy array for OpenCV
        rgb_arr = np.array(image)
        bgr_arr = rgb_arr[:, :, ::-1].copy()
        return bgr_arr
    except Exception as e:
        print(f"[CALIBRATION ERROR] Failed to decode base64 frame: {e}")
        return None


def calculate_baseline_stress(analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate personalized baseline and optimal functioning bounds from calibration analyses.
    analysis_results: List of dicts, each containing:
      - 'emotions': Dict[str, float] with emotion probabilities
      - 'valid': bool (whether face was detected and analyzed)

    Returns:
      Dictionary with baseline_stress, baseline_sigma, optimal_range, and natural emotion medians.
    """
    valid = [r for r in analysis_results if r.get('valid') and r.get('emotions')]

    if len(valid) < 3:
        # Conservative default when insufficient valid calibration photos are available
        return {
            'baseline_stress': 25.0,
            'baseline_sigma': 5.0,
            'optimal_range': [21.0, 32.5],
            'natural_angry': 10.0,
            'natural_sad': 10.0,
            'natural_fear': 10.0,
            'valid_photos': len(valid),
            'note': 'Default — need >= 3 valid photos',
        }

    emotion_keys = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
    all_emotions = {k: [] for k in emotion_keys}
    scores = []

    for r in valid:
        # Neutral context: task_complexity=5.0, motion_level=0.0
        s = calculate_stress_from_emotions(
            r['emotions'], task_complexity=5.0, motion_level=0.0
        )
        scores.append(s)
        for k in emotion_keys:
            val = r['emotions'].get(k)
            if val is not None:
                all_emotions[k].append(float(val))

    arr = np.array(scores, dtype=float)

    # IQR-trimmed mean (interquartile range filtering)
    q1, q3 = np.percentile(arr, [25, 75])
    mask = (arr >= q1) & (arr <= q3)
    trimmed = arr[mask] if mask.sum() >= 2 else arr
    mu = float(np.mean(trimmed))

    # Personal sigma with floor of 2.0 to maintain meaningful Z-scores
    sigma = float(np.std(arr)) if len(arr) > 1 else 3.0
    sigma = max(sigma, 2.0)

    medians = {k: float(np.median(v)) if v else 0.0 for k, v in all_emotions.items()}

    # Natural expressive face adjustment
    natural_angry = medians.get('angry', 0.0)
    natural_sad = medians.get('sad', 0.0)
    natural_fear = medians.get('fear', 0.0)

    adjust = 0.0
    if natural_angry > 20.0:
        adjust -= (natural_angry - 20.0) * 0.15
    if natural_sad > 20.0:
        adjust -= (natural_sad - 20.0) * 0.10
    if natural_fear > 15.0:
        adjust -= (natural_fear - 15.0) * 0.10

    baseline = round(max(5.0, min(90.0, mu + adjust)), 1)
    opt_low = round(max(0.0, baseline - 0.8 * sigma), 1)
    opt_high = round(min(100.0, baseline + 1.5 * sigma), 1)

    return {
        'baseline_stress': baseline,
        'baseline_sigma': round(sigma, 2),
        'optimal_range': [opt_low, opt_high],
        'natural_angry': round(natural_angry, 1),
        'natural_sad': round(natural_sad, 1),
        'natural_fear': round(natural_fear, 1),
        'valid_photos': len(valid),
        'emotion_breakdown': {k: round(v, 1) for k, v in medians.items() if v > 0},
    }
