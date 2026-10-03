"""Export the trained surrogate to ONNX (one graph: raw crop -> pft map). Not wired into the UI.

How the browser could run it later (onnxruntime-web, WebGPU or WASM backend, vendored in web/vendor/):
  inputs  z      float32 [1,1,256,256]  DEM crop in metres (terrain_f32.bin rows from north, box from
                                        surrogate_boxes.json, i.e. cells r0..r0+255, c0..c0+255)
          mask   float32 [1,1,256,256]  release cells of the sector (largest 4-connected patch of sectors_u8 == index)
          relth  float32 [1]            slab thickness in metres (0.4..2.0 seen in training)
          frict  float32 [1,3]          one-hot: samosATSmall, samosATMedium, samosAT
  output  pft    float32 [1,256,256]    peak flow thickness in metres, 0 outside the predicted footprint
  A slider handler would only change `relth` and re-run the session; the crop inputs stay cached.

Usage: python export_onnx.py <modelDir> <out.onnx>
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from net import CELL, S, UNet


class ExportWrap(nn.Module):
    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, z, mask, relth, frict):
        zn = (z - z.mean(dim=(2, 3), keepdim=True)) / 250.0
        zp = F.pad(z, (1, 1, 1, 1), mode="replicate")
        gx = (zp[:, :, 1:-1, 2:] - zp[:, :, 1:-1, :-2]) / (2 * CELL)
        gy = (zp[:, :, 2:, 1:-1] - zp[:, :, :-2, 1:-1]) / (2 * CELL)
        lap = (zp[:, :, 1:-1, 2:] + zp[:, :, 1:-1, :-2] + zp[:, :, 2:, 1:-1] + zp[:, :, :-2, 1:-1] - 4 * z) / CELL
        slope = torch.atan(torch.sqrt(gx * gx + gy * gy)) / (np.pi / 4)
        rt = (relth / 2.0).view(1, 1, 1, 1) * torch.ones_like(z)
        fr = frict.view(1, 3, 1, 1) * torch.ones_like(z)
        x = torch.cat([zn, gx, gy, lap.clamp(-3, 3), slope, mask, mask * rt, rt, fr], 1)
        o = self.net(x)
        th = torch.exp(o[:, 1].clamp(min=0)) - 1
        return torch.where(o[:, 0] > 0, th, torch.zeros_like(th))


def main(model_dir, out):
    ck = torch.load(Path(model_dir) / "model.pt", map_location="cpu", weights_only=False)
    net = UNet()
    net.load_state_dict(ck["state"])
    wrap = ExportWrap(net).eval()
    args = (torch.zeros(1, 1, S, S) + 1800, torch.zeros(1, 1, S, S), torch.tensor([1.2]), torch.tensor([[0., 1., 0.]]))
    torch.onnx.export(wrap, args, out, input_names=["z", "mask", "relth", "frict"], output_names=["pft"],
                      opset_version=17, dynamo=False)
    boxes = {s: [int(v) for v in b] for s, b in ck["boxes"].items()}
    Path(out).with_name("surrogate_boxes.json").write_text(json.dumps(boxes), encoding="utf-8")
    print(out, Path(out).stat().st_size / 1e6, "MB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
