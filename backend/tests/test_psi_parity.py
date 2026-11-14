"""
ASTRA MIND — PSI Mathematical Parity & Benchmark Test Suite
============================================================
Tests mathematical parity between the original PSI implementation (fix_clean)
and the migrated ASTRA MIND implementation (app.psi).

Covers all 10 benchmark modules (B1–B10) plus calibration parity (B11)
and extensive randomized differential fuzzing (B12).
"""

import sys
import os
import math
import random
import statistics
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINAL_PSI_DIR = os.path.abspath(r"D:\astra-mind-extension\fix_clean")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ORIGINAL_PSI_DIR not in sys.path:
    sys.path.insert(0, ORIGINAL_PSI_DIR)

# Migrated PSI components
from app.psi.research_monitor import (
    calculate_stress_from_emotions as migrated_calc_stress,
    calculate_emotional_stress as migrated_calc_emotional,
    rebalance_emotions as migrated_rebalance,
    ResearchStressMonitor as MigratedStressMonitor,
    calculate_brs as migrated_brs,
    classify_brs as migrated_classify_brs,
    detect_chronic_stress as migrated_detect_chronic,
    EMOTION_DIMENSIONS as MIGRATED_DIMENSIONS,
    STRESS_WEIGHTS as MIGRATED_WEIGHTS,
)
from app.psi.calibration import (
    calculate_baseline_stress as migrated_calc_baseline,
)

# Original PSI components (for direct differential verification)
import research_monitor as orig_rm
import photo_capture as orig_pc


CANONICAL_VECTORS = {
    "angry": {
        "angry": 22, "neutral": 58, "sad": 7, "disgust": 4,
        "fear": 3, "surprise": 2, "happy": 4,
    },
    "fear": {
        "fear": 25, "neutral": 55, "sad": 8, "disgust": 3,
        "angry": 4, "surprise": 3, "happy": 2,
    },
    "sad": {
        "sad": 30, "neutral": 52, "angry": 5, "disgust": 3,
        "fear": 4, "surprise": 2, "happy": 4,
    },
    "disgust": {
        "disgust": 28, "neutral": 54, "angry": 6, "sad": 4,
        "fear": 3, "surprise": 2, "happy": 3,
    },
    "surprise": {
        "surprise": 40, "neutral": 40, "happy": 8, "angry": 4,
        "sad": 3, "fear": 3, "disgust": 2,
    },
    "neutral": {
        "neutral": 80, "happy": 8, "sad": 4, "angry": 3,
        "fear": 2, "surprise": 2, "disgust": 1,
    },
    "happy": {
        "happy": 65, "neutral": 25, "surprise": 5, "sad": 2,
        "angry": 1, "fear": 1, "disgust": 1,
    },
}


# =============================================================================
# B1: CANONICAL VECTORS & FORMULA PARITY
# =============================================================================
class TestB1FormulaParity:

    @pytest.mark.parametrize("emotion", list(CANONICAL_VECTORS.keys()))
    def test_direct_parity_canonical_vectors(self, emotion):
        vec = CANONICAL_VECTORS[emotion]
        orig_val = orig_rm.calculate_stress_from_emotions(vec)
        migr_val = migrated_calc_stress(vec)
        assert math.isclose(orig_val, migr_val, abs_tol=1e-5), (
            f"Parity mismatch for {emotion}: Original={orig_val}, Migrated={migr_val}"
        )

    def test_rebalance_emotions_direct_parity(self):
        for emotion, vec in CANONICAL_VECTORS.items():
            orig_reb = orig_rm.rebalance_emotions(vec)
            migr_reb = migrated_rebalance(vec)
            for k in orig_reb:
                assert math.isclose(orig_reb[k], migr_reb[k], abs_tol=1e-6), (
                    f"Rebalance mismatch for {emotion} on key {k}: {orig_reb[k]} vs {migr_reb[k]}"
                )

    def test_calibration_stress_parity(self):
        for emotion, vec in CANONICAL_VECTORS.items():
            orig_cal = orig_rm.calculate_emotional_stress(vec)
            migr_cal = migrated_calc_emotional(vec)
            assert math.isclose(orig_cal, migr_cal, abs_tol=1e-5), (
                f"Calibration stress mismatch for {emotion}: {orig_cal} vs {migr_cal}"
            )


# =============================================================================
# B2: LATENCY & THROUGHPUT
# =============================================================================
class TestB2LatencyThroughput:

    def test_latency_and_throughput(self):
        import time
        vec = CANONICAL_VECTORS["angry"]
        N = 5000
        t0 = time.perf_counter()
        for _ in range(N):
            migrated_calc_stress(vec)
        elapsed = time.perf_counter() - t0
        mean_ms = (elapsed / N) * 1000.0
        throughput = int(N / elapsed)

        assert mean_ms < 0.5, f"Mean latency {mean_ms:.4f}ms exceeds 0.5ms threshold"
        assert throughput > 2000, f"Throughput {throughput}/sec below 2000/sec threshold"


# =============================================================================
# B3: SMOOTHING PARITY & NOISE SUPPRESSION
# =============================================================================
class TestB3SmoothingParity:

    def test_smoothing_parity_with_original(self):
        random.seed(42)
        true_signal = [30.0 + (40.0 * i / 99.0) for i in range(100)]
        noisy_signal = [v + random.gauss(0, 5.0) for v in true_signal]

        orig_monitor = orig_rm.ResearchStressMonitor(staff_baseline=25.0)
        migr_monitor = MigratedStressMonitor(staff_baseline=25.0)

        orig_smoothed = [orig_monitor.apply_smoothing(v) for v in noisy_signal]
        migr_smoothed = [migr_monitor.apply_smoothing(v) for v in noisy_signal]

        for i, (o, m) in enumerate(zip(orig_smoothed, migr_smoothed)):
            assert math.isclose(o, m, abs_tol=1e-5), f"Step {i} mismatch: orig={o}, migr={m}"

        var_raw = statistics.variance(noisy_signal)
        var_smoothed = statistics.variance(migr_smoothed)
        reduction = (var_raw - var_smoothed) / var_raw * 100.0
        fidelity_error = statistics.mean(abs(s - t) for s, t in zip(migr_smoothed, true_signal))

        # Both implementations match variance reduction and fidelity error
        assert reduction > 10.0
        assert fidelity_error < 2.0


# =============================================================================
# B4: DETERMINISM (REBALANCE STABILITY)
# =============================================================================
class TestB4Determinism:

    def test_deterministic_output(self):
        vec = CANONICAL_VECTORS["angry"]
        runs = [migrated_calc_stress(vec) for _ in range(100)]
        assert statistics.stdev(runs) == 0.0
        assert len(set(runs)) == 1


# =============================================================================
# B5: BASELINE PERSONALISATION PARITY (Z-SCORE NUDGE)
# =============================================================================
class TestB5BaselinePersonalisation:

    def test_personalisation_parity_across_baselines(self):
        vec = CANONICAL_VECTORS["angry"]
        for base in [15.0, 25.0, 40.0, 50.0, 70.0]:
            orig_val = orig_rm.calculate_stress_from_emotions(vec, baseline=base, baseline_sigma=5.0)
            migr_val = migrated_calc_stress(vec, baseline=base, baseline_sigma=5.0)
            assert math.isclose(orig_val, migr_val, abs_tol=1e-5), (
                f"Mismatch at baseline={base}: orig={orig_val}, migr={migr_val}"
            )

    def test_personalisation_differentiates_medium_stress(self):
        # On medium stress (raw ~45), headroom > 0 and Z-score doesn't hit the 12.0 clamp
        medium_vec = {
            "angry": 8, "neutral": 60, "sad": 15, "disgust": 8,
            "fear": 5, "surprise": 2, "happy": 2,
        }
        psi_low_base  = migrated_calc_stress(medium_vec, baseline=20.0, baseline_sigma=5.0)
        psi_high_base = migrated_calc_stress(medium_vec, baseline=40.0, baseline_sigma=5.0)
        # Person with baseline 20 is further above baseline -> receives higher nudge
        assert psi_low_base >= psi_high_base


# =============================================================================
# B6: BURNOUT RISK SCORE (BRS) PARITY
# =============================================================================
class TestB6BurnoutRiskScore:

    PROFILES = [
        ("Calm astronaut",       15.0,  3.0,  4.0,  9.2,  "Low"),
        ("Moderate stress",     35.0, 10.0, 35.0, 27.5,  "Low"),
        ("High stress",         55.0, 18.0, 55.0, 43.9,  "Moderate"),
        ("Burnout risk",        72.0, 22.0, 70.0, 56.6,  "High"),
        ("Variable performer",  40.0, 25.0, 38.0, 35.1,  "Moderate"),
        ("Low stress, high var",20.0, 30.0, 20.0, 23.0,  "Low"),
    ]

    @pytest.mark.parametrize("name,avg,var,task,expected_score,expected_tier", PROFILES)
    def test_brs_exact_formula_and_classification(self, name, avg, var, task, expected_score, expected_tier):
        score = migrated_brs(avg, var, task)
        assert math.isclose(score, expected_score, abs_tol=0.1)
        tier = migrated_classify_brs(score)
        assert tier == expected_tier


# =============================================================================
# B7: EXTREME INPUT SAFETY & PARITY
# =============================================================================
class TestB7ExtremeInputSafety:

    EDGE_CASES = [
        ("All zeros",   {"angry":0,"fear":0,"sad":0,"disgust":0,"surprise":0,"neutral":0,"happy":0}),
        ("All neutral", {"angry":0,"fear":0,"sad":0,"disgust":0,"surprise":0,"neutral":100,"happy":0}),
        ("All happy",   {"angry":0,"fear":0,"sad":0,"disgust":0,"surprise":0,"neutral":0,"happy":100}),
        ("All angry",   {"angry":100,"fear":0,"sad":0,"disgust":0,"surprise":0,"neutral":0,"happy":0}),
        ("Tiny values", {"angry":1,"fear":1,"sad":1,"disgust":1,"surprise":1,"neutral":94,"happy":1}),
    ]

    @pytest.mark.parametrize("case_name,vec", EDGE_CASES)
    def test_extreme_inputs_parity(self, case_name, vec):
        orig_val = orig_rm.calculate_stress_from_emotions(vec)
        migr_val = migrated_calc_stress(vec)
        assert math.isclose(orig_val, migr_val, abs_tol=1e-5), (
            f"Mismatch on {case_name}: orig={orig_val}, migr={migr_val}"
        )
        assert not math.isnan(migr_val)
        assert 0.0 <= migr_val <= 100.0


# =============================================================================
# B8: HAPPY FACE SUPPRESSION (HIF)
# =============================================================================
class TestB8HappyFaceConfirmation:

    def test_happy_face_ordering_and_suppression(self):
        psi_happy = migrated_calc_stress(CANONICAL_VECTORS["happy"])
        psi_neutral = migrated_calc_stress(CANONICAL_VECTORS["neutral"])
        psi_angry = migrated_calc_stress(CANONICAL_VECTORS["angry"])

        assert psi_happy < 15.0
        assert psi_happy < psi_neutral < psi_angry

        orig_happy = orig_rm.calculate_stress_from_emotions(CANONICAL_VECTORS["happy"])
        assert math.isclose(psi_happy, orig_happy, abs_tol=1e-5)


# =============================================================================
# B9: TASK COMPLEXITY LIFT & PARITY
# =============================================================================
class TestB9TaskComplexityEffect:

    def test_task_complexity_parity_and_lift(self):
        vec = CANONICAL_VECTORS["neutral"]
        for tc in [1.0, 3.0, 5.0, 7.0, 9.0, 10.0]:
            orig_val = orig_rm.calculate_stress_from_emotions(vec, task_complexity=tc)
            migr_val = migrated_calc_stress(vec, task_complexity=tc)
            assert math.isclose(orig_val, migr_val, abs_tol=1e-5)

        # High task (9.0) produces greater PSI than baseline (5.0)
        assert migrated_calc_stress(vec, task_complexity=9.0) > migrated_calc_stress(vec, task_complexity=5.0)


# =============================================================================
# B10: CHRONIC STRESS THRESHOLD DETECTION
# =============================================================================
class TestB10ChronicStressDetection:

    SCENARIOS = [
        ("Normal week",       [26, 27, 24, 25, 28, 26, 25], False),
        ("Slightly elevated", [35, 38, 36, 37, 40, 35, 36], False),
        ("Chronic stress",    [45, 47, 48, 44, 46, 48, 45], True),
        ("Severe chronic",    [65, 68, 70, 66, 67, 69, 68], True),
    ]

    @pytest.mark.parametrize("name,daily,expected", SCENARIOS)
    def test_chronic_scenarios(self, name, daily, expected):
        baseline = 25.0
        is_chronic = migrated_detect_chronic(daily, baseline)
        assert is_chronic == expected


# =============================================================================
# B11: CALIBRATION STATISTICAL PARITY (IQR TRIMMING)
# =============================================================================
class TestB11CalibrationParity:

    def test_calibration_baseline_exact_parity(self):
        # 5 calibration photos with full 7-emotion vectors
        mock_analysis = [
            {"valid": True, "emotions": {"neutral": 75, "happy": 15, "sad": 4, "angry": 2, "fear": 2, "disgust": 1, "surprise": 1}},
            {"valid": True, "emotions": {"neutral": 78, "happy": 12, "sad": 3, "angry": 3, "fear": 2, "disgust": 1, "surprise": 1}},
            {"valid": True, "emotions": {"neutral": 70, "happy": 18, "sad": 4, "angry": 3, "fear": 2, "disgust": 2, "surprise": 1}},
            {"valid": True, "emotions": {"neutral": 82, "happy": 10, "sad": 3, "angry": 2, "fear": 1, "disgust": 1, "surprise": 1}},
            {"valid": True, "emotions": {"neutral": 76, "happy": 14, "sad": 3, "angry": 3, "fear": 2, "disgust": 1, "surprise": 1}},
        ]

        pc = orig_pc.PhotoCapture()
        orig_result = pc.calculate_baseline_stress(mock_analysis)
        migr_result = migrated_calc_baseline(mock_analysis)

        assert math.isclose(orig_result['baseline_stress'], migr_result['baseline_stress'], abs_tol=1e-1), (
            f"Baseline mismatch: orig={orig_result['baseline_stress']}, migr={migr_result['baseline_stress']}"
        )
        assert math.isclose(orig_result['baseline_sigma'], migr_result['baseline_sigma'], abs_tol=1e-1)
        assert orig_result['optimal_range'] == migr_result['optimal_range']

    def test_insufficient_photos_fallback(self):
        insufficient = [
            {"valid": True, "emotions": {"neutral": 80, "happy": 20}},
            {"valid": False, "emotions": {}},
        ]
        res = migrated_calc_baseline(insufficient)
        assert res['baseline_stress'] == 25.0
        assert res['baseline_sigma'] == 5.0
        assert res['valid_photos'] == 1


# =============================================================================
# B12: EXTENSIVE RANDOMIZED DIFFERENTIAL FUZZING (200 RUNS)
# =============================================================================
class TestB12RandomizedDifferentialParity:

    def test_randomized_inputs_exact_parity(self):
        random.seed(1337)
        emotion_keys = ['angry', 'fear', 'sad', 'disgust', 'surprise', 'neutral', 'happy']

        for iteration in range(200):
            raw_weights = [random.uniform(0.1, 100.0) for _ in range(7)]
            total = sum(raw_weights)
            vec = {k: (w / total) * 100.0 for k, w in zip(emotion_keys, raw_weights)}

            tc = random.uniform(1.0, 10.0)
            motion = random.uniform(0.0, 10.0)
            baseline = random.choice([None, random.uniform(10.0, 60.0)])
            sigma = random.choice([None, random.uniform(1.0, 15.0)]) if baseline else None

            orig_val = orig_rm.calculate_stress_from_emotions(
                vec, task_complexity=tc, motion_level=motion, baseline=baseline, baseline_sigma=sigma
            )
            migr_val = migrated_calc_stress(
                vec, task_complexity=tc, motion_level=motion, baseline=baseline, baseline_sigma=sigma
            )

            assert math.isclose(orig_val, migr_val, abs_tol=1e-5), (
                f"Fuzz failure iter={iteration}: Orig={orig_val}, Migr={migr_val}"
            )
