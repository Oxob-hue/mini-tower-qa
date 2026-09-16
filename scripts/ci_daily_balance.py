"""CI 每日平衡回归（确定性）：参考编队通关/三星/时长带 + 最强编队漂移检测。

用法：python scripts/ci_daily_balance.py   （CI：main 提交即回归 + 每日 02:00 UTC 定时）
- 阈值来自 REQ-BAL-001/002/005（docs/requirements.md），非拍脑袋；
- seed 固定 → 结果确定、机器无关；任一越界 → exit 1（CI 红）；
- 越界时在 FAIL 行下方打印「实测 vs 阈值 + 差值」，不必再翻用例或调参脚本就能
  判断"差多少、是数值过了还是时序偏了"。
"""

import sys
from pathlib import Path

# Windows 控制台默认 GBK：直接 print(✅/❌) 会抛 UnicodeEncodeError 导致脚本假失败。
# 统一把 stdout 切到 UTF-8；不支持 reconfigure 的环境（被重定向的旧管道）忽略即可。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (OSError, ValueError):        # pragma: no cover - 极端环境兜底
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.simulator import run_batch  # noqa: E402

ROUNDS = 300
SEED = 20240301

#: 最强编队漂移阈值：冠军编队满星率下限（REQ-BAL-004 设计目标）
DRIFT_MIN_STAR = 0.99
#: 参与漂移检测的候选编队（满星率最高且最快者为冠军）
CHAMPION_CANDIDATES = [
    ("sniper_a", "guard_b", "caster_c", "storm_d"),
    ("sniper_a", "caster_c", "storm_d", "frost_f"),
]

#: (stage, team, min_clear, min_star, dur_lo, dur_hi, 说明)
CHECKS = [
    ("1-1", ("sniper_a", "guard_b", "caster_c", "storm_d"), 0.999, 0.999, 24, 33, "REQ-BAL-001 编队A"),
    ("1-2", ("sniper_a", "caster_c", "storm_d", "frost_f"), 0.999, 0.99, 52, 58, "REQ-BAL-002 编队B"),
    ("1-2", ("guard_b",), 0.999, 0.0, None, None, "REQ-BAL-003 弱编队(应漏怪0三星)"),
    ("1-2", ("guard_b", "storm_d"), 0.999, 0.95, None, None, "REQ-BAL-005 临界编队"),
]


def _num(value: float) -> str:
    """阈值/差值用的紧凑数字：0.999→'0.999'、1.0001→'1.0001'、-0.019→'-0.019'。"""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-") else text


def evaluate(cat, stage, team, min_clear, min_star, dur_lo, dur_hi):
    """跑一批并返回 (batch_stats, 越界说明列表)；说明里带实测值、阈值与差值。"""
    bs = run_batch(cat, stage, team, rounds=ROUNDS, master_seed=SEED)
    problems = []
    if bs.clear_rate < min_clear:
        problems.append(
            f"通关率 {_num(bs.clear_rate)} < 阈值 {_num(min_clear)}"
            f"（差 {_num(bs.clear_rate - min_clear)}）"
        )
    if bs.three_star_rate < min_star:
        problems.append(
            f"三星率 {_num(bs.three_star_rate)} < 阈值 {_num(min_star)}"
            f"（差 {_num(bs.three_star_rate - min_star)}）"
        )
    if dur_lo is not None and not (dur_lo < bs.avg_duration < dur_hi):
        bound = dur_lo if bs.avg_duration <= dur_lo else dur_hi
        side = f"低于下限 {dur_lo}s" if bs.avg_duration <= dur_lo else f"高于上限 {dur_hi}s"
        problems.append(
            f"平均时长 {bs.avg_duration:.2f}s 不在区间 ({dur_lo}, {dur_hi})s"
            f"（{side}，偏离 {bs.avg_duration - bound:+.2f}s）"
        )
    return bs, problems


def main() -> None:
    cat = load_catalog()
    print(f"每日平衡回归 rounds={ROUNDS} seed={SEED}\n")
    failed = 0
    for stage, team, min_clear, min_star, dur_lo, dur_hi, label in CHECKS:
        bs, problems = evaluate(cat, stage, team, min_clear, min_star, dur_lo, dur_hi)
        ok = not problems
        failed += 0 if ok else 1
        extra = f" avg={bs.avg_duration:.2f}s" if dur_lo is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {label:<18} {','.join(team):<34} "
              f"clear={bs.clear_rate:.3f} star={bs.three_star_rate:.3f}{extra}")
        for problem in problems:
            print(f"       └ {problem}")

    # 最强编队漂移检测：看当前"满星且最快"的编队是否符合预期
    champion = None
    best = (-1.0, float("-inf"))     # 目标：三星率越高越好、时长越短越好
    for team in CHAMPION_CANDIDATES:
        bs = run_batch(cat, "1-1", team, rounds=ROUNDS, master_seed=SEED)
        score = (bs.three_star_rate, -bs.avg_duration)
        if score > best:
            best, champion = score, team
    drift_ok = best[0] >= DRIFT_MIN_STAR
    failed += 0 if drift_ok else 1
    print(f"\n[{'PASS' if drift_ok else 'FAIL'}] 最强编队漂移检测：满星率={best[0]:.3f} "
          f"(冠军={','.join(champion)})")
    if not drift_ok:
        print(f"       └ 满星率 {_num(best[0])} < 阈值 {_num(DRIFT_MIN_STAR)}"
              f"（差 {_num(best[0] - DRIFT_MIN_STAR)}）；"
              f"候选编队 {len(CHAMPION_CANDIDATES)} 支，均未达设计目标")

    total = len(CHECKS) + 1
    if failed == 0:
        print(f"\n全部通过 ✅（{total} 项检查：{len(CHECKS)} 项编队 + 1 项漂移检测）")
    else:
        print(f"\n存在越界 ❌：{failed}/{total} 项未通过（差值见上方 └ 行）")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
