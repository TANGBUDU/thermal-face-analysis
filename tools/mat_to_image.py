#!/usr/bin/env python3
"""Render frames from a FLIR thermal .mat (temperature_C) to PNG images.

For VISUALIZATION, or as the geometry-track display image only. A PNG is NOT
temperature data: quantitative analysis must always use the raw temperature_C
(float) array. Never read temperature back from an image -- that loses ~0.8 C
because contrast enhancement (CLAHE) is non-linear. See interp_precision_check.py.

Modes:
  raw    -> inferno heatmap with a degrees-C colorbar (for viewing)
  clahe  -> normalized + CLAHE grayscale (the display image fed to registration /
            landmarking; carries geometry only, not calibrated temperature)

Usage:
    python mat_to_image.py file.mat                    # middle frame -> file_f####.png
    python mat_to_image.py file.mat 120                # frame 120
    python mat_to_image.py file.mat all out_dir        # every frame into out_dir
    python mat_to_image.py file.mat 120 . clahe        # CLAHE display image

Requires numpy, scipy, matplotlib (+ scikit-image for the 'clahe' mode).
"""
import os, sys
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render(frame, out_path, mode):
    lo, hi = np.percentile(frame, 2), np.percentile(frame, 99.5)
    if mode == "clahe":
        from skimage.exposure import equalize_adapthist
        img = equalize_adapthist(np.clip((frame - lo) / (hi - lo), 0, 1), clip_limit=0.01)
        plt.imsave(out_path, img, cmap="gray")
    else:
        fig, ax = plt.subplots(figsize=(7, 5.5))
        m = ax.imshow(frame, cmap="inferno", vmin=lo, vmax=hi)
        ax.axis("off")
        fig.colorbar(m, ax=ax, shrink=0.8, label="temperature (C)")
        fig.savefig(out_path, dpi=110, bbox_inches="tight")
        plt.close(fig)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python mat_to_image.py file.mat [frame|mid|all] [out_dir] [raw|clahe]")
    mp = sys.argv[1]
    which = sys.argv[2] if len(sys.argv) > 2 else "mid"
    out_dir = sys.argv[3] if len(sys.argv) > 3 else "."
    mode = sys.argv[4] if len(sys.argv) > 4 else "raw"
    os.makedirs(out_dir, exist_ok=True)

    T = loadmat(mp, variable_names=["temperature_C"])["temperature_C"]
    n = T.shape[2]
    base = os.path.splitext(os.path.basename(mp))[0]
    idx = range(n) if which == "all" else [n // 2 if which == "mid" else int(which)]
    for i in idx:
        suffix = "_clahe" if mode == "clahe" else ""
        out_path = os.path.join(out_dir, f"{base}_f{i:04d}{suffix}.png")
        render(T[:, :, i].astype(float), out_path, mode)
        print("saved", out_path)


if __name__ == "__main__":
    main()
