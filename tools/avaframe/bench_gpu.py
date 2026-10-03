"""GPU benchmark for the surrogate idea: matmul throughput and a small conv encoder-decoder training step
on 128x128 runout maps (the shape a surrogate of AvaFrame would learn)."""

import json
import time

import torch
import torch.nn as nn


def matmul_tflops(dtype, n=8192, reps=20):
    a = torch.randn(n, n, device="cuda", dtype=dtype)
    b = torch.randn(n, n, device="cuda", dtype=dtype)
    for _ in range(3):
        a @ b
    torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(reps):
        a @ b
    torch.cuda.synchronize()
    return 2 * n ** 3 * reps / (time.perf_counter() - t) / 1e12


def net():
    def blk(i, o):
        return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                             nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True))
    return nn.Sequential(blk(4, 32), nn.MaxPool2d(2), blk(32, 64), nn.MaxPool2d(2), blk(64, 128),
                         nn.Upsample(scale_factor=2), blk(128, 64), nn.Upsample(scale_factor=2), blk(64, 32),
                         nn.Conv2d(32, 1, 1))


def train_rate(batch=64, steps=60):
    m = net().cuda()
    opt = torch.optim.AdamW(m.parameters(), 1e-3)
    x = torch.randn(batch, 4, 128, 128, device="cuda")  # DEM, release mask, slab depth, friction
    y = torch.rand(batch, 1, 128, 128, device="cuda")   # flow thickness map
    scaler = torch.amp.GradScaler()
    for i in range(steps + 10):
        if i == 10:
            torch.cuda.synchronize()
            t = time.perf_counter()
        with torch.autocast("cuda", dtype=torch.float16):
            loss = nn.functional.mse_loss(m(x), y)
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
    torch.cuda.synchronize()
    dt = time.perf_counter() - t
    m.eval()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        xi = torch.randn(256, 4, 128, 128, device="cuda")
        m(xi)
        torch.cuda.synchronize()
        t2 = time.perf_counter()
        for _ in range(10):
            m(xi)
        torch.cuda.synchronize()
        infer = 2560 / (time.perf_counter() - t2)
    return batch * steps / dt, infer


if __name__ == "__main__":
    samples_s, infer_s = train_rate()
    print(json.dumps({
        "gpu": torch.cuda.get_device_name(0),
        "matmul_fp32_tflops": round(matmul_tflops(torch.float32), 1),
        "matmul_fp16_tflops": round(matmul_tflops(torch.float16), 1),
        "train_samples_per_s": round(samples_s),
        "inference_maps_per_s": round(infer_s),
    }))
