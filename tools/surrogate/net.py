"""Shared pieces of the AvaFrame surrogate: crop box, input features and a small U-Net."""

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

H = W = 400
CELL = 10.0
S = 256  # crop side in cells (2.56 km at 10 m)
SHIFT = 60  # crop centre moves this many cells downhill from the release centroid
FRICT = ["samosATSmall", "samosATMedium", "samosAT"]
N_IN = 11


def load_terrain(assets, sec_bin):
    assets = Path(assets)
    dem = np.fromfile(assets / "terrain_f32.bin", dtype="<f4").reshape(H, W)
    idx = np.fromfile(sec_bin, dtype=np.uint8).reshape(H, W)
    sectors = {s["id"]: s for s in json.loads((assets / "sectors.json").read_text(encoding="utf-8"))}
    return dem, idx, sectors


def release_mask(idx, index):
    """Largest 4-connected patch of the sector, as the AvaFrame release polygon is built."""
    from scipy import ndimage
    lab, n = ndimage.label(idx == index)
    if n <= 1:
        return lab > 0
    return lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)


def crop_box(dem, mask):
    """Square S x S box (r0, c0): release centroid pushed SHIFT cells down the mean fall line.
    Uses terrain and release cells only, never the simulated footprint."""
    gy, gx = np.gradient(dem.astype(np.float64), CELL)
    r, c = np.nonzero(mask)
    d = -np.array([gy[r, c].mean(), gx[r, c].mean()])
    d /= np.linalg.norm(d) + 1e-9
    cr, cc = r.mean() + SHIFT * d[0], c.mean() + SHIFT * d[1]
    r0 = int(np.clip(round(cr - S / 2), 0, H - S))
    c0 = int(np.clip(round(cc - S / 2), 0, W - S))
    return r0, c0


def features(z, mask, relth, frict):
    """z, mask: (B,1,S,S) float; relth: (B,) metres; frict: (B,) int. Returns (B,N_IN,S,S)."""
    B, _, h, w = z.shape
    zn = (z - z.mean(dim=(2, 3), keepdim=True)) / 250.0
    zp = F.pad(z, (1, 1, 1, 1), mode="replicate")
    gx = (zp[:, :, 1:-1, 2:] - zp[:, :, 1:-1, :-2]) / (2 * CELL)
    gy = (zp[:, :, 2:, 1:-1] - zp[:, :, :-2, 1:-1]) / (2 * CELL)
    lap = (zp[:, :, 1:-1, 2:] + zp[:, :, 1:-1, :-2] + zp[:, :, 2:, 1:-1] + zp[:, :, :-2, 1:-1] - 4 * z) / CELL
    slope = torch.atan(torch.sqrt(gx * gx + gy * gy)) / (np.pi / 4)
    rt = (relth / 2.0).view(B, 1, 1, 1).expand(B, 1, h, w)
    fr = F.one_hot(frict, 3).float().view(B, 3, 1, 1).expand(B, 3, h, w)
    return torch.cat([zn, gx, gy, lap.clamp(-3, 3), slope, mask, mask * rt, rt, fr], 1)


def block(ci, co):
    return nn.Sequential(nn.Conv2d(ci, co, 3, padding=1, bias=False), nn.BatchNorm2d(co), nn.GELU(),
                         nn.Conv2d(co, co, 3, padding=1, bias=False), nn.BatchNorm2d(co), nn.GELU())


class UNet(nn.Module):
    """Five downsamplings (256 -> 8) so the receptive field spans a whole avalanche path.
    Output channel 0: footprint logit (pft > 0.1 m); channel 1: log1p(pft)."""

    def __init__(self, ch=(32, 64, 128, 192, 256, 320)):
        super().__init__()
        self.enc = nn.ModuleList([block(N_IN, ch[0])] + [block(a, b) for a, b in zip(ch, ch[1:])])
        self.dec = nn.ModuleList([block(b + a, a) for a, b in zip(ch[:-1], ch[1:])])
        self.head = nn.Conv2d(ch[0], 2, 1)

    def forward(self, x):
        skips = []
        for i, e in enumerate(self.enc):
            x = e(x if i == 0 else F.max_pool2d(x, 2))
            skips.append(x)
        x = skips.pop()
        for d in reversed(self.dec):
            s = skips.pop()
            x = d(torch.cat([F.interpolate(x, size=s.shape[-2:], mode="bilinear", align_corners=False), s], 1))
        return self.head(x)


def to_pft(out):
    """Network output -> peak flow thickness [m] (zero outside the predicted footprint)."""
    fp = out[:, 0] > 0
    return torch.where(fp, torch.expm1(out[:, 1].float().clamp(min=0)), torch.zeros_like(out[:, 1].float()))


class Surrogate(nn.Module):
    """Raw crop inputs -> pft map. Wraps features + UNet so it exports as one graph."""

    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, z, mask, relth, frict):
        return to_pft(self.net(features(z, mask, relth, frict)))
