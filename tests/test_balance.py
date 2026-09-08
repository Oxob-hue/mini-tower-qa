"""W3 数值测试：平衡性回归（蒙特卡洛批量）+ 数值膨胀/克制校验。

断言区间来源（面试口径）：
- 平衡回归区间：REQ-BAL 设计目标 + 基准（baseline）校准，不是拍脑袋；
- 膨胀比/克制比上限：数值设计约束（REQ-ANL-001/002/003）；
- 全部随机结论 seed 固定、模拟量写明（REQ-SIM-001/003）。
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mini_tower.analysis import analyze_roster, theoretical_dps, true_damage_advantage  # noqa: E402
from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.simulator import run_batch  # noqa: E402

TEAM_A = ("sniper_a", "guard_b", "caster_c", "storm_d")   # REQ-BAL-001
TEAM_B = ("sniper_a", "caster_c", "storm_d", "frost_f")   # REQ-BAL-002


class TestBalanceRegression(unittest.TestCase):
    """蒙特卡洛批量回归（REQ-BAL-001/002）：通关率与时长落在设计区间。"""

    ROUNDS = 2000
    SEED = 20240301

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_bal001_team_a_on_1_1_always_three_star(self):
        bs = run_batch(self.catalog, "1-1", TEAM_A, rounds=self.ROUNDS, master_seed=self.SEED)
        self.assertGreaterEqual(bs.clear_rate, 0.999)
        self.assertGreaterEqual(bs.three_star_rate, 0.999)

    def test_bal001_team_a_duration_in_design_band(self):
        bs = run_batch(self.catalog, "1-1", TEAM_A, rounds=self.ROUNDS, master_seed=self.SEED)
        self.assertGreater(bs.avg_duration, 24.0)     # 基准 28.0s：太快说明数值超标
        self.assertLess(bs.avg_duration, 33.0)        # 太慢说明输出不足
        self.assertLessEqual(bs.p99_duration, 34.0)

    def test_bal002_team_b_on_1_2_three_star_stable(self):
        bs = run_batch(self.catalog, "1-2", TEAM_B, rounds=self.ROUNDS, master_seed=self.SEED)
        self.assertGreaterEqual(bs.clear_rate, 0.999)
        self.assertGreaterEqual(bs.three_star_rate, 0.99)
        self.assertLess(bs.avg_duration, 58.0)        # 基准 ≈55.2s
        self.assertGreater(bs.avg_duration, 52.0)

    def test_weak_team_on_1_2_leaks_but_no_star_any_seed(self):
        """跨 seed 稳定性：单近卫漏 3 只铁壳 → 通关但 0% 三星（每局一致）。"""
        bs = run_batch(self.catalog, "1-2", ("guard_b",), rounds=200, master_seed=self.SEED)
        self.assertEqual(bs.clear_rate, 1.0)
        self.assertEqual(bs.three_star_rate, 0.0)
        self.assertTrue(all(r.leaked == 3 for r in bs.records))
        self.assertTrue(all(not r.three_star for r in bs.records))

    def test_dmg_aggregation_sanity(self):
        """伤害占比聚合自洽：Σ干员伤害 == 总局伤害，且归属干员都在编队内。

        注：1-1 敌人被高攻速干员秒杀，慢速高伤干员（焰雀 2.8s 前摇）可能整局
        “抢不到怪”零输出——溢出伤害不转移（REQ-DMG-006），这是现象而非缺陷。"""
        bs = run_batch(self.catalog, "1-1", TEAM_A, rounds=200, master_seed=self.SEED)
        for rec in bs.records:
            self.assertEqual(sum(rec.dmg_by_op.values()), rec.total_damage)
            self.assertTrue(rec.dmg_by_op)
            self.assertTrue(set(rec.dmg_by_op).issubset(set(TEAM_A)))
            self.assertTrue(all(v > 0 for v in rec.dmg_by_op.values()))


class TestInflationAndCountercheck(unittest.TestCase):
    """数值膨胀/克制静态校验（REQ-ANL-001..003）。"""

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_anl001_no_inflation_on_armorless_targets(self):
        """0 防目标：全干员理论 DPS 跨度 ≤ 3.2 倍（顶级未碾压入门，无膨胀）。"""
        ra = analyze_roster(self.catalog, defense=0)
        self.assertLess(ra.spread_ratio, 3.2)          # 实测 2.56

    def test_anl001_rarity_gap_within_design(self):
        """稀有度平均强度差受控：6★ 均值 / 4★ 均值 ≤ 3.0。"""
        ra = analyze_roster(self.catalog, defense=0)
        ratio = ra.rarity_mean_dps[6] / ra.rarity_mean_dps[4]
        self.assertLess(ratio, 3.0)                    # 实测 ≈2.46

    def test_anl003_high_defense_exposes_physical_weakness(self):
        """def100 下物理低攻大幅崩盘：理论跨度 ≥ 8 倍（高防环境有区分度）。"""
        ra = analyze_roster(self.catalog, defense=100)
        self.assertGreater(ra.spread_ratio, 8.0)       # 实测 ≈25.5

    def test_anl002_true_damage_is_the_counter(self):
        """克制校验（REQ-BAL-003）：def100 下真实伤害相对物理低攻优势 ≥ 10 倍。"""
        adv = true_damage_advantage(self.catalog, defense=100)
        self.assertGreater(adv, 10.0)                  # 实测 ≈25.2

    def test_anl004_theory_consistency_on_true_damage(self):
        """理论口径一致性：真实伤害干员 dps 与防御无关。"""
        caster = self.catalog.operators["caster_c"]
        self.assertAlmostEqual(theoretical_dps(caster, 0), theoretical_dps(caster, 100), places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
