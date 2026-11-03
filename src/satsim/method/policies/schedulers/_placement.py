"""初次放置：按迭代时间代价选节点（各 Scheduler 共用）。

placement.mode:
  balance — 现默认，按 iter_time 摊开
  pack    — 优先填已占用节点，留下空闲星冷却（相位错开自热）
placement.max_busy_nodes: 可选上限；未满 KV 前不新开更多忙节点。
"""
from __future__ import annotations

from satsim.input.schema import SpecError
from satsim.method.engine.timing import iter_time


def _placement_cfg(world) -> tuple[str, int | None]:
    block = world.cfg.get("placement") or {}
    mode = str(block.get("mode", "balance"))
    raw = block.get("max_busy_nodes")
    max_busy = int(raw) if raw is not None else None
    return mode, max_busy


def place_by_iter_time(world, req) -> int:
    cap = float(world.cfg["gpu"]["kv_gib"]) * (2**30)
    mode, max_busy = _placement_cfg(world)
    scores: list[float] = []
    feasible: list[int] = []
    for j in range(world.n):
        used = sum(r.kv for r in world.nodes[j]) * world.bpt
        if used + req.kv * world.bpt > cap:
            scores.append(float("inf"))
            continue
        nd, ctx = world._stats()
        scores.append(
            iter_time(
                nd[j] + 1,
                ctx[j] + req.kv,
                world.f_of(j, world.env.now),
                world.cfg["gpu"],
            )
        )
        feasible.append(j)
    if not feasible:
        raise SpecError(f"请求 {req.i} 在所有节点都放不下 KV")

    occupied = [j for j in feasible if world.nodes[j]]
    candidates = list(feasible)

    if max_busy is not None and max_busy > 0:
        busy_ids = {j for j in range(world.n) if world.nodes[j]}
        if len(busy_ids) >= max_busy:
            limited = [j for j in candidates if j in busy_ids]
            if limited:
                candidates = limited

    if mode == "pack" and occupied:
        packed = [j for j in candidates if j in set(occupied)]
        if packed:
            candidates = packed

    return min(candidates, key=lambda j: scores[j])
