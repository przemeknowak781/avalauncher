"""Train the U-Net surrogate on AvaFrame peak flow thickness, holding out whole sectors.

Everything lives on the GPU: one DEM, one release mask per sector, one pft map per run.
Each sample is a 256 x 256 crop (jittered) with a random rotation / flip; features are computed
after augmentation so slope and fall line stay consistent with the rotated terrain.

Usage: python train.py <outDir> <assetsDir> <sectors_u8.bin> <steps> <heldOut,comma> <cache.npz> [...]
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from net import S, Surrogate, UNet, crop_box, features, load_terrain, release_mask, to_pft

dev = "cuda"
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


def load_caches(paths):
    seen, cols = set(), {k: [] for k in ("pft", "relTh", "frict", "sector", "sim", "path")}
    t_runs = []
    for p in paths:
        z = np.load(p)
        d = {k: z[k] for k in z.files}
        t_runs += list(d["s_per_run"])
        for i, path in enumerate(d["path"]):
            if path in seen:
                continue
            seen.add(path)
            for k in cols:
                cols[k].append(d[k][i])
    return {k: np.stack(v) if k == "pft" else np.array(v) for k, v in cols.items()}, np.array(t_runs)


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0


def main(out, assets, sec_bin, steps, held, caches):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    held = held.split(",")
    D, t_runs = load_caches(caches)
    dem, idx, sectors = load_terrain(assets, sec_bin)
    sec_ids = sorted(set(D["sector"]))
    masks = {s: release_mask(idx, sectors[s]["index"]) for s in sec_ids}
    boxes = {s: crop_box(dem, masks[s]) for s in sec_ids}
    # sectors whose runouts reach any cell of a held-out footprint are left out of training too,
    # so the held-out runout terrain is unseen as well (they are not used for evaluation either)
    fp = D["pft"] > 0.1
    held_union = fp[np.isin(D["sector"], held)].any(0)
    excluded = sorted(s for s in sec_ids if s not in held and (fp[D["sector"] == s].any(0) & held_union).any())
    tr = np.array([s not in held and s not in excluded for s in D["sector"]])
    ev = np.array([s in held for s in D["sector"]])
    print("excluded (runout overlaps held-out):", excluded, flush=True)
    print(f"{len(D['sector'])} sims, {len(sec_ids)} sectors; train {tr.sum()} / held-out {ev.sum()} ({held})",
          flush=True)

    dem_t = torch.tensor(dem, device=dev)
    mask_t = torch.stack([torch.tensor(masks[s], dtype=torch.float32) for s in sec_ids]).to(dev)
    sec_of = torch.tensor([sec_ids.index(s) for s in D["sector"]], device=dev)
    pft_t = torch.tensor(D["pft"], device=dev)  # float16 (N,400,400)
    rel_t = torch.tensor(D["relTh"], device=dev)
    fr_t = torch.tensor(D["frict"], device=dev)
    box_t = torch.tensor([boxes[s] for s in sec_ids], device=dev)

    def batch(ids, jitter=0, aug=False):
        zs, ms, ts = [], [], []
        for i in ids.tolist():
            si = int(sec_of[i])
            r0, c0 = box_t[si].tolist()
            if jitter:
                r0 = int(np.clip(r0 + np.random.randint(-jitter, jitter + 1), 0, 400 - S))
                c0 = int(np.clip(c0 + np.random.randint(-jitter, jitter + 1), 0, 400 - S))
            z = dem_t[r0:r0 + S, c0:c0 + S]
            m = mask_t[si, r0:r0 + S, c0:c0 + S]
            t = pft_t[i, r0:r0 + S, c0:c0 + S].float()
            if aug:
                k, fl = np.random.randint(4), np.random.rand() < 0.5
                z, m, t = (torch.rot90(a, k) for a in (z, m, t))
                if fl:
                    z, m, t = (torch.flip(a, (1,)) for a in (z, m, t))
            zs.append(z), ms.append(m), ts.append(t)
        z, m, t = (torch.stack(a)[:, None] for a in (zs, ms, ts))
        return features(z, m, rel_t[ids], fr_t[ids]), t[:, 0]

    net = UNet().to(dev).to(memory_format=torch.channels_last)
    print(f"params {sum(p.numel() for p in net.parameters()) / 1e6:.2f} M", flush=True)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=steps, pct_start=0.1)
    tr_ids = torch.tensor(np.nonzero(tr)[0], device=dev)
    bs = 32
    t0 = time.time()
    log = []
    for step in range(steps):
        net.train()
        ids = tr_ids[torch.randint(len(tr_ids), (bs,), device=dev)]
        x, t = batch(ids, jitter=24, aug=True)
        y, m = torch.log1p(t), (t > 0.1).float()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            o = net(x.contiguous(memory_format=torch.channels_last)).float()
        bce = F.binary_cross_entropy_with_logits(o[:, 0], m, pos_weight=torch.tensor(2.0, device=dev))
        l1 = ((o[:, 1] - y).abs() * (1 + 4 * m)).mean()
        loss = bce + l1
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        if step % 100 == 0 or step == steps - 1:
            el = time.time() - t0
            print(f"step {step:5d}  loss {loss.item():.4f} (bce {bce.item():.4f} l1 {l1.item():.4f})  "
                  f"{(step + 1) * bs / el:.0f} samples/s  {el:.0f} s", flush=True)
            log.append((step, loss.item()))
    train_s = time.time() - t0

    # ---- evaluation on the full 400 x 400 grid (crop pasted back, outside = 0)
    net.eval()
    res = {"train": [], "held": []}
    held_pred = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for i in np.nonzero(tr | ev)[0]:
            ids = torch.tensor([int(i)], device=dev)
            x, _ = batch(ids)
            p = to_pft(net(x.contiguous(memory_format=torch.channels_last)))[0].float().cpu().numpy()
            full = np.zeros((400, 400), np.float32)
            r0, c0 = boxes[D["sector"][i]]
            full[r0:r0 + S, c0:c0 + S] = p
            ref = D["pft"][i].astype(np.float32)
            v = iou(full > 0.1, ref > 0.1)
            key = "train" if tr[i] else "held"
            res[key].append(v)
            if ev[i]:
                held_pred.append((i, full.astype(np.float16), v))

    # ---- timing: one map at a time (batch 1) and throughput (batch 64), features + net on GPU
    sur = Surrogate(net).eval()
    s0 = held[0] if held[0] in boxes else sec_ids[0]
    r0, c0 = boxes[s0]
    z1 = dem_t[r0:r0 + S, c0:c0 + S][None, None].contiguous()
    m1 = mask_t[sec_ids.index(s0), r0:r0 + S, c0:c0 + S][None, None].contiguous()
    timing = {}
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for b in (1, 64):
            zb, mb = z1.expand(b, -1, -1, -1).contiguous(), m1.expand(b, -1, -1, -1).contiguous()
            rb, fb = torch.full((b,), 1.2, device=dev), torch.ones(b, dtype=torch.long, device=dev)
            for _ in range(20):
                sur(zb, mb, rb, fb)
            torch.cuda.synchronize()
            ts = []
            for _ in range(100 if b == 1 else 20):
                a = time.perf_counter()
                sur(zb, mb, rb, fb).cpu()
                ts.append(time.perf_counter() - a)
            timing[b] = float(np.median(ts)) * 1000 / b
    print(f"ms/map batch1 {timing[1]:.2f}, batch64 {timing[64]:.3f}", flush=True)

    torch.save({"state": net.state_dict(), "boxes": boxes, "held": held, "sectors": sec_ids}, out / "model.pt")
    hi = [h[0] for h in held_pred]
    np.savez_compressed(out / "held_pred.npz", idx=np.array(hi), pred=np.stack([h[1] for h in held_pred]),
                        iou=np.array([h[2] for h in held_pred]), ref=D["pft"][hi], relTh=D["relTh"][hi],
                        frict=D["frict"][hi], sector=D["sector"][hi], sim=D["sim"][hi])
    m = {"model": "U-Net 6 poziomów (32-320 kanałów), wejście 256x256 komórek po 10 m, PyTorch bf16",
         "params_M": round(sum(p.numel() for p in net.parameters()) / 1e6, 2),
         "trained_on_runs": int(tr.sum()), "all_runs": int(len(tr)),
         "train_sectors": [s for s in sec_ids if s not in held and s not in excluded], "held_out_sectors": held,
         "excluded_sectors": excluded, "held_out_runs": int(ev.sum()),
         "iou_mean": round(float(np.mean(res["held"])), 3), "iou_median": round(float(np.median(res["held"])), 3),
         "iou_train_mean": round(float(np.mean(res["train"])), 3),
         "iou_by_sector": {s: round(float(np.mean([h[2] for h in held_pred if D["sector"][h[0]] == s])), 3)
                           for s in held if s in boxes},
         "ms_per_map_gpu": round(timing[1], 2), "ms_per_map_gpu_batch64": round(timing[64], 3),
         "s_per_run_avaframe": round(float(np.median(t_runs)), 2) if len(t_runs) else None,
         "avaframe_timing_logs": int(len(t_runs)),
         "train_steps": steps, "batch": bs, "train_seconds": round(train_s, 1)}
    (out / "metrics.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(m, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6:])
