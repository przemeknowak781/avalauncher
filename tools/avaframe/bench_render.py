"""Time one 3D frame of render3d (same box and 2x mesh as the real renders)."""

import json
import platform
import sys
import time

import numpy as np

import render3d as r3

if __name__ == "__main__":
    assets = sys.argv[1]
    sc = r3.Scene(assets, (102, 150, 250))
    ft = np.zeros((400, 400), np.float32)
    ft[200:230, 260:300] = 1.2  # a patch of flow so the colour path runs too
    sc.frame(ft, 84, 28, "t = 0 s", "warm-up", "")
    t = time.perf_counter()
    for _ in range(3):
        sc.frame(ft, 84, 28, "t = 0 s", "bench", "")
    print(json.dumps({"host": platform.node(), "render3d_frame_s": round((time.perf_counter() - t) / 3, 1)}))
