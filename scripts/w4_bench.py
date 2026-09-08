"""W4 性能基线生成/比对：结果写 results/baseline.json（无写权限则降级打印）。

用法：python scripts/w4_bench.py [--no-write]
产出：基准毫秒/局 + 峰值内存 + 伸缩曲线 + 与既有基线比对（容忍系数 1.5）。
对应 REQ-PERF-001..006。
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.perf import (  # noqa: E402
    bench_batch,
    bench_scale,
    build_baseline_entry,
    check_within_baseline,
    load_baseline,
    machine_info,
    scale_ratio,
    serialize_baseline,
)

TEAM_A = ("sniper_a", "guard_b", "caster_c", "storm_d")
TEAM_B = ("sniper_a", "caster_c", "storm_d", "frost_f")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-write", action="store_true", help="只打印不落盘")
    parser.add_argument("--baseline", default=str(REPO_ROOT / "results" / "baseline.json"))
    args = parser.parse_args()

    cat = load_catalog()
    print(f"机器：{machine_info()}\n")
    print("基准（每局平均墙钟毫秒 + 单局峰值内存）")
    results = {}
    for key, sid, team, rounds in [
        ("1-1/A", "1-1", TEAM_A, 2000),
        ("1-2/B", "1-2", TEAM_B, 2000),
    ]:
        b = bench_batch(cat, key, sid, team, rounds=rounds)
        results[key] = b
        print(f"  {key:<6} {rounds:>5} 局  {b.ms_per_run:8.4f} ms/局  峰值 {b.peak_mem_kb:8.1f} KB")

    scale = bench_scale(cat, (300, 3000))
    print("\n伸缩曲线（同构压力关：×10 敌人）")
    for k, v in scale.items():
        print(f"  enemies={k:<5} {v:8.2f} ms/局")
    print(f"  伸缩比 = {scale_ratio(scale):.2f}（近线性 ≈10）")

    entry = build_baseline_entry(results, scale)
    old = load_baseline(args.baseline) if not args.no_write else None
    if old and "bench" in old:
        print("\n与既有基线比对（容忍系数 1.5，REQ-PERF-003）")
        for key, b in results.items():
            base = old["bench"].get(key, {}).get("ms_per_run")
            if base is None:
                print(f"  {key}: 基线无此项（新场景）")
                continue
            ok = check_within_baseline(b.ms_per_run, base)
            print(f"  {key}: 当前 {b.ms_per_run:.4f} vs 基线 {base:.4f}"
                  f" 比值 {b.ms_per_run / base:.2f} -> {'PASS' if ok else 'FAIL(回归!)'}")
    else:
        print("\n（无既有基线：本次将新建）")

    text = serialize_baseline(entry)
    if args.no_write:
        print("\nbaseline.json（打印，未落盘）:\n" + text)
        return
    path = Path(args.baseline)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"\n已写入基线：{path}")
    except PermissionError:
        print(f"\n[!] 无写权限，无法落盘 {path}；基线内容如下：\n{text}")


if __name__ == "__main__":
    main()
