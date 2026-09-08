"""性能基准与基线防回归（对"被测系统"，不是对测试用例本身）。

面试口径区分：
- pytest-xdist / 多进程 = "测试执行效率"（让测试跑得快），不是被测对象性能；
- 本模块测的是"被测引擎单局模拟性能"：N 局墙钟时间、单局峰值内存（tracemalloc）、
  同构规模伸缩曲线，并做 基线(baseline.json) 防回归断言（REQ-PERF-001..005）。

时机类断言注意：墙钟时间受机器负载影响 → 基线回归用"容忍系数 1.5"防误报；
伸缩曲线用"相对比值"（对机器速度不敏感），比绝对阈值稳健。
"""

from __future__ import annotations

import json
import os
import platform
import tracemalloc
from dataclasses import dataclass
from time import perf_counter
from typing import Dict, Optional, Sequence

from .combat import run_battle
from .models import Catalog, StageDef, WaveDef
from .simulator import run_once


@dataclass(frozen=True)
class BenchResult:
    key: str
    rounds: int
    ms_per_run: float        # 平均每局墙钟毫秒
    peak_mem_kb: float       # tracemalloc 单局峰值内存（KB）


def bench_batch(catalog: Catalog, key: str, stage_id: str, team: Sequence[str],
                rounds: int = 1000, master_seed: int = 20240501) -> BenchResult:
    """跑 rounds 局，返回平均毫秒/局 + 单局峰值内存。"""
    t0 = perf_counter()
    run_once_multi(catalog, stage_id, team, rounds, master_seed)
    dt_ms = (perf_counter() - t0) * 1000.0
    tracemalloc.start()
    run_once(catalog, stage_id, team, seed=master_seed)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return BenchResult(key=key, rounds=rounds,
                       ms_per_run=dt_ms / rounds, peak_mem_kb=peak / 1024.0)


def run_once_multi(catalog: Catalog, stage_id: str, team: Sequence[str],
                   rounds: int, master_seed: int) -> None:
    """批量跑局（仅计耗时，不构造汇总结构，减少测量噪声）。"""
    from .simulator import resolve_team
    stage = catalog.stages[stage_id]
    team_ops = resolve_team(catalog, team)
    for i in range(rounds):
        run_battle(catalog.enemies, stage, team_ops, seed=master_seed + i,
                   max_time=600.0)


def make_burst_stage(count: int, path: float = 200.0,
                     enemy_id: str = "walker") -> StageDef:
    """同构压力关：count 只敌人瞬间连发（interval=0.01）。

    事件量 ≈ 3×count（spawn + attack + kill），攻防与胜负条件一致，
    耗时随 count 的变化近似反映引擎"每敌人成本"。
    """
    return StageDef(
        sid=f"burst-{count}",
        name=f"压力关×{count}",
        path_length=path,
        base_hp=1000,
        three_star_lives=1,
        waves=(WaveDef(enemy_id=enemy_id, count=count,
                       start_time=0.0, interval=0.01),),
    )


def bench_scale(catalog: Catalog, counts: Sequence[int], reps: int = 2,
                enemy_id: str = "walker") -> Dict[int, float]:
    """伸缩曲线：返回 {count: 平均毫秒/局}。多次取最小值降噪。"""
    op = catalog.operators["storm_d"]   # 高攻速高伤，压力关单刷
    out: Dict[int, float] = {}
    for count in counts:
        stage = make_burst_stage(count, enemy_id=enemy_id)
        times = []
        for _ in range(reps):
            t0 = perf_counter()
            run_battle(catalog.enemies, stage, [op], seed=1, max_time=600.0)
            times.append((perf_counter() - t0) * 1000.0)
        out[count] = min(times)
    return out


def scale_ratio(times: Dict[int, float]) -> float:
    """伸缩比：最大档毫秒 / 最小档毫秒。纯线性应为 10（×10 敌人）；宽松判定见 REQ-PERF-004。"""
    keys = sorted(times)
    return times[keys[-1]] / times[keys[0]]


def machine_info() -> str:
    return (f"{platform.system()} {platform.release()} | "
            f"Python {platform.python_version()} | {platform.processor() or 'unknown'}")


def serialize_baseline(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def load_baseline(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_within_baseline(ms_now: float, baseline_ms: float, factor: float = 1.5) -> bool:
    """基线防回归（REQ-PERF-003）：当前毫秒/局 ≤ 基线 × factor。"""
    return ms_now <= baseline_ms * factor


def build_baseline_entry(results: Dict[str, BenchResult],
                         scale: Dict[int, float]) -> dict:
    return {
        "machine": machine_info(),
        "bench": {
            key: {
                "ms_per_run": round(r.ms_per_run, 4),
                "peak_mem_kb": round(r.peak_mem_kb, 1),
            }
            for key, r in results.items()
        },
        "scale": {str(k): round(v, 4) for k, v in scale.items()},
    }
