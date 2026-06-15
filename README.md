# Thermal Face Analysis

Research on pixel-based facial thermal image analysis for emotion sensing.

## Components

The pipeline runs in order: raw camera recordings → temperature data → alignment → landmarks.

- **`seq-conversion/`** — Data preparation: convert FLIR `.seq` recordings to
  `.mat` (lossless raw + temperature in °C) and `.wmv` previews, without FLIR
  software. Verified against FLIR-software output to ~1×10⁻⁵ °C.
- **`alignment/`** — Development of pixel-based facial thermal image alignment
  (originally `Thermal-facial-alignment`)
- **`landmark-detection/`** — Landmark detection for thermal facial images, MATLAB
  (originally `Thermal_face_Landmark_detection`)

The `alignment/` and `landmark-detection/` components keep their full original
commit history (merged via git subtree).
