"""Train a flight-plan policy (REINFORCE with a shared baseline over K samples per morning,
POMO-style) on SYNTHETIC mornings scored by the real engine, then compare it with the engine's
greedy VOI plan and the fixed patrol route on held-out mornings at the same 20-min budget.
Usage: python tools/rl/train.py <dir with meta.json, m_/t_ tr*, eval*, d2 json> [train_minutes]"""
import glob
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))
from avaenv import BUDGET, Lib, Mornings, Policy, metrics, rollout, route_minutes  # noqa: E402

D = Path(sys.argv[1])
TRAIN_MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
dev = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(0)
meta = json.loads((D / "meta.json").read_text())
lib = Lib(meta, dev)
idx = {k: i for i, k in enumerate(lib.ids)}


def load(tag):
    ms, ts = [], []
    for f in sorted(glob.glob(str(D / f"t_{tag}*.json"))):
        T = json.loads(Path(f).read_text())
        m = json.loads(Path(f.replace("t_", "m_")).read_text())
        assert m["ids"] == lib.ids, "library changed"
        n = len(T["now0"])
        ms.append({k: m[k][:n] for k in ("h", "s")})
        ts.append(T)
    cat = lambda xs, k: [r for x in xs for r in x[k]]
    m = {k: cat(ms, k) for k in ("h", "s")}
    T = {k: cat(ts, k) for k in ts[0]}
    return m, T


mt, Tt = load("tr")
me, Te = load("eval")
md, Td = load("d2")
ALL = Mornings(lib, mt, Tt)
perm = torch.randperm(ALL.B, generator=torch.Generator().manual_seed(1)).to(dev)
MV, MT = ALL.take(perm[:500]), ALL.take(perm[500:])  # validation (model selection) / training bank
ME, M2 = Mornings(lib, me, Te), Mornings(lib, md, Td)


def mask_of(routes):
    v = torch.zeros(len(routes), lib.L, dtype=torch.bool, device=dev)
    for m, r in enumerate(routes):
        for sid in r:
            v[m, idx[sid]] = True
    return v


assert max(route_minutes(lib, [idx[s] for s in r]) for r in Te["voi"]) <= BUDGET + 1e-6
res = {"greedy_voi": metrics(ME, mask_of(Te["voi"])), "fixed_route": metrics(ME, mask_of([meta["fixed"]] * ME.B))}
eng = lambda k: round(100 * sum(a - b for a, b in zip(Te["u0"], Te[k])) / sum(Te["u0"]), 2)
print("train bank", MT.B, "val", MV.B, "eval", ME.B, "| engine drop VOI", eng("u_voi"), "fixed", eng("u_fixed"), flush=True)
print("VOI", res["greedy_voi"], "\nfixed", res["fixed_route"], flush=True)

pol = Policy().to(dev)
opt = torch.optim.Adam(pol.parameters(), lr=3e-4)
B, K = 512, 16
curve, best, it, episodes, t0 = [], (-1e9, None), 0, 0, time.time()


def evaluate(M):
    pol.eval()
    with torch.no_grad():
        ret, _, _, vis, route = rollout(pol, M, greedy=True)
    pol.train()
    return ret.mean().item(), vis, route


g = torch.Generator(device=dev).manual_seed(2)
while time.time() - t0 < TRAIN_MIN * 60:
    M = MT.take(torch.randint(0, MT.B, (B,), device=dev, generator=g)).repeat(K)
    ret, logp, ent, _, _ = rollout(pol, M)
    R = ret.view(B, K)
    adv = ((R - R.mean(1, keepdim=True)) / (R.std() + 1e-6)).view(-1)
    ent_coef = 0.01 * max(0.0, 1 - (time.time() - t0) / (TRAIN_MIN * 60))
    loss = -(adv.detach() * logp).mean() - ent_coef * ent.mean()
    opt.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(pol.parameters(), 1.0)
    opt.step()
    episodes += B * K
    if it % 10 == 0:
        val, _, _ = evaluate(MV)
        test, _, _ = evaluate(ME)
        curve.append(dict(it=it, episodes=episodes, minutes=round((time.time() - t0) / 60, 3),
                          train_reward=round(ret.mean().item(), 4), val_reward=round(val, 4), eval_reward=round(test, 4)))
        if val > best[0]:
            best = (val, {k: v.clone() for k, v in pol.state_dict().items()}, it)
        if it % 100 == 0:
            print(curve[-1], flush=True)
    it += 1

train_minutes = (time.time() - t0) / 60
pol.load_state_dict(best[1])
_, vis, route = evaluate(ME)
assert all(route_minutes(lib, [i for i in r if i >= 0]) <= BUDGET + 1e-6 for r in route.tolist())
res["rl"] = metrics(ME, vis)
_, _, r2 = evaluate(M2)
rl_d2 = [lib.ids[i] for i in r2[0].tolist() if i >= 0]
torch.save(best[1], D / "policy.pt")
result = dict(
    algo="REINFORCE, baza = średnia z K=16 lotów tego samego poranka (POMO); polityka: MLP na cechach sektora + kontekst zbioru, maskowanie akcji",
    env_episodes_trained=episodes, iterations=it, best_iteration=best[2], train_minutes=round(train_minutes, 1),
    gpu=torch.cuda.get_device_name(0) if dev == "cuda" else "CPU", eval_mornings=ME.B, train_mornings=MT.B,
    sectors=lib.L, library_runs=lib.n_runs, metrics=res, engine_check=dict(voi=eng("u_voi"), fixed=eng("u_fixed")), curve=curve,
    day2=dict(rl=rl_d2, greedy_voi=Td["voi"][0], fixed_route=meta["fixed"],
              rl_min=round(route_minutes(lib, [idx[s] for s in rl_d2]), 1), voi_min=round(Td["voi_min"][0], 1),
              fixed_min=round(meta["fixed_min"], 1),
              kind0=dict(zip(lib.ids, Td["kind0"][0])), kind1=dict(zip(lib.ids, Td["kind1"][0])),
              metrics=dict(rl=metrics(M2, vis_d2 := torch.zeros(1, lib.L, dtype=torch.bool, device=dev).index_fill_(1, torch.tensor([idx[s] for s in rl_d2], device=dev), True)),
                           greedy_voi=metrics(M2, mask_of([Td["voi"][0]])), fixed_route=metrics(M2, mask_of([meta["fixed"]])))),
)
(D / "rl_result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf8")
print(json.dumps({k: v for k, v in result.items() if k != "curve"}, indent=1))
