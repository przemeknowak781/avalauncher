"""Vectorised drone flight-plan environment (PyTorch) on top of the REAL engine.

tools/rl/bank.mjs runs web/engine.js on SYNTHETIC mornings (tools/rl/gen.py) and stores, per sector,
everything the engine says before and after a survey: decision uncertainty now0/now1 (sectorValue),
expected value of information (info, gain), flags (kind0/kind1) and the hidden truth test (threat).
All of it is per sector and independent, so the environment is an orienteering problem: start at
the base, pick the next sector (masked so the return to base always fits the 20-min budget),
collect the realized reward, end when nothing else fits. The policy sees only belief features.
"""
import math

import numpy as np
import torch

SENSOR, SPEED, SURVEY, BUDGET = 0.08, 60.0, 1.5, 20.0
BONUS = 0.5  # x trail weight, for confirming a truly threatening slope as "zagrozenie"


class Lib:
    def __init__(self, meta, device="cpu"):
        self.ids, self.n_runs, self.dev = meta["ids"], meta["runs"], device
        self.L = len(self.ids)
        t = lambda a: torch.tensor(np.asarray(a, dtype=np.float64), dtype=torch.float32, device=device)
        self.base = np.array(meta["base"], dtype=np.float64)
        self.cent_np = np.array(meta["centroid"], dtype=np.float64)
        self.cent, self.base_t = t(self.cent_np), t(self.base)
        self.weight = t(meta["weight"])
        self.thr = t([x if x is not None else 3.0 for x in meta["threshold"]])
        self.d_base = torch.linalg.norm(self.cent - self.base_t, dim=1)
        self.D = torch.cdist(self.cent, self.cent)


class Mornings:
    def __init__(self, lib, m, T):
        t = lambda k, src: torch.tensor(np.asarray(src[k], dtype=np.float64), dtype=torch.float32, device=lib.dev)
        self.lib = lib
        self.h, self.s = t("h", m), t("s", m)
        self.now0, self.now1, self.info, self.gain, self.p = (t(k, T) for k in ("now0", "now1", "info", "gain", "p"))
        self.kind0, self.kind1 = t("kind0", T).long(), t("kind1", T).long()
        self.threat = t("threat", T) > 0.5
        self.B = self.h.shape[0]
        self.drop = self.now0 - self.now1  # realized drop of the engine's decision uncertainty
        self.resolved = (self.kind0 == 1) & (self.kind1 != 1)
        self.caught = self.threat & (self.kind1 == 2) & (self.kind0 != 2)
        self.reward = self.drop + BONUS * lib.weight * self.caught.float()
        self.u0 = self.now0.sum(1)

    def _new(self, fn, B):
        out = object.__new__(Mornings)
        out.__dict__.update({k: (fn(v) if torch.is_tensor(v) else v) for k, v in self.__dict__.items()})
        out.B = B
        return out

    def repeat(self, K):
        return self._new(lambda v: v.repeat_interleave(K, 0), self.B * K)

    def take(self, idx):
        return self._new(lambda v: v[idx], len(idx))


N_FEAT = 17


def features(M, pos, used, visited, feasible, d_pos):
    lib = M.lib
    cost = d_pos / SPEED + SURVEY
    rem = (BUDGET - used)[:, None]
    slack = (rem - cost - lib.d_base[None] / SPEED) / BUDGET
    val = M.gain * feasible.float()
    nb = (val[:, None, :] * torch.exp(-lib.D / 40.0)[None]).sum(-1)  # value reachable nearby
    z = ((M.h - lib.thr[None]) / M.s).clamp(-5, 5)
    w = lib.weight[None].expand_as(M.h)
    return torch.stack([
        M.h, M.s, z / 5, M.p, M.now0 / w, w / 3, M.info, M.gain, M.gain / cost, d_pos / 100,
        lib.d_base[None].expand_as(M.h) / 100, slack, rem.expand_as(M.h) / BUDGET,
        (M.kind0 == 1).float(), (M.kind0 == 2).float(), visited.float(), nb / 5,
    ], -1)


class Policy(torch.nn.Module):
    """Per-sector MLP scores with a pooled context (DeepSets), masked softmax over sectors."""

    def __init__(self, hid=128):
        super().__init__()
        self.l1 = torch.nn.Linear(N_FEAT, hid)
        self.l2 = torch.nn.Linear(2 * hid, hid)
        self.l3 = torch.nn.Linear(hid, 1)

    def forward(self, f, feasible):
        h1 = torch.relu(self.l1(f))
        m = feasible.float()[..., None]
        ctx = (h1 * m).sum(1) / m.sum(1).clamp_min(1)
        h2 = torch.relu(self.l2(torch.cat([h1, ctx[:, None].expand_as(h1)], -1)))
        return self.l3(h2)[..., 0]


def rollout(policy, M, greedy=False):
    lib = M.lib
    B, L = M.B, lib.L
    pos = lib.base_t[None].expand(B, 2).clone()
    used = torch.zeros(B, device=lib.dev)
    visited = torch.zeros(B, L, dtype=torch.bool, device=lib.dev)
    ret, logp, ent = (torch.zeros(B, device=lib.dev) for _ in range(3))
    ar = torch.arange(B, device=lib.dev)
    route = []
    for _ in range(L):
        d_pos = torch.linalg.norm(lib.cent[None] - pos[:, None], dim=-1)
        feas = (~visited) & (used[:, None] + d_pos / SPEED + SURVEY + lib.d_base[None] / SPEED <= BUDGET + 1e-6)
        alive = feas.any(1)
        if not alive.any():
            break
        logits = policy(features(M, pos, used, visited, feas, d_pos), feas)
        mask = feas.clone()
        mask[~alive, 0] = True
        logits = logits.masked_fill(~mask, -1e9)
        dist = torch.distributions.Categorical(logits=logits)
        a = logits.argmax(1) if greedy else dist.sample()
        af = alive.float()
        logp = logp + dist.log_prob(a) * af
        ent = ent + dist.entropy() * af
        ret = ret + M.reward[ar, a] * af
        used = used + (d_pos[ar, a] / SPEED + SURVEY) * af
        pos = torch.where(alive[:, None], lib.cent[a], pos)
        visited = visited | (torch.nn.functional.one_hot(a, L).bool() & alive[:, None])
        route.append(torch.where(alive, a, -1))
    return ret, logp, ent, visited, torch.stack(route, 1)


def route_minutes(lib, idx):
    pos, m = lib.base, 0.0
    for i in idx:
        c = lib.cent_np[i]
        m += math.hypot(*(c - pos)) / SPEED + SURVEY
        pos = c
    return m + math.hypot(*(lib.base - pos)) / SPEED


def metrics(M, visited):
    """Same realized evaluation for every planner: visited [B, L] bool."""
    v = visited.float()
    return dict(
        reward=round(float((M.reward * v).sum(1).mean()), 4),
        uncertainty_drop_pct=round(float(100 * (M.drop * v).sum() / M.u0.sum()), 2),
        unknowns_resolved=int((M.resolved & visited).sum()),
        unknowns_before=int((M.kind0 == 1).sum()),
        threats_caught=int((M.caught & visited).sum()),
        threats_catchable=int(M.caught.sum()),
        sectors_per_flight=round(float(v.sum(1).mean()), 2),
    )
