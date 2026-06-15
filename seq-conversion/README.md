# seq-conversion — FLIR `.seq` → `.mat` / `.wmv`

Data-preparation stage of the thermal-face-analysis pipeline. Converts raw FLIR
ResearchIR `.seq` thermal recordings into:

- **`.mat`** — lossless raw signal **and** temperature in °C, ready for the
  `alignment/` and `landmark-detection/` MATLAB code
- **`.wmv`** — a quick colour-mapped video preview

No FLIR / ResearchIR software required. Temperatures are reproduced from the
camera's own calibration constants (stored inside the `.seq`) using the standard
FLIR radiometric equation, and have been **verified against FLIR-software output
to ~1×10⁻⁵ °C** (see [Accuracy](#accuracy)).

Developed and verified on a **FLIR A655sc** (640×480); the code reads the
resolution and calibration from each file, so other FLIR models should work too.

---

## Files

| File | Purpose |
|------|---------|
| `flir_seq.py`   | Core reader: frame parsing, raw extraction, radiometric model (shared library) |
| `seq_to_mat.py` | Batch `.seq` → `.mat` |
| `seq_to_wmv.py` | Batch `.seq` → `.wmv` |

---

## Install

1. **Python 3.9+** and the Python packages:

   ```bash
   pip install -r requirements.txt
   ```

2. **ExifTool** (used to read the embedded calibration constants):
   - Download from <https://exiftool.org> and put `exiftool` on your `PATH`
     (on Windows, rename `exiftool(-k).exe` → `exiftool.exe`).
   - Or set an environment variable `EXIFTOOL` to the full path of the executable.

   FFmpeg is **not** needed separately — it ships with the `imageio-ffmpeg` package.

---

## Usage

`INPUT` can be a **single `.seq` file** or a **folder** (every `*.seq` inside is converted).

### Convert to `.mat`

```bash
# one file, output next to it
python seq_to_mat.py path/to/260318_01.seq

# whole folder, into a chosen output directory
python seq_to_mat.py  D:\research\seqs  -o  D:\research\mat
```

| Flag | Effect |
|------|--------|
| `-o OUTDIR`     | write `.mat` files here (default: beside each `.seq`) |
| `--no-raw`      | don't store the raw 16-bit signal |
| `--no-temp`     | don't store the temperature array |
| `--float64`     | store temperature as `double` (default `single`) |
| `--no-compress` | write uncompressed `.mat` (faster, much larger) |

### Convert to `.wmv`

```bash
python seq_to_wmv.py  D:\research\seqs  -o  D:\research\video  --fps 30 --cmap inferno
```

| Flag | Effect |
|------|--------|
| `-o OUTDIR`    | output folder (default: beside each `.seq`) |
| `--fps F`      | playback frame rate (default `30`) |
| `--cmap NAME`  | colour map: `inferno` (default), `jet`, `hot`, `gray`, `viridis`, … |
| `--tmin T` / `--tmax T` | fix the colour scale (°C); default = per-clip min/max |
| `--bitrate B`  | video bitrate (default `4000k`) |

---

## Output `.mat` format

One file per clip. In MATLAB, `data(:,:,k)` is frame *k*:

| Variable | Type | Shape | Meaning |
|----------|------|-------|---------|
| `temperature_C` | single (or double) | `H × W × N` | temperature in °C |
| `raw_counts`    | uint16 | `H × W × N` | **lossless** 16-bit detector signal |
| `calibration`   | struct | — | Planck constants + object & atmospheric parameters |
| `info`          | struct | — | camera, lens, serial, frame rate, date, etc. |

```matlab
m = load('260318_01.mat');
imagesc(m.temperature_C(:,:,1)); colorbar; axis image   % first frame, °C
```

```python
from scipy.io import loadmat
m = loadmat('260318_01.mat')
T = m['temperature_C']          # (H, W, N)
```

---

## Accuracy

### Raw signal — bit-exact

`raw_counts` is the camera's 16-bit detector reading copied verbatim from the
file. It is **lossless** and has been checked byte-for-byte against ExifTool's
decode of the embedded image. It does not depend on any parameter, so you can
always recompute temperature later with different settings.

### Temperature — matches FLIR software to ~10⁻⁵ °C

Temperature is computed with the standard FLIR radiometric equation

```
T = B / ln( R1 / (R2·(S_obj + O)) + F ) − 273.15
S_obj = S/(ε·τ) − (1−ε)/ε·S_refl − (1−τ)/(ε·τ)·S_atm
```

using the Planck constants (`R1, R2, B, F, O`) and object parameters
(emissivity, reflected/atmospheric temperature, distance, humidity) **stored in
the `.seq` itself** — i.e. exactly the numbers FLIR's own software uses.

**Verification:** a full 632-frame clip was converted and compared to the same
clip exported by FLIR software (`Frame0…Frame631`, `double`):

```
global max |ΔT| = 0.00001 °C  over all 632 frames
```

That residual is just floating-point rounding — the two are effectively
identical.

### The small influences (and why they don't matter)

1. **`single` vs `double` storage.** Temperature is stored as `single` (float32)
   by default to halve file size. The rounding this adds is **< 0.001 °C**, far
   below the camera's noise floor (NETD ≈ 0.05 °C). Use `--float64` for an exact
   `double` copy if you prefer.

2. **Atmospheric model.** We use the FLIR-standard **single path** with
   `√(ObjectDistance)`. The popular R *Thermimage* package uses a two-half
   `√(OD/2)` variant; on our data that introduces a **~0.02–0.04 °C** bias, so we
   deliberately do **not** use it. (At 1 m the atmospheric transmission is
   τ ≈ 0.994, so this correction is tiny anyway.)

3. **Object parameters are whatever was set at capture.** Emissivity, reflected
   temperature, distance and humidity are read from the recording. If any were
   set incorrectly when filming, the temperature inherits that error — **but so
   would FLIR's software.** Because `raw_counts` is stored too, you can recompute
   corrected temperatures at any time.

### Why the `.mat` is so much smaller than FLIR's

FLIR software exports every frame as a **separate `double` variable**
(`Frame0`, `Frame1`, …) plus per-frame metadata, **uncompressed** — easily
several GB. This tool stores the data as compressed 3-D arrays (`single`
temperature + `uint16` raw), typically **~0.5 GB** for the same clip, with
**identical** numbers.

---

## ⚠️ A note on `.wmv` playback speed

The video plays every frame at a **constant fps** and does **not** reproduce the
real acquisition timing. FLIR cameras often record at a **variable rate** — e.g.
a short high-speed burst followed by a slow time-lapse (one frame every couple of
seconds). A constant-fps video of such a clip will look sped up. The `.wmv` is a
**visual preview only**; for any quantitative work use the `.mat`.
