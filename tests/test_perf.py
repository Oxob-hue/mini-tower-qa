"""W4 性能测试：绝对守卫 + 伸缩曲线 + 基线回归机制（纯 stdlib，不落盘）。

对应 REQ-PERF-001..006（docs/requirements.md §2.11）。
口径提醒：这里测的是"被测引擎单局性能"，不是测试用例执行效率。
墙钟断言易受机器影响 → 用宽松绝对守卫 + 对机器速度不敏感的"相对伸缩比"；
基线回归机制（baseline.json 比对）单独以纯函数形式验证，落盘由 scripts/w4_bench.py 完成。
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.perf import (  # noqa: E402
    bench_batch,
    bench_scale,
    check_within_baseline,
    load_baseline,
    scale_ratio,
    serialize_baseline,
)

TEAM_A = ("sniper_a", "guard_b", "caster_c", "storm_d")


class TestPerformanceGuards(unittest.TestCase):
    """REQ-PERF-001/002：绝对守卫（防灾难性回归，如死循环）。"""

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_perf001_single_run_under_absolute_guard(self):
        """1-1 编队A 单局 < 5ms（实测 ≈0.09ms；若代码引入死循环/灾难回归将远超）。"""
        b = bench_batch(self.catalog, "1-1/A", "1-1", TEAM_A, rounds=2000)
        self.assertLess(b.ms_per_run, 5.0)

    def test_perf002_peak_memory_bounded(self):
        """单局峰值内存 < 100MB（实测 ≈9KB，事件日志保留在设计预算内）。"""
        b = bench_batch(self.catalog, "1-1/A", "1-1", TEAM_A, rounds=200)
        self.assertLess(b.peak_mem_kb, 100_000)


class TestScaleCurve(unittest.TestCase):
    """REQ-PERF-004：×10 敌人 → 耗时近似 ×10（近线性），非平方爆炸。"""

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_perf004_tenfold_enemies_tenfold_time_approx(self):
        times = bench_scale(self.catalog, (300, 3000))
        ratio = scale_ratio(times)
        self.assertGreater(ratio, 5.0)    # 确实随规模增长（防"假实现/常量时间"）
        self.assertLess(ratio, 25.0)      # 未超线性过多（防 O(n²) 级别退化）


class TestBaselineMachinery(unittest.TestCase):
    """REQ-PERF-003/005/006：基线比对逻辑（纯函数，不依赖墙钟/落盘）。"""

    def test_check_within_baseline_respects_factor(self):
        self.assertTrue(check_within_baseline(10.0, 10.0, factor=1.5))
        self.assertTrue(check_within_baseline(14.9, 10.0, factor=1.5))
        self.assertFalse(check_within_baseline(15.1, 10.0, factor=1.5))

    def test_serialize_roundtrip_preserves_data(self):
        payload = {"machine": "t", "bench": {"k": {"ms_per_run": 0.1}}, "scale": {"100": 1.0}}
        restored = __import__("json").loads(serialize_baseline(payload))
        self.assertEqual(restored, payload)

    def test_load_missing_baseline_returns_none(self):
        self.assertIsNone(load_baseline(os.path.join(REPO_ROOT, "no-such-file.json")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
