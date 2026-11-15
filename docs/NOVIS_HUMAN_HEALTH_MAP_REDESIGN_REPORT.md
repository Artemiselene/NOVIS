# NOVIS — Human Health Map Redesign Report
## Neural Onboard Vitality & Intelligence System (NOVIS v3.2)

**Date:** 2026-11-15  
**Platform:** NOVIS — Neural Onboard Vitality & Intelligence System  
**Tagline:** *Intelligent Crew Health. Adaptive Mission Readiness.*  
**Project Root:** `D:\astra-mind-extension\astra-mind-extension`  
**Frontend Build Status:** **SUCCESS** (`vite build` compiled in 549ms, 0 errors, 0 warnings)  
**Backend Test Status:** **120 passed, 0 failed** (100% pass rate in 2.32s)  
**Deliverable Status:** Production-Ready Two-Column Interactive Anatomical Scanner & Health Intelligence Console.

---

## 1. Executive Summary

This release completely overhauls the **Human Health Map** page within the NOVIS platform, elevating it from a basic silhouette display into a high-grade aerospace medical intelligence and interactive anatomical scanner console matching the supplied NOVIS design specifications.

Key enhancements delivered:
1. **Two-Column Mission Operations Layout:**
   - **Left Panel:** Dark navy **NOVIS Anatomical Scanner Viewport** featuring a medical HUD, technical grid matrix, animated cyan scanning beam, concentric radar rings, vertical caliper measurement marks, coordinate tracking lines, and full anterior (front) / dorsal (back) anatomical projections.
   - **Right Panel:** Medical-grade **Health Intelligence Console** delivering connected sensor hardware telemetry, four system-specific metric tiles, a 24-hour historical telemetry profile with SVG sparkline and time axis, biological functional architecture, monitored biomarker chips (distinguishing active sensor streams from non-invasive proxies or unavailable adapters), and flight surgeon guidance.
2. **Interactive Anterior (Front) & Dorsal (Back) Projections:**
   - Anterior view displays detailed frontal cranium/cortex, bilateral lungs with bronchial tree, myocardium with aortic arch and SA node pulse, pectoral and rectus abdominis muscle segments, gastric curvature, and small intestine convolutions.
   - Dorsal view renders occipital cranium, cerebellar hemispheres, the complete vertebral column (Spine C1-L5 + Sacrum with intervertebral discs and radiating spinal roots), bilateral scapulae, trapezius and latissimus dorsi back muscles, gluteus maximus, hamstrings, posterior lung bases, descending thoracic aorta, and dorsal sympathetic/parasympathetic ganglionic chain nodes.
3. **Six Interactive Body Systems:**
   - **Brain & Nervous System:** Connected to Optical Affect Camera & Neural Telemetry, tracking Psychological Stress Index (PSI), Burnout Risk Score (BRS), Dominant Affect, and Personal Baseline.
   - **Cardiovascular System:** Connected to Continuous Optical PPG & Wearable Bio-Harness, tracking Heart Rate, Resting HR Baseline, Autonomic Stress Deviation, and Data Stream Mode.
   - **Respiratory System:** Connected to Continuous Pulse Oximeter & Thoracic Piezo Bands, tracking SpO2, Respiration Rate, Ventilation Efficiency, and Spacecraft Cabin pO2.
   - **Musculoskeletal System:** Connected to Tri-Axial IMU & Activity Telemetry, tracking Physical Exertion, Operational Workload, VO2 Max, and Countermeasure Compliance.
   - **Digestive & Metabolic Core:** Connected to Core Body Temperature Probe & Crew Medical Log, tracking Core Temperature, Hydration Equilibrium, Metabolic Stability, and GI Tolerance.
   - **Sleep & Circadian Recovery:** Connected to Actigraphy & Sleep Pod Bio-Station, tracking Sleep Duration, Sleep Quality Index, Readiness/Recovery Score, and Circadian Phase Alignment.
4. **Data Integrity & Telemetry Discipline:**
   - Real data is strictly pulled from the active astronaut's database records and live streams (`/dashboard/astronaut/{id}`, `/telemetry/astronaut/{id}/history`, `/psi/readings/{id}/history`).
   - If historical logs are absent, the interface explicitly displays `"NO LOGGED SAMPLES"` and avoids fabricating artificial curves.
   - Unavailable diagnostic measurements (e.g. direct multi-channel EEG, 12-lead Holter, DEXA) are clearly tagged as `[DEMO MODEL PROXY]` or `[UNAVAILABLE]`, ensuring clear distinction between live sensor streams and non-diagnostic proxies.

---

## 2. Interface Architecture & Component Design

### 2.1 Top Aerospace Status & Astronaut Selector Bar

Located at the top of the Human Health Map view, the navigation header provides instant situational awareness across crew readiness:
- **Eyebrow & Page Title:** `NOVIS / MISSION OPERATIONS // Human Health Map`
- **Live Telemetry Pill:** Real-time pulsing green indicator showing `LIVE TELEMETRY // CONNECTED` (driven by active WebSocket status `wsStatus === "open"`).
- **Target Astronaut Selector:** Dropdown listing active crew members with ID, name, callsign, and mission role.
- **Active Crew Status Badge:** Visual tag (`ACTIVE`, `TRAINING`, `RESTING`) reflecting operational status.
- **User Role Badge:** Verified demonstration persona badge (e.g. `FLIGHT SURGEON`, `ASTRONAUT`, `MISSION DIRECTOR`).
- **Data Stream Mode Badge:** Distinct visual indicator for `ANALOG STREAM` (simulated telemetry bus) vs `HARDWARE LINK` (physical biosensors).
- **System Quick-Filter Pills:** Six quick navigation pills with icons and live status indicators for one-click system switching.

### 2.2 Left Panel: NOVIS Anatomical Scanner

Built as a dedicated dark-navy aerospace medical scanner viewport (`.anatomy-viewport`):
- **Background Matrix & Radar:** Layered SVG background pattern (`#techGrid`), concentric range circles (`r=150`, `r=90`, `r=44`), and subtle blue ambient illumination (`radial-gradient`).
- **Animated Cyan Scanning Beam:** CSS-animated scanning bar (`.scanner-scanline` with `@keyframes scanline-sweep`) continuously moving down and up across the anatomical figure with a soft cyan drop-shadow.
- **HUD Caliper Markings:** Lateral millimeter caliper scale with labeled aerospace anatomical divisions (`CRANIAL`, `THORACIC`, `ABDOMINAL`, `PELVIC`, `FEMORAL`).
- **Anterior / Dorsal View Toggle:** Segmented button control allowing instant projection switching between Anterior (Front) and Dorsal (Back) views.
- **Interactive SVG Hotspots:** Clickable anatomical structures with SVG glow filters (`#glowActive`), dashed rotating reticles (`.scanner-spin` and `.scanner-spin-rev`), and coordinate callout lines.
- **HUD Terminal Footer:** Status readouts indicating targeted system name, 3D anatomical coordinates (e.g. `X:190 Y:50 Z:+12`), and sensor link status (`LIVE SENSOR LINKED` vs `STANDBY`).

```
+-------------------------------------------------------------------------+
| NOVIS ANATOMICAL SCANNER // v3.2                    [ANT] [DOR]         |
| ----------------------------------------------------------------------- |
|  CRANIAL   |      [Cerebral Cortex / Cerebellum Reticle]                |
|            |      ------------------------------------ (Cyan Beam)      |
|  THORACIC  |   [Bilateral Lungs]  [Heart / Aorta]                       |
|            |   (Anterior: Bronchia / Dorsal: Spine C1-T12)              |
|  ABDOMINAL |   [Pectorals / Abs / Stomach / Hepatic Core]               |
|            |   (Dorsal: Scapulae / Latissimus / Kidneys)                |
|  PELVIC    |   [Intestinal Loops / Sacrum / Coccyx / Gluteus]           |
|            |                                                            |
|  FEMORAL   |   [Quadriceps Muscle Chains / Hamstrings]                  |
| ----------------------------------------------------------------------- |
| TARGET: BRAIN & CNS     COORDS: X:190 Y:50 Z:+12     LIVE SENSOR LINKED |
+-------------------------------------------------------------------------+
```

### 2.3 Right Panel: Health Intelligence Console

Built with aerospace telemetry styling in `#ffffff` with high-contrast slate borders:
- **System Header:** System icon in colored badge, full system title, Latin biological taxonomy, operational status badge, and data stream indicator.
- **Connected Sensor Hardware Banner:** Card highlighting the active hardware provider (e.g., `Optical Affect Camera & Neural Telemetry`), data protocol (`WebSocket Frame Telemetry + REST`), and sensor classification.
- **Live System Metric Grid:** Four responsive metric tiles displaying large monospace values, metric label, and status indicator dot (Green = Nominal, Yellow = Elevated, Red = Critical, Blue = Informational).
- **24-Hour Telemetry Profile:**
  - Dark navy container (`#090f1f`) matching the scanner aesthetics.
  - Header with current value readout badge and logged sample count.
  - Smooth SVG curve with gradient area fill under the curve and highlighted data points.
  - Formatted time axis: `-24h`, `-18h`, `-12h`, `-6h`, `Now (T-0)`.
  - Fallback view displaying `NO LOGGED SAMPLES` when history is empty.
- **Functional Architecture:** Detailed biological mechanism description based on spaceflight medicine.
- **Monitored Biomarkers & Indicators:** Tagged chips explicitly denoting active hardware streams versus demo proxy models.
- **Flight Surgeon Clinical Protocol:** Notice callout with clinical guidance and non-diagnostic decision-support warnings.
- **Operational Flight Guidance:** Bulleted operational recommendations derived from current vitals.
- **Cross-Workflow Navigation:** Action buttons linking directly to **Astronaut Telemetry** and **Baseline Calibration**.

---

## 3. Body Systems Specification & Telemetry Binding

| System | Key | Connected Hardware | Live Metrics Bound | Biomarkers Shown |
| :--- | :--- | :--- | :--- | :--- |
| **Brain & Nervous System** | `brain` | Optical Affect Camera & Neural Telemetry | PSI (%), Burnout Risk (BRS), Dominant Affect, Personal Baseline | Behavioral PSI, Facial AU Variance, Autonomic Valence, EEG (Demo Proxy) |
| **Cardiovascular System** | `heart` | Astronaut Biomarker PPG Wearable & Bio-Harness | Heart Rate (bpm), Resting HR Baseline, Autonomic Stress Deviation, Stream Mode | Heart Rate, HRV (rMSSD), Sympathetic Tone, Holter ECG (Unavailable) |
| **Respiratory System** | `lungs` | Continuous Pulse Oximeter & Thoracic Bands | SpO2 (%), Respiration Rate (brpm), Ventilation Efficiency, Cabin pO2 | SpO2, Respiration Rate, Alveolar Diffusion, EtCO2 (EVA Only) |
| **Musculoskeletal System** | `muscles` | Tri-Axial IMU & Load Cells | Physical Exertion (0-10), Workload Score (0-10), VO2 Max, Countermeasures | Tri-Axial Exertion, ARED Force Compliance, Surface EMG (Research) |
| **Digestive & Metabolic Core** | `digestive` | Core Temp Sensor & Metabolic Log | Core Temp (°C), Hydration Equilibrium, Metabolic Stability, GI Status | Core Temp (°C), Hydration & Intake, Interstitial Glucose (Offline) |
| **Sleep & Recovery** | `sleep` | Actigraphy & Sleep Pod Station | Sleep Hours (hrs), Sleep Quality (0-100), Recovery Score (0-100), Circadian Phase | REM/NREM Actigraphy, Sleep Debt Accumulator, Circadian Shift Index |

---

## 4. Verification & Validation

### 4.1 Automated Backend Test Suite
Executed the complete test suite against all authentication, mission, astronaut, telemetry, PSI, and security hardening routines:
```powershell
Set-Location D:\astra-mind-extension\astra-mind-extension
& "D:\astra-mind-extension\.venv\Scripts\python.exe" -m pytest backend/tests -q
```
**Result:**
```
........................................................................ [ 60%]
................................................                         [100%]
120 passed in 2.32s
```
All 120 tests passed with 0 errors and 0 warnings.

### 4.2 Frontend Production Build
Compiled client assets via Vite:
```powershell
Set-Location D:\astra-mind-extension\astra-mind-extension\frontend
npm run build
```
**Result:**
```
vite v8.3.8 building client environment for production...
transforming...
✓ 2087 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.72 kB │ gzip:   0.48 kB
dist/assets/index-DzTD3KRm.css   25.49 kB │ gzip:   5.55 kB
dist/assets/index-B-THorZd.js   357.34 kB │ gzip: 103.50 kB

✓ built in 549ms
```
The bundle compiled cleanly with zero errors.

### 4.3 Feature Verification Checklist

- [x] **Two-Column Responsive Grid:** Tested on desktop (480px / 1fr), tablet (420px / 1fr), and mobile (single-column stacked).
- [x] **Anterior (Front) / Dorsal (Back) Projections:** Verified clean SVG rendering and perspective change for skull, spine, ribs, organs, and muscle chains.
- [x] **Six Body Systems:** Verified interactive hotspot clicks, color accents, and reticle highlights across Brain, Cardio, Pulm, Musc, Core, and Sleep.
- [x] **Astronaut Selection:** Switching target crew updates telemetry metrics, baseline info, and historical profiles in real time.
- [x] **Missing Data Handling:** Non-calibrated or unrecorded metrics gracefully display `"--"` or `"NO LOGGED SAMPLES"` without breaking.
- [x] **Aerospace HUD Styling:** Cyan scanning beam, rotating reticles, technical calipers, and status indicators render smoothly.
- [x] **Safety & Constraints Preserved:** Zero changes made to `fix_clean`, PSI formulas preserved, no uncommitted git operations executed.

---

## 5. Conclusion

The redesigned **NOVIS Human Health Map** provides an aerospace-grade anatomical scanner and health intelligence suite that faithfully embodies the reference aesthetic while upholding rigorous engineering standards, complete API integration, and clinical decision-support data clarity.
