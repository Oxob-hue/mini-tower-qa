"""CI 每日平衡回归（确定性）：参考编队通关/三星/时长带 + 最强编队漂移检测。

用法：python scripts/ci_daily_balance.py   （CI/GitHub Actions 每日定时）
- 阈值来自 REQ-BAL-001/002/005（docs/requirements.md），非拍脑袋；
- seed 固定 → 结果确定，机器无关；任一越界 → exit 1（CI 红）。
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.simulator import run_batch  # noqa: E402

ROUNDS = 300
SEED = 20240301

#: (stage, team, min_clear, min_star, dur_lo, dur_hi, 说明)
CHECKS = [
    ("1-1", ("sniper_a", "guard_b", "caster_c", "storm_d"), 0.999, 0.999, 24, 33, "REQ-BAL-001 编队A"),
    ("1-2", ("sniper_a", "caster_c", "storm_d", "frost_f"), 0.999, 0.99, 52, 58, "REQ-BAL-002 编队B"),
    ("1-2", ("guard_b",), 0.999, 0.0, None, None, "REQ-BAL-003 弱编队(应漏怪0三星)"),
    ("1-2", ("guard_b", "storm_d"), 0.999, 0.95, None, None, "REQ-BAL-005 临界编队"),
]


def main() -> None:
    cat = load_catalog()
    print(f"每日平衡回归 rounds={ROUNDS} seed={SEED}\n")
    ok_all = True
    for stage, team, cmin, smin, dlo, dhi, label in CHECKS:
        bs = run_batch(cat, stage, team, rounds=ROUNDS, master_seed=SEED)
        dur_ok = (dlo is None) or (dlo < bs.avg_duration < dhi)
        clear_ok, star_ok = bs.clear_rate >= cmin, bs.three_star_rate >= smin
        ok = clear_ok and star_ok and dur_ok
        ok_all &= ok
        extra = f" avg={bs.avg_duration:.2f}s" if dlo is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {label:<18} {','.join(team):<34} "
              f"clear={bs.clear_rate:.3f} star={bs.three_star_rate:.3f}{extra}")
    # 最强编队漂移检测：看当前"满星且最快"的编队是否符合预期
    champion = None
    best = (-1.0, float("-inf"))     # 目标：三星率越高越好、时长越短越好
    teams = [("sniper_a", "guard_b", "caster_c", "storm_d"),
             ("sniper_a", "caster_c", "storm_d", "frost_f")]
    for team in teams:
        bs = run_batch(cat, "1-1", team, rounds=ROUNDS, master_seed=SEED)
        score = (bs.three_star_rate, -bs.avg_duration)
        if score > best:
            best, champion = score, team
    drift_ok = best[0] >= 0.99
    ok_all &= drift_ok
    print(f"\n[{'PASS' if drift_ok else 'FAIL'}] 最强编队漂移检测：满星率={best[0]:.3f} "
          f"(冠军={','.join(champion)})")
    print(f"\n{'全部通过 ✅' if ok_all else '存在越界 ❌（详见上方 FAIL 行）'}")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
