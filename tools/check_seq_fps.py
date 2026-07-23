#!/usr/bin/env python3
"""Check the effective saved frame rate (fps) of a FLIR .seq recording.

Reads the per-frame DateTimeOriginal timestamps embedded in the .seq via ExifTool,
then reports frame count, total duration, effective fps (= frames / duration), and
the inter-frame interval distribution. Useful for spotting decimated or non-uniform
recordings whose saved rate differs from the camera's configured frame rate.

Usage:
    python check_seq_fps.py path/to/file.seq
    python check_seq_fps.py                 # auto-pick the first *.seq under the current dir

Requires ExifTool (https://exiftool.org). If it is not on PATH, set the EXIFTOOL
environment variable to its full path.
"""
import os, re, sys, glob, subprocess, statistics
from datetime import datetime

EXIFTOOL = os.environ.get("EXIFTOOL", "exiftool")

def find_seq():
    hits = glob.glob("**/*.seq", recursive=True)
    return hits[0] if hits else None

def main():
    seq = sys.argv[1] if len(sys.argv) > 1 else find_seq()
    if not seq:
        sys.exit("No .seq file given or found under the current directory.")
    print("File:", seq)
    out = subprocess.run(
        [EXIFTOOL, "-ee", "-a", "-s", "-s", "-s", "-DateTimeOriginal", seq],
        capture_output=True).stdout.decode("latin1")
    pat = re.compile(r"\d{4}:\d\d:\d\d \d\d:\d\d:\d\d\.\d+")
    ts = [datetime.strptime(m.group(), "%Y:%m:%d %H:%M:%S.%f").timestamp()
          for m in (pat.search(l) for l in out.splitlines()) if m]
    if len(ts) < 2:
        sys.exit("Read fewer than 2 timestamps - is ExifTool installed and the file a valid .seq?")
    ts = [t - ts[0] for t in ts]
    span = ts[-1]
    dt = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
    print(f"Frames             : {len(ts)}")
    print(f"Duration (s)       : {span:.1f}")
    print(f"Effective fps      : {(len(ts) - 1) / span:.3f}   (= frames / duration)")
    print(f"Inter-frame dt (s) : min {min(dt):.3f}  median {statistics.median(dt):.3f}  max {max(dt):.3f}")
    print(f"Uniform?           : {'yes (near-constant interval)' if (max(dt) - min(dt)) < 0.1 else 'no (uneven / likely decimated)'}")

if __name__ == "__main__":
    main()
