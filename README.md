# Thermal Face Analysis

Tooling and data for working with FLIR thermal face/ear recordings.

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
