# -*- coding: utf-8 -*-
"""
seq_to_mat.py  --  Batch-convert FLIR `.seq` thermal sequences to MATLAB `.mat`.

Usage
-----
    python seq_to_mat.py INPUT [-o OUTDIR] [options]

    INPUT      a .seq file, or a folder (every *.seq inside is converted)
    -o OUTDIR  where to write the .mat files (default: next to each .seq)

Options
-------
    --no-raw       do not store the raw 16-bit signal
    --no-temp      do not store the temperature array
    --float64      store temperature as double instead of single (2x larger)
    --no-compress  write uncompressed .mat (faster, much larger)

Output .mat (single file per clip; in MATLAB:  data(:,:,k) = frame k)
    temperature_C : single/double  [H x W x N]   temperature in deg C
    raw_counts    : uint16          [H x W x N]   lossless 16-bit detector signal
    calibration   : struct          Planck + object + atmospheric constants
    info          : struct          camera / lens / acquisition metadata

See README.md for the accuracy discussion.
"""
import os
import sys
import time
import glob
import argparse
import numpy as np
from scipy.io import savemat

from flir_seq import FlirSeq


def convert_one(path, outdir, store_raw, store_temp, temp_dtype, compress):
    t0 = time.time()
    name = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(outdir or os.path.dirname(path), name + ".mat")
    print("[%s] %d frames..." % (os.path.basename(path), 0), end="", flush=True)

    seq = FlirSeq(path)
    print("\r[%s] %s  %dx%d  %d frames  (%s, tau=%.5f)" % (
        os.path.basename(path), seq.info["CameraModel"], seq.width, seq.height,
        seq.n_frames, seq.info["CameraSerialNumber"], seq.tau_atm))

    mat = {"calibration": seq.calibration}
    info = dict(seq.info)
    info.update(Width=seq.width, Height=seq.height, NumFrames=seq.n_frames,
                SourceFile=os.path.basename(path),
                Note=("temperature_C = standard FLIR radiometric model on raw_counts "
                      "(Planck + emissivity + single-path atmospheric correction); "
                      "raw_counts = lossless 16-bit detector signal."))
    mat["info"] = info

    if store_raw or store_temp:
        raw = seq.read_all_raw()
        if store_raw:
            mat["raw_counts"] = raw
        if store_temp:
            T = np.empty(raw.shape, dtype=temp_dtype)
            for k in range(seq.n_frames):
                T[:, :, k] = seq.raw2temp(raw[:, :, k].astype(np.float64)).astype(temp_dtype)
            mat["temperature_C"] = T
            print("    temperature %.2f .. %.2f C" % (T.min(), T.max()))

    savemat(out, mat, do_compression=compress, oned_as="row")
    print("    -> %s  (%.1f MB, %.1fs)" % (out, os.path.getsize(out) / 1e6, time.time() - t0))


def main():
    ap = argparse.ArgumentParser(description="Batch FLIR .seq -> .mat converter")
    ap.add_argument("input", help="a .seq file or a folder containing .seq files")
    ap.add_argument("-o", "--outdir", help="output directory (default: beside each .seq)")
    ap.add_argument("--no-raw", action="store_true", help="omit raw_counts")
    ap.add_argument("--no-temp", action="store_true", help="omit temperature_C")
    ap.add_argument("--float64", action="store_true", help="temperature as double")
    ap.add_argument("--no-compress", action="store_true", help="no zlib compression")
    a = ap.parse_args()

    if os.path.isdir(a.input):
        files = sorted(glob.glob(os.path.join(a.input, "*.seq")))
    else:
        files = [a.input]
    if not files:
        sys.exit("No .seq files found in %r" % a.input)
    if a.outdir:
        os.makedirs(a.outdir, exist_ok=True)

    print("Converting %d file(s) -> .mat\n" % len(files))
    ok = 0
    for p in files:
        try:
            convert_one(p, a.outdir, not a.no_raw, not a.no_temp,
                        np.float64 if a.float64 else np.float32, not a.no_compress)
            ok += 1
        except Exception as e:
            print("    FAILED: %s" % e)
    print("\nDone: %d/%d converted." % (ok, len(files)))


if __name__ == "__main__":
    main()
