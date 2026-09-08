"""W3 数据报告生成器：模拟/招募 → SQLite → 6 条分析 SQL 回放。

用法：python scripts/w3_report.py [--db results/w3.db]
产出：results/w3.db（任意 SQLite 客户端可打开）+ 控制台 6 条分析结论。
说明：目标目录无写权限时自动降级为内存库回放（仅打印，不落盘）。
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mini_tower.db import fetch, insert_recruit_runs, insert_sim_batch, load_queries, open_db  # noqa: E402
from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.recruit import RecruitPool  # noqa: E402
from mini_tower.simulator import run_batch  # noqa: E402

SCENARIOS = [
    ("1-1", ("sniper_a", "guard_b", "caster_c", "storm_d"), 800),   # 编队A
    ("1-2", ("sniper_a", "caster_c", "storm_d", "frost_f"), 1000),  # 编队B 含真伤
    ("1-2", ("sniper_a", "sniper_b", "storm_d", "frost_f"), 1000),  # 编队C 无真伤
    ("1-2", ("guard_b",), 400),                                     # 单近卫（弱编队）
    ("1-1", ("sniper_a", "sniper_b", "storm_d", "frost_f"), 400),   # 编队C 低难关
]

RECRUIT = {
    "off": dict(pity_cap=0),
    "on": dict(pity_cap=100, soft_pity_start=50, soft_pity_step=0.02),
}
RECRUIT_PULLS_PER_SEED = 250_000
RECRUIT_SEEDS = 4


def main() -> None:
    parser = argparse.ArgumentParser(description="W3 数据报告生成器")
    parser.add_argument("--db", default=str(REPO_ROOT / "results" / "w3.db"))
    args = parser.parse_args()

    catalog = load_catalog()
    db_path = args.db
    in_memory = False
    try:
        if Path(db_path) != Path(":memory:") and Path(db_path).exists():
            Path(db_path).unlink()
        conn = open_db(db_path)
    except PermissionError:
        in_memory = True
        conn = open_db(":memory:")
        print(f"[!] 无写权限，{db_path} 无法落盘 → 降级为内存库回放（仅打印）\n")

    total = 0
    for stage_id, team, rounds in SCENARIOS:
        bs = run_batch(catalog, stage_id, team, rounds=rounds, master_seed=20240301)
        total += insert_sim_batch(conn, stage_id, "+".join(team), bs)
        print(f"[sim] {stage_id:<4} {','.join(team):<46} × {rounds:>4} 局 -> 落库")

    recruit_total = 0
    for mode, kw in RECRUIT.items():
        pool = RecruitPool(p6=0.02, p5=0.08, **kw)
        sums = [pool.simulate(seed=900 + i, pulls=RECRUIT_PULLS_PER_SEED)
                for i in range(RECRUIT_SEEDS)]
        recruit_total += insert_recruit_runs(conn, sums, pity_enabled=(mode == "on"))
        for s in sums:
            print(f"[recruit] pity={mode:<3} seed={s.seed} pulls={s.pulls} "
                  f"6★={s.n6} rate={s.rate_6:.5f} max_gap={s.max_gap_6}")

    print(f"\n落库完成：sim_runs {total} 行，recruit_runs {recruit_total} 行"
          f"{'（内存库）' if in_memory else ''}\n")
    print("=" * 100)
    queries = load_queries()
    for name, sql in queries.items():
        print(f"\n【{name}】")
        rows = fetch(conn, sql)
        if not rows:
            print("  (无数据)")
            continue
        cols = list(rows[0].keys())
        print("  " + " | ".join(f"{c:<16}" for c in cols))
        for r in rows:
            print("  " + " | ".join(f"{str(r[c]):<16}" for c in cols))
    conn.close()


if __name__ == "__main__":
    main()
