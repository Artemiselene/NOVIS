# Extension database schema

## Core Extension Tables
- `mission_environments`: mission environment metadata; `mission_id` references host-owned mission identifiers.
- `body_systems`: explanatory metadata for body systems (including `brain`, `heart`, `lungs`, `muscles`, `digestive`, `sleep`).
- `health_routines`: scheduled astronaut/mission activities.
- `routine_completions`: completion events.
- `health_challenges`: participation-based challenge definitions.
- `astronaut_achievements`: earned participation achievements; `astronaut_id` references host-owned astronaut identifiers.
- `health_education`: plain-language measurement explanations.

## PSI Behavioral Health Intelligence Tables

### 1. `astronaut_psi_baselines`
Stores personalized resting stress baseline parameters derived from voluntary 5-pose photo calibration.
- `id` (INTEGER, Primary Key): Surrogate record identifier.
- `astronaut_id` (INTEGER, Unique, Indexed, NOT NULL): External host-owned astronaut reference. Enforces 1-to-1 baseline mapping per astronaut.
- `is_calibrated` (BOOLEAN, default False): Flag indicating whether the astronaut completed valid baseline calibration.
- `baseline_stress` (FLOAT, default 25.0): Resting baseline stress $\mu$ computed via IQR-trimmed mean.
- `baseline_sigma` (FLOAT, default 5.0): Personal emotional variability $\sigma$ (enforces safe floor $\ge 2.0$).
- `optimal_range_low` (FLOAT, default 15.0): Lower bound of optimal functioning zone ($\mu - 0.8\sigma$).
- `optimal_range_high` (FLOAT, default 35.0): Upper bound of optimal functioning zone ($\mu + 1.5\sigma$).
- `natural_angry` (FLOAT, default 0.0): Median resting anger percentage during calibration (used for expressiveness compensation).
- `natural_sad` (FLOAT, default 0.0): Median resting sadness percentage during calibration.
- `natural_fear` (FLOAT, default 0.0): Median resting fear percentage during calibration.
- `stress_threshold` (FLOAT, default 70.0): Acute stress alert threshold.
- `calibrated_at` (DATETIME with timezone, nullable): Timestamp of calibration completion.
- `created_at` (DATETIME with timezone, default UTC now): Record creation timestamp.
- `updated_at` (DATETIME with timezone, default UTC now): Record modification timestamp.
- **Relationships:**
  - `readings`: 1-to-many relationship with `PsiStressReading`.
  - `calibration_records`: 1-to-many relationship with `PsiCalibrationMetadata` (`cascade="all, delete-orphan"`).

### 2. `psi_stress_readings`
Continuous time-series records of stress monitoring measurements evaluated from video frames or telemetry streams.
- `id` (INTEGER, Primary Key): Unique reading identifier.
- `baseline_id` (INTEGER, ForeignKey to `astronaut_psi_baselines.id`, `ondelete="SET NULL"`, Indexed, Nullable): Associated baseline configuration. Preserves telemetry history if baseline is reset.
- `astronaut_id` (INTEGER, Indexed, NOT NULL): External host-owned astronaut identifier.
- `mission_id` (INTEGER, Indexed, Nullable): External host-owned mission identifier.
- `raw_stress` (FLOAT, NOT NULL): Instantaneous un-smoothed PSI score $[0.0, 100.0]$.
- `smoothed_stress` (FLOAT, NOT NULL): Rolling window smoothed PSI score $[0.0, 100.0]$.
- `stress_deviation` (FLOAT, default 0.0): Deviation from personal baseline ($\text{smoothed\_stress} - \mu$).
- `stress_trend` (VARCHAR(20), default "stable"): Directional trend indicator ("rising", "falling", "stable").
- `dominant_emotion` (VARCHAR(20), NOT NULL): Emotion category with the highest probability.
- `emotion_vector` (JSON, NOT NULL): Full 7-dimensional normalized emotion probability distribution.
- `motion_level` (FLOAT, default 0.0): Physical motion score $[0.0, 10.0]$ derived from frame differencing.
- `motion_detected` (BOOLEAN, default False): Flag indicating significant physical movement.
- `mission_phase` (VARCHAR(60), default "nominal_operations"): Operational context (e.g. transit, EVA, rest).
- `task_complexity` (FLOAT, default 5.0): Task difficulty scale $[1.0, 10.0]$ (neutral default = 5.0).
- `environmental_factor` (FLOAT, default 1.0): Environmental multiplier.
- `risk_level` (VARCHAR(20), default "low"): Evaluated stress risk tier ("low", "warning", "elevated", "high").
- `created_at` (DATETIME with timezone, default UTC now, Indexed): Measurement timestamp.
- **Relationships:**
  - `baseline`: Many-to-1 relationship with `AstronautPsiBaseline`.

### 3. `psi_calibration_metadata`
Pose-by-pose statistical metadata from the 5-photo calibration sequence. **Does NOT store personal photographs or raw biometric images**; records only derived affective scores.
- `id` (INTEGER, Primary Key): Unique record identifier.
- `baseline_id` (INTEGER, ForeignKey to `astronaut_psi_baselines.id`, `ondelete="CASCADE"`, Indexed, NOT NULL): Owning baseline identifier.
- `astronaut_id` (INTEGER, Indexed, NOT NULL): External host-owned astronaut identifier.
- `pose_name` (VARCHAR(32), NOT NULL): Calibration pose label (e.g. "neutral", "left", "right", "smile").
- `photo_number` (INTEGER, NOT NULL): Sequence index ($1$ to $5$).
- `is_valid` (BOOLEAN, default True): Whether the face was successfully detected and analyzed.
- `dominant_emotion` (VARCHAR(32), Nullable): Dominant emotion classified for this pose.
- `emotions_json` (JSON, default empty dict): Full emotion vector for this calibration pose.
- `calculated_stress` (FLOAT, Nullable): Resting emotional stress score computed for this pose.
- `created_at` (DATETIME with timezone, default UTC now): Calibration capture timestamp.
- **Relationships:**
  - `baseline`: Many-to-1 relationship with `AstronautPsiBaseline`.

---

## Architectural & Privacy Notes
1. **Isolation by Astronaut ID:** All queries, history retrievals, and analytics calculations are scoped to `astronaut_id` to guarantee astronaut baseline privacy.
2. **Telemetry Preservation:** Historical readings retain `mission_id` and timestamps even if a baseline is re-calibrated.
3. **No Biometric Storage:** In-memory decoding ensures facial photographs remain transient; only numerical affect vectors and statistical baselines are persisted.
