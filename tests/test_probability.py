"""W3 概率域测试：招募引擎的正确性 + 统计假设检验。

对应 REQ-PRB-001..007 与 docs/test-case-matrix.md（W3 节）。
统计口径（面试口径）：
- 断言不是"模拟 1000 次等于 2%"，而是"在 95% 置信水平下不拒绝原假设"；
- χ² 拟合优度：df=2、α=0.05 临界值 5.991（纯 stdlib，无 scipy）；
- 二项比例 CI：正态近似 z=1.96。
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mini_tower.recruit import RecruitConfigError, RecruitPool, load_recruit_pool  # noqa: E402
from mini_tower.stats import (  # noqa: E402
    CHI2_CRITICAL_DF2_95,
    binomial_ci,
    chi2_gof_statistic,
)


class TestRecruitEngine(unittest.TestCase):
    """引擎正确性（REQ-PRB-001/003/005/006）。"""

    def test_prb001_seed_reproducible_sequence(self):
        pool = RecruitPool(p6=0.02, p5=0.08, pity_cap=100)
        a = pool.draw(seed=42, pulls=5000)
        b = pool.draw(seed=42, pulls=5000)
        self.assertEqual(a, b)

    def test_prb006_probabilities_sum_to_one(self):
        pool = RecruitPool(p6=0.02, p5=0.08, pity_cap=100)
        self.assertAlmostEqual(pool.p6 + pool.p5 + pool.p4, 1.0, places=9)
        self.assertTrue(pool.p6 < pool.p5 < pool.p4)     # 稀有度越高概率越低

    def test_prb005_pity_resets_after_six_star(self):
        """hard pity 窗口：cap=10 且无软保底时，6★ 每 10 抽必现、之后重新累计。"""
        pool = RecruitPool(p6=1e-9, p5=0.2, pity_cap=10, soft_pity_start=0)
        seq = pool.draw(seed=1, pulls=30)
        positions = [i for i, r in enumerate(seq, start=1) if r == 6]
        self.assertEqual(positions, [10, 20, 30])        # REQ-PRB-003/005

    def test_prb003_inclusive_gap_bounded_by_cap(self):
        """任意连续窗口内 6★ 间隔（含首尾）≤ cap（100）。"""
        s = load_recruit_pool().simulate(seed=7, pulls=200_000)
        self.assertLessEqual(s.max_gap_6, 100)

    def test_prb004_soft_pity_rate_increases(self):
        """软保底区间内 6★ 概率随距上次 6★ 的抽数单调不减。"""
        pool = RecruitPool(p6=0.02, p5=0.08, pity_cap=100,
                           soft_pity_start=50, soft_pity_step=0.02)
        rates = [pool._rate6(p) for p in range(45, 100)]
        self.assertEqual(rates, sorted(rates))

    def test_config_validation(self):
        with self.assertRaises(RecruitConfigError):
            RecruitPool(p6=0.5, p5=0.6)                    # p4 < 0
        with self.assertRaises(RecruitConfigError):
            RecruitPool(p6=0.02, p5=0.08, soft_pity_start=120, pity_cap=100)

    def test_recruit_data_file_loads(self):
        pool = load_recruit_pool()
        self.assertEqual(pool.p6, 0.02)
        self.assertEqual(pool.pity_cap, 100)


class TestHypothesisTests(unittest.TestCase):
    """统计假设检验（REQ-PRB-002：基础概率与声明一致）。"""

    N = 2_000_000   # 大样本，保证期望频数 ≫ 5（χ² 适用条件）

    def test_prb002_no_pity_chi2_goodness_of_fit(self):
        """关闭保底时，观测三档频数不显著偏离声明概率（χ²<5.991）。"""
        pool = RecruitPool(p6=0.02, p5=0.08, pity_cap=0)
        s = pool.simulate(seed=42, pulls=self.N)
        obs = [s.n6, s.n5, s.n4]
        exp = [self.N * p for p in (pool.p6, pool.p5, pool.p4)]
        stat = chi2_gof_statistic(obs, exp)
        self.assertLess(stat, CHI2_CRITICAL_DF2_95)
        self.assertLess(stat, 2.0)      # 宽松二次防线（该 seed 实测 0.146）

    def test_prb002_no_pity_six_star_rate_ci_contains_declared(self):
        """6★ 观测率落在声明概率 0.02 的 95% 二项置信区间内。"""
        pool = RecruitPool(p6=0.02, p5=0.08, pity_cap=0)
        s = pool.simulate(seed=42, pulls=self.N)
        lo, hi = binomial_ci(s.n6, s.pulls)
        self.assertGreaterEqual(hi, pool.p6)
        self.assertLessEqual(lo, pool.p6)

    def test_pity_improves_overall_rate_within_gap_bound(self):
        """开启保底后：整体 6★ 率高于基础概率，且间隔有界（引擎语义自洽）。"""
        pool = RecruitPool(p6=0.02, p5=0.08, pity_cap=100,
                           soft_pity_start=50, soft_pity_step=0.02)
        s = pool.simulate(seed=7, pulls=1_000_000)
        self.assertGreater(s.rate_6, 0.027)     # 实测 ≈0.0288
        self.assertLessEqual(s.max_gap_6, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
