# -*- coding: utf-8 -*-
"""
seq_to_wmv.py  --  Batch-convert FLIR `.seq` thermal sequences to `.wmv` video.

Renders each frame's temperature through a colour map and encodes a WMV (wmv2)
video for quick visual preview.

Usage
-----
    python seq_to_wmv.py INPUT [-o OUTDIR] [options]

    INPUT      a .seq file, or a folder (every *.seq inside is converted)
    -o OUTDIR  where to write the .wmv files (default: next to each .seq)

Options
-------
    --fps F        playback frame rate (default 30)
    --cmap NAME    matplotlib colormap (default inferno; try: jet, hot, gray, viridis)
    --tmin T       fix colour-scale minimum (deg C); default = clip minimum
    --tmax T       fix colour-scale maximum (deg C); default = clip maximum
    --bitrate B    video bitrate (default 4000k)

IMPORTANT - playback speed
--------------------------
The video plays every frame at a CONSTANT fps. It does NOT reproduce the real
acquisition timing. FLIR cameras often record at a variable rate (e.g. a short
high-speed burst followed by a slow time-lapse), so a constant-fps video can
look sped up. For quantitative work use the .mat (see seq_to_mat.py); the .wmv
is only a visual preview. Tune --fps to taste.
"""
import os
import sys
import time
import glob
import argparse
import subprocess
import numpy as np
import matplotlib
import imageio_ffmpeg

from flir_seq import FlirSeq


def convert_one(path, outdir, fps, cmap_name, tmin, tmax, bitrate):
    t0 = time.time()
    name = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(outdir or os.path.dirname(path), name + ".wmv")

    seq = FlirSeq(path)
    W, H, N = seq.width, seq.height, seq.n_frames
    T = seq.read_all_temp(dtype=np.float32)
    vmin = tmin if tmin is not None else float(T.min())
    vmax = tmax if tmax is not None else float(T.max())
    print("[%s] %dx%d  %d frames  scale %.2f..%.2f C  -> %s @ %d fps" % (
        os.path.basename(path), W, H, N, vmin, vmax, os.path.basename(out), fps))

    cmap = matplotlib.colormaps[cmap_name]
    scale = 1.0 / (vmax - vmin) if vmax > vmin else 0.0

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(fps), "-i", "-",
           "-c:v", "wmv2", "-b:v", bitrate, out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(N):
        norm = np.clip((T[:, :, k] - vmin) * scale, 0, 1)
        rgb = (cmap(norm)[:, :, :3] * 255).astype(np.uint8)
        p.stdin.write(rgb.tobytes())
    p.stdin.close()
    rc = p.wait()
    if rc != 0:
        raise RuntimeError("ffmpeg exited with code %d" % rc)
    print("    -> %s  (%.2f MB, %.1fs)" % (out, os.path.getsize(out) / 1e6, time.time() - t0))


def main():
    ap = argparse.ArgumentParser(description="Batch FLIR .seq -> .wmv preview video")
    ap.add_argument("input", help="a .seq file or a folder containing .seq files")
    ap.add_argument("-o", "--outdir", help="output directory (default: beside each .seq)")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--cmap", default="inferno")
    ap.add_argument("--tmin", type=float, default=None)
    ap.add_argument("--tmax", type=float, default=None)
    ap.add_argument("--bitrate", default="4000k")
    a = ap.parse_args()

    if os.path.isdir(a.input):
        files = sorted(glob.glob(os.path.join(a.input, "*.seq")))
    else:
        files = [a.input]
    if not files:
        sys.exit("No .seq files found in %r" % a.input)
    if a.outdir:
        os.makedirs(a.outdir, exist_ok=True)

    print("Converting %d file(s) -> .wmv\n" % len(files))
    ok = 0
    for p in files:
        try:
            convert_one(p, a.outdir, a.fps, a.cmap, a.tmin, a.tmax, a.bitrate)
            ok += 1
        except Exception as e:
            print("    FAILED: %s" % e)
    print("\nDone: %d/%d converted." % (ok, len(files)))


if __name__ == "__main__":
    main()
