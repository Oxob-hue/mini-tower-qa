"""W4 平衡调参故事线回归：改数值 → 平衡测试变红 → 调参 → 回归绿。

故事（REQ-BAL-005）：临界编队 磐石+惊雷 @ 1-2 的三星设计目标 ≥95%。
某版本把惊雷攻击力砍到 70%（140→98）→ 三星率 100%→43% → 测试红；
按建议把攻击力恢复到 ≥110（≥ 原值 79%）→ 回归绿。
全部数字来自引擎确定性模拟（非墙钟），测试稳定可复现。

实现手法：不修改正式 JSON 配置，用 dataclasses.replace 生成"改动后的干员"副本注入模拟
（等价于改配置 → 跑回归），避免污染主数据。
"""

import os
import sys
import unittest
from dataclasses import replace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.simulator import run_batch  # noqa: E402

TEAM = ("guard_b", "storm_d")        # REQ-BAL-005 临界编队
STAGE = "1-2"
ROUNDS = 800
SEED = 20240301
#: 设计目标：三星率 ≥95%（REQ-BAL-005）
STAR_TARGET = 0.95


def variant(operator_id: str, atk: int):
    """把干员攻击力改成 atk 的目录副本（不改正式 JSON）。"""
    cat = load_catalog()
    op = replace(cat.operators[operator_id], atk=atk)
    return replace(cat, operators={**cat.operators, operator_id: op})


def star_rate(cat) -> float:
    return run_batch(cat, STAGE, TEAM, rounds=ROUNDS, master_seed=SEED).three_star_rate


class TestTuningStory(unittest.TestCase):
    """「改数值→变红→调参→回归绿」全链路锁定。"""

    def test_baseline_critical_team_meets_design(self):
        bs = run_batch(load_catalog(), STAGE, TEAM, rounds=ROUNDS, master_seed=SEED)
        self.assertEqual(bs.clear_rate, 1.0)
        self.assertGreaterEqual(bs.three_star_rate, 0.99)

    def test_red_after_over_nerf(self):
        """改动超标（惊雷 atk 140→98，砍 30%）→ 三星率跌破设计目标 → 测试红。"""
        bs = run_batch(variant("storm_d", 98), STAGE, TEAM,
                       rounds=ROUNDS, master_seed=SEED)
        self.assertEqual(bs.clear_rate, 1.0)             # 削的是星级，不是通关
        self.assertLess(bs.three_star_rate, STAR_TARGET)  # 实测 ≈0.43

    def test_green_after_tuning_to_suggestion(self):
        """采纳建议（atk ≥110，取 112 ≈ 原值 80%）→ 三星率回到设计目标 → 回归绿。"""
        bs = run_batch(variant("storm_d", 112), STAGE, TEAM,
                       rounds=ROUNDS, master_seed=SEED)
        self.assertGreaterEqual(bs.three_star_rate, 0.99)  # 实测 1.0

    def test_suggestion_floor_locates_boundary(self):
        """建议下限确实贴着临界点：109 达标、106 不达标（自证"区间来自测试"而非拍脑袋）。"""
        self.assertGreaterEqual(star_rate(variant("storm_d", 109)), STAR_TARGET)
        self.assertLess(star_rate(variant("storm_d", 106)), STAR_TARGET)


if __name__ == "__main__":
    unittest.main(verbosity=2)
