# Thermal Face Analysis

Tooling for working with FLIR thermal face recordings.

## seq-conversion

Convert FLIR ResearchIR `.seq` recordings to:

- **`.mat`** — lossless raw 16-bit signal **and** temperature in °C
- **`.wmv`** — colour-mapped preview video

…without FLIR / ResearchIR software. Temperatures are reproduced from the
camera's embedded calibration using the standard FLIR radiometric equation, and
have been **verified against FLIR-software output to ~1×10⁻⁵ °C**.

→ See **[`seq-conversion/`](seq-conversion/)** for installation, usage, options,
and the full accuracy discussion.
