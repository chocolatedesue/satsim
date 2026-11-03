"""placement.pack / max_busy_nodes：优先批次化占用、保留空闲。"""
from __future__ import annotations

from types import SimpleNamespace

from satsim.method.policies.schedulers._placement import place_by_iter_time


class _Req:
    def __init__(self, i, kv=100):
        self.i = i
        self.kv = kv


def _world(mode="pack", max_busy=2, n=4):
    nodes = [[] for _ in range(n)]
    cfg = {
        "gpu": {
            "kv_gib": 24.0,
            "t_fixed_s": 0.003,
            "t_weights_s": 0.01,
            "t_kv_tok_s": 1.0e-7,
            "t_seq_s": 5.0e-5,
            "mem_freq_exp": 0.6,
        },
        "placement": {"mode": mode, "max_busy_nodes": max_busy},
    }
    if max_busy is None:
        cfg["placement"] = {"mode": mode}

    def _stats():
        nd = [len(rs) for rs in nodes]
        ctx = [sum(r.kv for r in rs) for rs in nodes]
        return nd, ctx

    return SimpleNamespace(
        n=n,
        nodes=nodes,
        cfg=cfg,
        bpt=1.0,
        env=SimpleNamespace(now=0.0),
        f_of=lambda j, t: 1.0,
        _stats=_stats,
    )


def test_pack_prefers_occupied():
    w = _world(mode="pack", max_busy=None)
    j0 = place_by_iter_time(w, _Req(0))
    w.nodes[j0].append(_Req(0))
    j1 = place_by_iter_time(w, _Req(1))
    assert j1 == j0


def test_max_busy_caps_open_nodes():
    w = _world(mode="balance", max_busy=2)
    seen = set()
    for i in range(6):
        j = place_by_iter_time(w, _Req(i))
        w.nodes[j].append(_Req(i))
        seen.add(j)
    assert len(seen) == 2
