# -*- coding: utf-8 -*-
"""
flir_seq.py  --  Core reader for FLIR ResearchIR `.seq` thermal sequences.

A `.seq` file is a concatenation of FLIR FFF frame records. Each frame stores
the raw 16-bit detector signal (uncompressed) plus an FFF header that carries
the camera's radiometric calibration. This module:

  * locates every frame and the exact pixel-block offset (self-validating),
  * reads the lossless raw 16-bit signal,
  * converts raw signal -> temperature with the standard FLIR radiometric model
    (verified against FLIR/ResearchIR .mat export to ~1e-5 deg C, see README).

External dependency: ExifTool (https://exiftool.org) on PATH, or set $EXIFTOOL,
used to read the embedded calibration constants. Only the first ~0.6 MB frame is
handed to ExifTool, so non-ASCII paths (e.g. Chinese folder names) are handled
by copying that one small frame to a temp file.
"""
import os
import re
import io
import json
import shutil
import subprocess
import tempfile
import numpy as np
from PIL import Image

FFF_MAGIC = b"\x46\x46\x46\x00\x52\x65\x73"   # 'FFF\0Res'


def find_exiftool():
    """Locate the exiftool executable."""
    candidates = [
        os.environ.get("EXIFTOOL"),
        shutil.which("exiftool"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\ExifTool\exiftool.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    if shutil.which("exiftool"):
        return "exiftool"
    raise RuntimeError(
        "ExifTool not found. Install it from https://exiftool.org, put it on "
        "PATH, or set the EXIFTOOL environment variable to the .exe.")


def _num(value):
    """Pull the leading number out of an ExifTool value like '1.00 m' / '20.0 C'."""
    if value is None:
        return None
    m = re.search(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", str(value))
    return float(m.group()) if m else None


class FlirSeq:
    """Lazy reader for one .seq file."""

    def __init__(self, path, exiftool=None, verbose=True):
        self.path = path
        self.verbose = verbose
        self.exiftool = exiftool or find_exiftool()
        with open(path, "rb") as f:
            self._data = f.read()

        # 1. find all FFF frame starts
        starts, i = [], self._data.find(FFF_MAGIC)
        while i != -1:
            starts.append(i)
            i = self._data.find(FFF_MAGIC, i + 1)
        if not starts:
            raise ValueError("No FLIR FFF frames found in %r" % path)
        self.starts = starts
        self.n_frames = len(starts)

        # 2. read calibration + dimensions + frame0 ground truth via ExifTool
        end0 = starts[1] if len(starts) > 1 else len(self._data)
        self._read_meta(self._data[starts[0]:end0])

        # 3. locate pixel blocks (self-validating against ground truth + EOF)
        self._derive_offsets()

        # 4. build the radiometric conversion
        self._make_raw2temp()

    # ------------------------------------------------------------------ meta
    def _run_exiftool(self, frame0_bytes, args):
        tmp = os.path.join(tempfile.gettempdir(), "flirseq_meta.fff")
        with open(tmp, "wb") as f:
            f.write(frame0_bytes)
        return subprocess.run([self.exiftool] + args + [tmp], capture_output=True)

    def _read_meta(self, frame0_bytes):
        out = self._run_exiftool(frame0_bytes, ["-j", "-FLIR:all"]).stdout
        tags = json.loads(out.decode("latin1"))[0]

        def g(k):
            return tags.get(k)

        self.width = int(_num(g("RawThermalImageWidth")))
        self.height = int(_num(g("RawThermalImageHeight")))

        self.calibration = dict(
            PlanckR1=_num(g("PlanckR1")), PlanckR2=_num(g("PlanckR2")),
            PlanckB=_num(g("PlanckB")), PlanckF=_num(g("PlanckF")),
            PlanckO=_num(g("PlanckO")),
            Emissivity=_num(g("Emissivity")),
            ObjectDistance_m=_num(g("ObjectDistance")),
            ReflectedApparentTemperature_C=_num(g("ReflectedApparentTemperature")),
            AtmosphericTemperature_C=_num(g("AtmosphericTemperature")),
            IRWindowTemperature_C=_num(g("IRWindowTemperature")),
            IRWindowTransmission=_num(g("IRWindowTransmission")),
            RelativeHumidity_pct=_num(g("RelativeHumidity")),
            ATA1=_num(g("AtmosphericTransAlpha1")), ATA2=_num(g("AtmosphericTransAlpha2")),
            ATB1=_num(g("AtmosphericTransBeta1")), ATB2=_num(g("AtmosphericTransBeta2")),
            ATX=_num(g("AtmosphericTransX")),
        )
        self.info = dict(
            CameraModel=g("CameraModel") or "",
            CameraPartNumber=g("CameraPartNumber") or "",
            CameraSerialNumber=str(g("CameraSerialNumber") or ""),
            LensModel=g("LensModel") or "",
            FieldOfView=str(g("FieldOfView") or ""),
            FrameRate_Hz=_num(g("FrameRate")) or 0.0,
            DateTimeOriginal=str(g("DateTimeOriginal") or ""),
        )

        # frame0 ground-truth pixels (ExifTool wraps the raw block in a TIFF)
        blob = self._run_exiftool(frame0_bytes, ["-b", "-RawThermalImage"]).stdout
        self._gt0 = np.array(Image.open(io.BytesIO(blob)))

    # --------------------------------------------------------------- offsets
    def _derive_offsets(self):
        W, H = self.width, self.height
        nb = W * H * 2
        gtb = self._gt0.astype("<u2").tobytes()

        end0 = self.starts[1] if self.n_frames > 1 else len(self._data)
        off0 = self._data.find(gtb[:128], self.starts[0], end0)
        if off0 < 0:
            raise ValueError("Could not locate frame-0 pixel block (corrupt file?)")
        self._off0 = off0 - self.starts[0]
        if self._data[off0:off0 + nb] != gtb:
            raise ValueError("Frame-0 pixel block does not match ExifTool ground truth")

        if self.n_frames > 1:
            stride0 = self.starts[1] - self.starts[0]
            stride = (self.starts[2] - self.starts[1]) if self.n_frames > 2 else stride0
            self._offN = self._off0 - (stride0 - stride)
            last_end = self.starts[-1] + self._offN + nb
            if last_end > len(self._data):
                raise ValueError("Derived frame offset overruns end of file")
            if self.verbose and last_end != len(self._data):
                print("  note: %d trailing byte(s) after last frame" %
                      (len(self._data) - last_end))
        else:
            self._offN = self._off0

    def _rel(self, k):
        return self._off0 if k == 0 else self._offN

    # ---------------------------------------------------------- radiometric
    def _make_raw2temp(self):
        c = self.calibration
        E, OD = c["Emissivity"], c["ObjectDistance_m"]
        RTemp, ATemp = c["ReflectedApparentTemperature_C"], c["AtmosphericTemperature_C"]
        IRT, RH = c["IRWindowTransmission"], c["RelativeHumidity_pct"]
        R1, R2, B, F, O = c["PlanckR1"], c["PlanckR2"], c["PlanckB"], c["PlanckF"], c["PlanckO"]
        A1, A2, B1, B2, X = c["ATA1"], c["ATA2"], c["ATB1"], c["ATB2"], c["ATX"]

        def planck_raw(Tc):
            return R1 / (R2 * (np.exp(B / (Tc + 273.15)) - F)) - O

        h2o = (RH / 100.0) * np.exp(1.5587 + 0.06939 * ATemp
                                    - 0.00027816 * ATemp ** 2
                                    + 0.00000068455 * ATemp ** 3)
        s = np.sqrt(OD)                       # single atmospheric path (FLIR standard)
        tau = X * np.exp(-s * (A1 + B1 * np.sqrt(h2o))) \
            + (1 - X) * np.exp(-s * (A2 + B2 * np.sqrt(h2o)))
        c_refl = (1 - E) / E * planck_raw(RTemp)
        c_atm = (1 - tau) / (E * tau) * planck_raw(ATemp)

        if IRT not in (None, 1.0) and self.verbose:
            print("  warning: IRWindowTransmission=%s (window optics not modelled)" % IRT)

        self.tau_atm = float(tau)

        def raw2temp(S):
            raw_obj = S / (E * tau) - c_refl - c_atm
            return B / np.log(R1 / (R2 * (raw_obj + O)) + F) - 273.15

        self.raw2temp = raw2temp

    # -------------------------------------------------------------- reading
    def raw_frame(self, k):
        """Raw 16-bit signal of frame k as (H, W) uint16 (lossless)."""
        off = self.starts[k] + self._rel(k)
        return np.frombuffer(self._data, dtype="<u2",
                             count=self.width * self.height,
                             offset=off).reshape(self.height, self.width)

    def temp_frame(self, k):
        """Temperature of frame k in deg C as (H, W) float."""
        return self.raw2temp(self.raw_frame(k).astype(np.float64))

    def read_all_raw(self):
        out = np.empty((self.height, self.width, self.n_frames), dtype=np.uint16)
        for k in range(self.n_frames):
            out[:, :, k] = self.raw_frame(k)
        return out

    def read_all_temp(self, dtype=np.float32):
        out = np.empty((self.height, self.width, self.n_frames), dtype=dtype)
        for k in range(self.n_frames):
            out[:, :, k] = self.temp_frame(k).astype(dtype)
        return out
