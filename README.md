# Thermal Face Analysis

Tooling and data for working with FLIR thermal face/ear recordings.

## Working with the temperature data (important)

The calibrated temperature lives in each `.mat` as `temperature_C` (a float °C
array) — **that** is the data. Rendered images (normalized / CLAHE) are only a
*display* used to compute geometry (registration, alignment, "unwrapping"); they
do **not** carry calibrated temperature.

- **Never read temperature back from an image.** Normalization / CLAHE / 8-bit is
  lossy and non-invertible (off by ~1 °C). Keep `temperature_C` as float throughout.
- **Compute geometry on the image, then apply it to the raw `temperature_C`.** A
  registration returns a deformation (where each pixel moves); apply that to the
  float °C with a **single cubic resample**. Interior precision loss is ~0.01 °C
  (measured — see [`tools/interp_precision_check.py`](tools/)); mask the edges.
- **Temperature is intensive — resample only, never Jacobian-modulate.** A point
  keeps the same °C whether the warp locally stretches or compresses it. A
  non-linear warp changes local spatial *resolution*, not the temperature values.
- **Use a diffeomorphic (fold-free) registration** so heavy local compression cannot
  fold the field; report the Jacobian (≈0 negative values) as a sanity check.

## seq-conversion

Convert FLIR ResearchIR `.seq` recordings to:

- **`.mat`** — lossless raw 16-bit signal **and** temperature in °C
- **`.wmv`** — colour-mapped preview video

…without FLIR / ResearchIR software. Temperatures are reproduced from the
camera's embedded calibration using the standard FLIR radiometric equation, and
have been **verified against FLIR-software output to ~1×10⁻⁵ °C**.

→ See **[`seq-conversion/`](seq-conversion/)** for installation, usage, options,
and the full accuracy discussion.

## tools

Diagnostic / QC utilities:

- **`check_seq_fps.py`** — report the effective saved frame rate of a `.seq`
  (frame count, duration, fps, and whether the cadence is uniform or decimated),
  read directly from the embedded per-frame timestamps via ExifTool.
- **`interp_precision_check.py`** — quantify the temperature precision lost when
  resampling `.mat` data. Confirms that applying geometry to the raw `temperature_C`
  (float, single cubic resample) costs only ~0.01 °C in smooth regions; the loss
  concentrates at edges and should be masked.

→ See **[`tools/`](tools/)**.

## dataset

Per-stimulus timing, emotion ratings, and participant info, plus notes on which
segments are excluded and why.

→ See **[`dataset/`](dataset/)** — start with
[`DATA_EXCLUSIONS.md`](dataset/DATA_EXCLUSIONS.md).
