#!/usr/bin/env python3
"""Quantify the temperature precision lost when resampling FLIR thermal .mat data.

Rationale: spatial processing (registration, normalization, "unwrapping") should be
COMPUTED on a display image (normalized / CLAHE) but APPLIED to the raw temperature_C
(float) with a single interpolation. The only precision cost is that one interpolation.
This tool measures it on real frames via a clean invertible transform (rotate +a then -a),
reporting the error in degrees C, split into smooth-interior vs high-gradient edges, and
compares it to the 8-bit quantization floor you avoid by keeping data in float.

Usage:
    python interp_precision_check.py "path/glob/*.mat" [n_files] [frames_per_file]

Each .mat must contain a `temperature_C` array of shape (H, W, n_frames).
Requires numpy + scipy.
"""
import sys, glob, random
import numpy as np
from scipy.io import loadmat
from scipy.ndimage import rotate, gaussian_gradient_magnitude

FG_C = 30.0          # skin foreground threshold (deg C); edit for other subjects/regions
SEED = 42

def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*.mat"
    n_files = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    per_file = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    files = sorted(glob.glob(pattern))
    if not files:
        sys.exit(f"No .mat files match: {pattern}")
    random.seed(SEED); np.random.seed(SEED)
    files = random.sample(files, min(n_files, len(files)))

    interior, edge, quant = [], [], []
    n = 0
    for mp in files:
        T = loadmat(mp, variable_names=["temperature_C"])["temperature_C"]
        N = T.shape[2]
        for fi in random.sample(range(N), min(per_file, N)):
            f = T[:, :, fi].astype(np.float64)
            fg = f > FG_C
            if fg.sum() < 5000:
                continue
            g = gaussian_gradient_magnitude(f, 1.0)
            gt = g[fg]
            sm = fg & (g < np.percentile(gt, 50))
            ed = fg & (g > np.percentile(gt, 90))
            ang = np.random.uniform(5, 15)
            rt = np.abs(rotate(rotate(f, ang, reshape=False, order=3, mode="nearest"),
                               -ang, reshape=False, order=3, mode="nearest") - f)
            interior.append(np.median(rt[sm]))
            edge.append(np.percentile(rt[ed], 95))
            q = np.round((f - f.min()) / (f.max() - f.min()) * 255) / 255 * (f.max() - f.min()) + f.min()
            quant.append(np.median(np.abs(q - f)[fg]))
            n += 1
        del T

    def report(name, a):
        a = np.array(a)
        print(f"  {name:38s} median {np.median(a):.4f}  p95 {np.percentile(a,95):.4f}  max {a.max():.4f}  degC")
    print(f"files={len(files)}  frames={n}  (seed {SEED}, cubic rotate +/-[5,15] deg round-trip = 2 interpolations)")
    print("\nCorrect path (geometry applied to raw temperature_C, cubic):")
    report("interior (smooth) error", interior)
    report("edge p95 error", edge)
    print("\nFor reference:")
    report("8-bit quantization floor (avoidable)", quant)

if __name__ == "__main__":
    main()
