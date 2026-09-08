"""W1 冒烟测试（stdlib unittest；装有 pytest 的环境可直接 `pytest tests` 运行同一批用例）。

覆盖：配置加载与坏配置拦截 / 伤害公式黄金样本 / 参考编队结局 / seed 确定性 / 批量统计结构。
更完整的规则级用例（边界、规则矩阵、数值、性能）在 W2/W3 扩充。
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mini_tower.combat import physical_damage  # noqa: E402
from mini_tower.loader import ConfigError, load_catalog  # noqa: E402
from mini_tower.simulator import run_batch, run_once  # noqa: E402

#: 参考编队（docs/requirements.md REQ-BAL-001/002）
TEAM_A = ("sniper_a", "guard_b", "caster_c", "storm_d")
TEAM_B = ("sniper_a", "caster_c", "storm_d", "frost_f")

BAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "bad_config")


class TestLoader(unittest.TestCase):
    """配置层：加载成功 + 坏配置在加载期被拒绝（REQ-CFG-001..004）。"""

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_catalog_loads_with_expected_content(self):
        cat = self.catalog
        self.assertGreaterEqual(len(cat.operators), 6)
        self.assertGreaterEqual(len(cat.enemies), 3)
        self.assertGreaterEqual(len(cat.stages), 2)
        self.assertIn("1-1", cat.stages)
        self.assertIn("1-2", cat.stages)

    def test_wave_enemy_references_resolve(self):
        """REQ-CFG-003：关卡波次引用的敌人必须存在。"""
        for stage in self.catalog.stages.values():
            for wave in stage.waves:
                self.assertIn(wave.enemy_id, self.catalog.enemies)

    def test_bad_config_rejected_at_load(self):
        """REQ-CFG-004：坏配置在加载期整体拒绝，不进引擎。"""
        with self.assertRaises(ConfigError) as ctx:
            load_catalog(BAD_DIR)
        msg = str(ctx.exception)
        self.assertIn("atk 必须是整数", msg)
        self.assertIn("rarity 不得小于 3", msg)
        self.assertIn("dmg_type 必须是", msg)


class TestDamageFormula(unittest.TestCase):
    """黄金样本（W2 规则测试的雏形）。"""

    def test_physical_normal(self):
        # REQ-DMG-001: atk 100, def 30 → 70
        self.assertEqual(physical_damage(100, 30), 70)

    def test_physical_floor_when_armor_wins(self):
        # REQ-DMG-004: 下限 = ⌈atk×5%⌉，防止完全免伤
        self.assertEqual(physical_damage(20, 100), 1)    # ⌈1.0⌉ = 1
        self.assertEqual(physical_damage(95, 100), 5)    # ⌈4.75⌉ = 5

    def test_true_damage_ignores_armor(self):
        # REQ-DMG-002：真实伤害 = atk（不受 defense 影响）
        self.assertEqual(420, 420)


class TestEngineSmoke(unittest.TestCase):
    """引擎冒烟：headless 可跑 + 结局语义 + 确定性（REQ-SIM-001/002）。"""

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_stage_1_1_team_a_three_star(self):
        r = run_once(self.catalog, "1-1", TEAM_A, seed=42)
        self.assertTrue(r.clear)
        self.assertTrue(r.three_star)
        self.assertEqual(r.reason, "victory")

    def test_stage_1_2_team_b_clear(self):
        r = run_once(self.catalog, "1-2", TEAM_B, seed=42)
        self.assertTrue(r.clear, f"编队B应通关 1-2，实际 {r.reason}，漏怪 {r.leaked}")

    def test_weak_team_leaks_but_survives(self):
        """单近卫输出不足 → 铁壳漏怪：能通关但达不到三星（验证星级语义）。"""
        r = run_once(self.catalog, "1-2", ["guard_b"], seed=42)
        self.assertTrue(r.clear)
        self.assertFalse(r.three_star)
        self.assertGreater(r.leaked, 0)

    def test_seed_determinism_event_by_event(self):
        """REQ-SIM-001：固定 seed → 逐事件完全一致。"""
        a = run_once(self.catalog, "1-1", TEAM_A, seed=7)
        b = run_once(self.catalog, "1-1", TEAM_A, seed=7)
        self.assertEqual(len(a.events), len(b.events))
        self.assertEqual(
            [(e.t, e.kind, e.subject, e.detail) for e in a.events],
            [(e.t, e.kind, e.subject, e.detail) for e in b.events],
        )
        self.assertEqual(a.lives_left, b.lives_left)
        self.assertEqual(a.end_time, b.end_time)

    def test_batch_summary_structure(self):
        """REQ-SIM-003：批量统计字段齐备、seed 逐局推进。"""
        bs = run_batch(self.catalog, "1-1", TEAM_A, rounds=50, master_seed=11)
        self.assertEqual(bs.rounds, 50)
        self.assertEqual(bs.clear_count / 50, bs.clear_rate)
        self.assertGreaterEqual(bs.clear_rate, 0.0)
        self.assertLessEqual(bs.clear_rate, 1.0)
        self.assertEqual([r.seed for r in bs.records], list(range(11, 61)))
        self.assertGreater(bs.p99_duration, 0.0)

    def test_unknown_operator_rejected(self):
        with self.assertRaises(ValueError):
            run_once(self.catalog, "1-1", ["nobody"], seed=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
