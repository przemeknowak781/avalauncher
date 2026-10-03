"""Two quick honesty checks before training.

1. Spatial leak: share of each held-out sector's footprint (union of pft > 0.1 over its runs) that lies
   inside the union of footprints of training runs, and which training sectors overlap it.
2. Crop coverage: share of each sector's footprint cells that fall inside its 256 x 256 input box.

Usage: python checks.py <assetsDir> <sectors_u8.bin> <heldOut,comma> <cache.npz> [...]
"""

import sys

import numpy as np

from net import S, crop_box, load_terrain, release_mask
from train import load_caches


def main(assets, sec_bin, held, caches):
    held = held.split(",")
    D, _ = load_caches(caches)
    dem, idx, sectors = load_terrain(assets, sec_bin)
    fp = D["pft"] > 0.1
    secs = sorted(set(D["sector"]))
    union = {s: fp[D["sector"] == s].any(0) for s in secs}
    train_union = np.any([union[s] for s in secs if s not in held], axis=0)
    for s in held:
        if s not in union:
            continue
        u = union[s]
        touch = sorted(((union[t] & u).sum() / u.sum(), t) for t in secs if t not in held and (union[t] & u).any())
        print(f"{s}: {u.sum()} cells, {100 * (u & train_union).sum() / u.sum():.0f}% inside training footprints; "
              f"overlapping sectors: " + ", ".join(f"{t} {100 * f:.0f}%" for f, t in touch[::-1]))
    low = []
    for s in secs:
        r0, c0 = crop_box(dem, release_mask(idx, sectors[s]["index"]))
        cov = union[s][r0:r0 + S, c0:c0 + S].sum() / union[s].sum()
        if cov < 0.99:
            low.append((round(float(cov), 3), s))
    print("crop coverage < 0.99:", sorted(low) or "none")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
