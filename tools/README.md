# tools

Diagnostic, QC, and visualization utilities for the thermal data. These do not
alter the data; they inspect `.seq` / `.mat` files or render frames for viewing.

## check_seq_fps.py
Report the effective **saved** frame rate of a `.seq` — frame count, duration,
fps, and whether the cadence is uniform or decimated — read directly from the
embedded per-frame timestamps.

```bash
python check_seq_fps.py path/to/file.seq
```
Requires ExifTool (set `EXIFTOOL` if it is not on PATH).

## interp_precision_check.py
Quantify the temperature precision lost when **resampling** `.mat` data (the one
interpolation incurred when geometry is applied to the raw temperature). Reports
error in °C split into smooth-interior vs edges, and the 8-bit quantization floor.

```bash
python interp_precision_check.py "path/glob/*.mat" [n_files] [frames_per_file]
```
Requires numpy, scipy. Confirms interior loss ≈ 0.01 °C (mask edges).

## mat_to_image.py
Render `temperature_C` frames to PNG — either an inferno heatmap (for viewing) or
a CLAHE grayscale (the display image fed to registration/landmarking).

```bash
python mat_to_image.py file.mat [frame|mid|all] [out_dir] [raw|clahe]
```
Requires numpy, scipy, matplotlib (+ scikit-image for `clahe`).

> **A PNG is not temperature data.** Quantitative analysis must use the raw
> `temperature_C` (float). Never read temperature back from an image — that loses
> ~0.8 °C because CLAHE is non-linear. Use images only to compute *geometry*
> (where things are), then apply that geometry to the raw °C with a single cubic
> resample. See `interp_precision_check.py`.
