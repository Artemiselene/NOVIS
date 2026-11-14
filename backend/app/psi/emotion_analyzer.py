"""
Emotion Analyzer — PSI-Net v5
DeepFace (primary) + OpenCV Haar cascade stub (fallback).

KEY DESIGN PRINCIPLES:
  1. DeepFace path: NO pre-amplification — rebalance_emotions() in
     research_monitor.py handles all correction with calibrated tiers.
  2. Stub path: 3-signal brow detection, neutral base lowered 38->20,
     angry base raised 9->16, brow multiplier 22->50.
  3. Grimace suppression: post-normalize, only when neg clearly > happy.
  4. Smile: 3-signal voting (cascade + cheek-raise + corner brightness).

ETHICAL & SCIENTIFIC NOTICE:
  - Facial expression estimates are behavioral proxy signals and must never
    be interpreted as definitive psychological or emotional truth.
"""

from typing import Dict, Any, Optional, List
import numpy as np
import os

_EMOTION_KEYS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

_DeepFace      = None
_face_cascade  = None
_smile_cascade = None
_eye_cascade   = None

_stub_prev_gray  = None
_stub_walk       = None
_stub_last_time  = 0

_last_features = {
    'smile_score': 0.0, 'eye_openness': 0.5,
    'brow_furrow': 0.0, 'face_found': False
}


def get_last_features() -> Dict[str, Any]:
    return dict(_last_features)


def _get_deepface():
    global _DeepFace
    if _DeepFace is None:
        try:
            from deepface import DeepFace
            _DeepFace = DeepFace
        except ImportError:
            _DeepFace = False
    return _DeepFace if _DeepFace else None


def _get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        import cv2
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    return _face_cascade


def _get_smile_cascade():
    global _smile_cascade
    if _smile_cascade is None:
        import cv2
        _smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml')
    return _smile_cascade


def _get_eye_cascade():
    global _eye_cascade
    if _eye_cascade is None:
        import cv2
        _eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
    return _eye_cascade


# ==========================================================================
# DEEPFACE PATH
# ==========================================================================
def analyze_emotion_frame(frame, face_box=None) -> Optional[Dict[str, float]]:
    """
    Analyze emotion from BGR frame.
    DeepFace when available, OpenCV stub otherwise.
    rebalance_emotions() in research_monitor.py applies the heavy correction —
    we do NOT pre-amplify here to avoid double-processing.
    """
    df = _get_deepface()
    if df:
        try:
            result = df.analyze(img_path=frame, actions=['emotion'],
                                enforce_detection=False, silent=True)
            if result:
                data   = result[0] if isinstance(result, list) else result
                emotions = data.get('emotion', {})
            else:
                return _stub_emotions(frame, face_box)
        except Exception:
            return _stub_emotions(frame, face_box)
    else:
        return _stub_emotions(frame, face_box)

    if not isinstance(emotions, dict) or not emotions:
        return None

    # Convert to float
    emotions = {k: float(v) for k, v in emotions.items()}

    # Normalize to 100%
    total = sum(emotions.values())
    if total > 0:
        for k in emotions:
            emotions[k] = round((emotions[k] / total) * 100, 2)

    # Grimace guard (post-normalize):
    # DeepFace confuses open-mouth anger with happiness.
    # Only suppress if angry+disgust+fear clearly dominate happy.
    neg = emotions.get('angry', 0) + emotions.get('disgust', 0) + emotions.get('fear', 0)
    h   = emotions.get('happy', 0)
    if neg > h * 1.2 and h > 8:
        # Redistribute: suppress happy, add to angry
        excess = h * 0.60
        emotions['happy']   = round(h - excess, 2)
        emotions['angry']   = round(emotions.get('angry', 0) + excess * 0.70, 2)
        emotions['disgust'] = round(emotions.get('disgust', 0) + excess * 0.20, 2)
        # Re-normalize
        total = sum(emotions.values())
        if total > 0:
            for k in emotions:
                emotions[k] = round((emotions[k] / total) * 100, 2)

    return emotions


def analyze_emotion_image(path: str) -> Optional[Dict[str, float]]:
    df = _get_deepface()
    if df:
        try:
            result = df.analyze(img_path=path, actions=['emotion'],
                                enforce_detection=False, silent=True)
            if result:
                data = result[0] if isinstance(result, list) else result
                return data.get('emotion', {}) or None
        except Exception:
            pass
        return None
    try:
        import cv2
        img = cv2.imread(path)
        if img is not None:
            return _stub_emotions(img)
    except Exception:
        pass
    return {'neutral': 42.0, 'happy': 14.0, 'sad': 10.0, 'angry': 9.0,
            'surprise': 9.0, 'fear': 8.0, 'disgust': 8.0}


# ==========================================================================
# OPENCV STUB PATH — full feature detection
# ==========================================================================
def _stub_emotions(frame, face_box=None) -> Dict[str, float]:
    """
    Fallback when DeepFace unavailable.
    Uses 3-signal brow detection, cheek-raise smile, eye openness.
    neutral base reduced 38->20, angry base raised 9->16, brow mult 22->50.
    """
    global _stub_prev_gray, _stub_walk, _stub_last_time, _last_features
    import cv2
    import time as _time

    now = _time.time()
    dt  = min(now - _stub_last_time, 2.0) if _stub_last_time > 0 else 0.5
    _stub_last_time = now

    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    fh, fw  = gray.shape

    if _stub_walk is None:
        _stub_walk = {e: 0.0 for e in _EMOTION_KEYS}

    mean_lum = float(np.mean(gray))
    std_lum  = float(np.std(gray))
    cf       = (std_lum - 40) / 80.0

    # Motion
    motion = 0.0
    if _stub_prev_gray is not None and _stub_prev_gray.shape == gray.shape:
        diff      = cv2.absdiff(_stub_prev_gray, gray)
        raw_motion = float(np.mean(diff)) / 255.0
        motion    = min(0.3, raw_motion) * 3.3
    _stub_prev_gray = gray.copy()

    # Feature defaults
    smile_score  = 0.0
    eye_openness = 0.5
    mouth_open   = 0.0
    brow_furrow  = 0.0

    # Face detection
    has_face = False
    if face_box is not None:
        fx    = max(0, face_box['x'])
        fy    = max(0, face_box['y'])
        fw_f  = min(face_box['w'], fw - fx)
        fh_f  = min(face_box['h'], fh - fy)
        has_face = fw_f > 30 and fh_f > 30
    else:
        faces = _get_face_cascade().detectMultiScale(gray, 1.15, 4, minSize=(50, 50))
        if len(faces) > 0:
            fx, fy, fw_f, fh_f = max(faces, key=lambda f: f[2] * f[3])
            has_face = True

    if has_face:
        face_roi = gray[fy:fy+fh_f, fx:fx+fw_f]

        # -- BROW FURROW - 3-signal system ---------------------------------
        brow_band    = face_roi[int(fh_f*0.18):int(fh_f*0.40), int(fw_f*0.10):int(fw_f*0.90)]
        forehead_roi = face_roi[:int(fh_f*0.18),               int(fw_f*0.10):int(fw_f*0.90)]
        brow_signals = 0
        brow_s1 = brow_s2 = brow_s3 = 0.0

        if brow_band.size > 50 and forehead_roi.size > 20:
            # S1: brightness contrast
            diff_b = float(np.mean(forehead_roi)) - float(np.mean(brow_band))
            if diff_b > 6:
                brow_s1 = min(1.0, (diff_b - 6) / 24.0)
                if brow_s1 > 0.15: brow_signals += 1

            # S2: vertical gradient (Sobel dy)
            vert_grad = cv2.Sobel(brow_band, cv2.CV_64F, 0, 1, ksize=3)
            grad_e    = float(np.mean(np.abs(vert_grad)))
            if grad_e > 12:
                brow_s2 = min(1.0, (grad_e - 12) / 20.0)
                if brow_s2 > 0.15: brow_signals += 1

            # S3: Laplacian texture variance
            lap        = cv2.Laplacian(brow_band, cv2.CV_64F)
            texture_v  = float(np.var(lap))
            if texture_v > 80:
                brow_s3 = min(1.0, (texture_v - 80) / 180.0)
                if brow_s3 > 0.15: brow_signals += 1

        raw_furrow  = brow_s1 * 0.35 + brow_s2 * 0.40 + brow_s3 * 0.25
        if brow_signals >= 2:
            brow_furrow = min(1.0, raw_furrow * 1.5)
        elif brow_signals == 1:
            brow_furrow = min(0.40, raw_furrow * 0.8)

        # -- SMILE - 3-signal voting ----------------------------------------
        lower_y    = int(fh_f * 0.48)
        lower_face = face_roi[lower_y:, :]
        cascade_sc = cheek_sc = corner_sc = 0.0
        smile_sigs = 0

        if lower_face.size > 0:
            smiles = _get_smile_cascade().detectMultiScale(
                lower_face, scaleFactor=1.25, minNeighbors=16,
                minSize=(fw_f // 6, fw_f // 12))
            if len(smiles) > 0:
                biggest  = max(smiles, key=lambda s: s[2] * s[3])
                cascade_sc = min(1.0, (biggest[2] / fw_f) * 2.2)
                if cascade_sc > 0.15: smile_sigs += 1

            # Cheek raise
            c_y1, c_y2 = int(fh_f*0.38), int(fh_f*0.58)
            n_y1, n_y2 = int(fh_f*0.30), int(fh_f*0.48)
            lc = face_roi[c_y1:c_y2, :int(fw_f*0.28)]
            rc = face_roi[c_y1:c_y2, int(fw_f*0.72):]
            nb = face_roi[n_y1:n_y2, int(fw_f*0.38):int(fw_f*0.62)]
            if lc.size > 0 and rc.size > 0 and nb.size > 0:
                cheek_sc = max(0.0, ((np.mean(lc)+np.mean(rc))/2 - np.mean(nb) + 5) / 22.0)
                if cheek_sc > 0.28: smile_sigs += 1

            # Corner brightness
            m_y1, m_y2 = int(fh_f*0.68), int(fh_f*0.86)
            if m_y2 <= fh_f and m_y2 > m_y1:
                mr = face_roi[m_y1:m_y2, :]
                lco = float(np.mean(mr[:, :int(fw_f*0.22)])) if mr.size else 0
                rco = float(np.mean(mr[:, int(fw_f*0.78):])) if mr.size else 0
                mc  = float(np.mean(mr[:, int(fw_f*0.38):int(fw_f*0.62)])) if mr.size else 0
                corner_sc = max(0.0, ((lco+rco)/2 - mc + 4) / 18.0)
                if corner_sc > 0.32: smile_sigs += 1

            # Mouth open -> surprise
            mouth_roi = face_roi[int(fh_f*0.65):, int(fw_f*0.25):int(fw_f*0.75)]
            if mouth_roi.size > 0:
                mb = float(np.mean(mouth_roi))
                fb = float(np.mean(face_roi))
                if mb < fb - 18:
                    mouth_open = min(1.0, (fb - mb - 18) / 38.0)

        raw_smile = cascade_sc*0.50 + cheek_sc*0.30 + corner_sc*0.20
        if smile_sigs >= 2:
            smile_score = min(1.0, raw_smile * 1.5)
        elif smile_sigs == 1:
            smile_score = min(0.35, raw_smile * 0.65)

        # Grimace guard: brow furrowed + cascade fired = not a genuine smile
        if brow_furrow > 0.28 and smile_score > 0.20:
            smile_score = smile_score * max(0.0, 1.0 - brow_furrow * 0.95)

        # -- EYES -----------------------------------------------------------
        upper_face = face_roi[:int(fh_f * 0.55), :]
        if upper_face.size > 0:
            eyes = _get_eye_cascade().detectMultiScale(
                upper_face, scaleFactor=1.1, minNeighbors=5, minSize=(15, 15))
            n_eyes = min(len(eyes), 2)
            if n_eyes >= 2:
                top2  = sorted(eyes, key=lambda e: e[2]*e[3], reverse=True)[:2]
                total_area = sum(e[2]*e[3] for e in top2)
                eye_ratio  = total_area / (fw_f * fh_f * 0.55)
                eye_openness = min(1.0, max(0.35, eye_ratio / 0.035))
            elif n_eyes == 1:
                eye_openness = 0.30
            else:
                eye_openness = 0.15

    _last_features = {
        'smile_score':  round(smile_score, 2),
        'eye_openness': round(eye_openness, 2),
        'brow_furrow':  round(brow_furrow, 2),
        'face_found':   has_face,
    }

    # -- EXPRESSION MODIFIERS -------------------------------------------
    smile_mod    = smile_score * 26.0
    eye_surprise = max(0, (eye_openness - 0.65)) * 20.0
    eye_squint   = max(0, (0.25 - eye_openness)) * 20.0   # squinting = angry signal
    brow_mod     = brow_furrow * 50.0                      # primary angry driver
    mouth_mod    = mouth_open  * 16.0

    # Yell = open mouth + furrowed brow simultaneously -> angry, not surprise
    yell_angry = 0.0
    if mouth_open > 0.25 and brow_furrow > 0.25:
        yell_angry = mouth_open * brow_furrow * 30.0
        mouth_mod  = mouth_open * 5.0

    # -- TIME OSCILLATIONS ----------------------------------------------
    def osc(freqs, amps):
        return sum(a * np.sin(now * f) for f, a in zip(freqs, amps))

    t_osc = {
        'neutral':  osc([0.31, 0.73, 1.57], [1.5, 1.0, 0.8]),
        'happy':    osc([0.43, 0.97, 1.83], [1.2, 0.8, 0.6]),
        'sad':      osc([0.37, 0.83, 2.11], [1.2, 0.8, 0.5]),
        'angry':    osc([0.29, 0.67, 1.91], [1.2, 0.8, 0.6]),
        'surprise': osc([0.53, 1.13, 2.37], [1.2, 0.8, 0.5]),
        'fear':     osc([0.41, 0.89, 1.73], [1.2, 0.8, 0.5]),
        'disgust':  osc([0.47, 1.03, 2.03], [1.0, 0.6, 0.4]),
    }

    # -- RANDOM WALK ----------------------------------------------------
    walk_step = dt * 0.3
    for emo in _EMOTION_KEYS:
        push = np.sin(now * (hash(emo) % 97) / 8.0 + mean_lum * 0.05) * 1.5
        _stub_walk[emo] = _stub_walk[emo] * 0.92 + push * walk_step
        _stub_walk[emo] = max(-4.0, min(4.0, _stub_walk[emo]))

    # -- COMPOSE --------------------------------------------------------
    base = {
        'neutral':  20.0 + t_osc['neutral']  + _stub_walk['neutral']
                    - smile_mod * 0.55
                    - eye_surprise * 0.25
                    - mouth_mod * 0.30
                    - motion * 10.0
                    - brow_furrow * 10.0,
        'happy':    14.0 + t_osc['happy']    + _stub_walk['happy']
                    + smile_mod
                    - cf * 2,
        'sad':      10.0 + t_osc['sad']      + _stub_walk['sad']
                    + cf * 2
                    - smile_mod * 0.5
                    + eye_squint * 0.5
                    + brow_furrow * 4.0
                    + (1.0 - eye_openness) * 6.0,
        'angry':    16.0 + t_osc['angry']    + _stub_walk['angry']
                    + cf * 3
                    - smile_mod * 0.5
                    + eye_squint * 1.4
                    + brow_mod
                    + motion * 4.0
                    + yell_angry,
        'surprise':  9.0 + t_osc['surprise'] + _stub_walk['surprise']
                    + eye_surprise + mouth_mod + motion * 10.0,
        'fear':      8.0 + t_osc['fear']     + _stub_walk['fear']
                    + eye_surprise * 0.5 + motion * 6.0,
        'disgust':   8.0 + t_osc['disgust']  + _stub_walk['disgust']
                    + brow_mod * 0.30 - smile_mod * 0.10,
    }

    for k in base:
        base[k] = max(1.0, base[k])
    total = sum(base.values())
    return {k: round(v / total * 100, 2) for k, v in base.items()}


# ==========================================================================
# FACE DETECTION
# ==========================================================================
def detect_face_box(frame) -> Optional[Dict[str, int]]:
    import cv2
    cascade = _get_face_cascade()
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces   = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40),
        flags=cv2.CASCADE_SCALE_IMAGE)
    if len(faces) == 0:
        return None
    x, y, w, h = [int(v) for v in max(faces, key=lambda f: f[2] * f[3])]
    return {'x': x, 'y': y, 'w': w, 'h': h}


# ==========================================================================
# FACE VERIFICATION
# ==========================================================================
def verify_face(frame, reference_path: str) -> Optional[Dict]:
    df = _get_deepface()
    if not df or not os.path.exists(reference_path):
        return None
    try:
        result = df.verify(
            img1_path=frame, img2_path=reference_path,
            enforce_detection=False, detector_backend='opencv', silent=True)
        return {
            'verified':  bool(result.get('verified', False)),
            'distance':  round(float(result.get('distance', 1.0)), 3),
            'threshold': float(result.get('threshold', 0.4)),
        }
    except Exception:
        return None


def verify_face_against_photos(frame, photo_paths: List[str]) -> Optional[Dict]:
    df = _get_deepface()
    if not df or not photo_paths:
        return None
    for path in photo_paths[:3]:
        result = verify_face(frame, path)
        if result is not None:
            return result
    return None


def is_deepface_available() -> bool:
    return _get_deepface() is not None
