"""命令行入口：`python -m mini_tower`（headless demo / 指定关卡批量模拟）。

示例：
  python -m mini_tower                                  # 演示模式：参考编队 + 确定性校验
  python -m mini_tower --stage 1-2 --team sniper_a,caster_c,storm_d,frost_f
  python -m mini_tower --stage 1-2 --team sniper_a,caster_c,storm_d,frost_f \
      --rounds 200 --seed 20240521                     # 批量统计（W3 平衡断言的雏形）
"""

from __future__ import annotations

import argparse
import time
from typing import List, Optional

from . import __version__
from .loader import load_catalog
from .simulator import run_batch, run_once
from .combat import BattleResult

#: 参考编队（docs/requirements.md REQ-BAL-001/002）
TEAM_A = ["sniper_a", "guard_b", "caster_c", "storm_d"]
TEAM_B = ["sniper_a", "caster_c", "storm_d", "frost_f"]


def _fmt(r: BattleResult) -> str:
    star = "3★" if r.three_star else "--"
    return (
        f"clear={str(r.clear):5} reason={r.reason:<12} 剩余生命={r.lives_left:>3}"
        f" 三星={star} 击杀={r.kills} 漏怪={r.leaked} 总伤={r.total_damage}"
        f" 时长≈{r.end_time:6.1f}s 事件={len(r.events)}"
    )


def _events_head(r: BattleResult, n: int = 6) -> List[str]:
    return [
        f"  t={e.t:6.1f}s [{e.kind:<6}] {e.subject}  {e.detail}" for e in r.events[:n]
    ]


def _run_case(catalog, stage_id: str, team: List[str], expect: str, seed: Optional[int] = None):
    r = run_once(catalog, stage_id, team, seed=seed)
    print(f"  关卡 {stage_id}  编队 {','.join(team)}")
    print(f"    -> {_fmt(r)}")
    for line in _events_head(r):
        print(line)
    if len(r.events) > 6:
        print(f"    ...（共 {len(r.events)} 条事件）")
    print(f"    期望: {expect}")


def demo(catalog) -> None:
    print(f"MiniTower v{__version__} —— headless 冒烟演示")
    print(
        f"配置加载 OK：干员 {len(catalog.operators)} 名 / 敌人 {len(catalog.enemies)} 种 / 关卡 {len(catalog.stages)} 张\n"
    )
    print("[场景1] 1-1 · 参考编队A（高台+近卫+术师）应三星通关")
    _run_case(catalog, "1-1", TEAM_A, "clear=True, 3★=True", seed=42)
    print("\n[场景2] 1-2 · 参考编队B（含真实伤害术师）应对铁壳通关")
    _run_case(catalog, "1-2", TEAM_B, "clear=True", seed=42)
    print("\n[场景3] 1-2 · 单近卫（输出不足，铁壳漏怪）应通关但不三星")
    _run_case(catalog, "1-2", ["guard_b"], "clear=True, 3★=False", seed=42)

    print("\n[确定性校验 REQ-SIM-001] seed=7 跑两局，逐事件比对:")
    a = run_once(catalog, "1-1", TEAM_A, seed=7)
    b = run_once(catalog, "1-1", TEAM_A, seed=7)
    same = [ (e.t, e.kind, e.subject, e.detail) for e in a.events ] == [
        (e.t, e.kind, e.subject, e.detail) for e in b.events
    ]
    print(f"  事件数 {len(a.events)} == {len(b.events)}，逐事件一致: {same}")

    print("\n[批量吞吐 W4 前置] 1-1 编队A × 500 局耗时:")
    t0 = time.perf_counter()
    bs = run_batch(catalog, "1-1", TEAM_A, rounds=500, master_seed=20240521)
    dt = time.perf_counter() - t0
    print(
        f"  500 局耗时 {dt:.2f}s（≈{dt / 500 * 1000:.1f} ms/局）"
        f" 通关率={bs.clear_rate:.3f} 三星率={bs.three_star_rate:.3f}"
    )


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mini_tower",
        description="MiniTower headless 战斗模拟器（被测对象 SUT）",
    )
    parser.add_argument("--stage", help="关卡 id，如 1-1")
    parser.add_argument("--team", help="干员 id 列表，逗号分隔，如 sniper_a,caster_c")
    parser.add_argument("--rounds", type=int, default=1, help="批量局数（默认单局）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（master_seed）")
    parser.add_argument("--max-time", type=float, default=600.0)
    args = parser.parse_args(argv)

    catalog = load_catalog()

    if args.stage and args.team:
        team = [s.strip() for s in args.team.split(",") if s.strip()]
        if args.rounds > 1:
            t0 = time.perf_counter()
            bs = run_batch(catalog, args.stage, team, rounds=args.rounds,
                           master_seed=args.seed, max_time=args.max_time)
            dt = time.perf_counter() - t0
            print(
                f"[{args.stage}] 编队 {','.join(team)} × {bs.rounds} 局 "
                f"(seed {args.seed}..{args.seed + bs.rounds - 1}) 耗时 {dt:.2f}s"
            )
            print(
                f"  通关率={bs.clear_rate:.4f} ({bs.clear_count}/{bs.rounds})"
                f"  三星率={bs.three_star_rate:.4f} ({bs.three_star_count}/{bs.rounds})"
            )
            print(
                f"  平均剩余生命={bs.avg_lives_left:.2f}"
                f"  平均时长={bs.avg_duration:.1f}s  p99时长={bs.p99_duration:.1f}s"
            )
        else:
            r = run_once(catalog, args.stage, team, seed=args.seed, max_time=args.max_time)
            print(_fmt(r))
            print(f"  事件日志前 8 条:")
            for line in _events_head(r, 8):
                print(line)
    else:
        demo(catalog)


if __name__ == "__main__":
    main()
