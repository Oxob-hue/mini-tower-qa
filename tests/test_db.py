"""W3 数据层测试：schema / 落库 / SQL 查询回放（内存库，不落盘）。

覆盖 REQ-DATA-001..004：模拟与招募结果落库、分析 SQL 可执行且结论正确。
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mini_tower.db import (  # noqa: E402
    fetch,
    insert_recruit_runs,
    insert_sim_batch,
    load_queries,
    open_db,
)
from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.recruit import RecruitPool  # noqa: E402
from mini_tower.simulator import run_batch  # noqa: E402

TEAM_A = ("sniper_a", "guard_b", "caster_c", "storm_d")
TEAM_B = ("sniper_a", "caster_c", "storm_d", "frost_f")


class TestDataLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.conn = open_db(":memory:")
        cls.queries = load_queries()
        # 数据：2 个编队 × 少量局 + 招募（保底开/关各 2 段）
        b1 = run_batch(cls.catalog, "1-1", TEAM_A, rounds=6, master_seed=1)
        b2 = run_batch(cls.catalog, "1-2", TEAM_B, rounds=6, master_seed=1)
        insert_sim_batch(cls.conn, "1-1", "+".join(TEAM_A), b1)
        insert_sim_batch(cls.conn, "1-2", "+".join(TEAM_B), b2)
        pool_off = RecruitPool(p6=0.02, p5=0.08, pity_cap=0)
        pool_on = RecruitPool(p6=0.02, p5=0.08, pity_cap=100,
                              soft_pity_start=50, soft_pity_step=0.02)
        insert_recruit_runs(cls.conn,
                            [pool_off.simulate(seed=s, pulls=50_000) for s in range(100, 102)],
                            pity_enabled=False)
        insert_recruit_runs(cls.conn,
                            [pool_on.simulate(seed=s, pulls=50_000) for s in range(200, 202)],
                            pity_enabled=True)

    def test_sql_file_parses_more_than_five_queries(self):
        self.assertGreaterEqual(len(self.queries), 6)

    def test_q1_team_ranking_counts_match_inserts(self):
        rows = fetch(self.conn, self.queries["Q1 各编队通关质量排行（通关率/三星率/平均时长/漏怪总量）"])
        self.assertEqual(len(rows), 2)
        by_team = {r["team_id"]: r for r in rows}
        self.assertEqual(by_team["+".join(TEAM_A)]["clears"], 6)
        self.assertEqual(by_team["+".join(TEAM_B)]["runs"], 6)

    def test_q2_caster_composition_difference(self):
        rows = fetch(self.conn, self.queries["Q2 高防关（1-2）：编队是否含真实伤害术师 → 漏怪与三星率差异"])
        # 本库数据里 1-2 只有编队 B（含真伤术师）
        self.assertEqual(len(rows), 1)
        self.assertIn("caster_c", rows[0]["composition"])
        self.assertEqual(rows[0]["leaked"], 0)

    def test_q3_operator_damage_share_sum_equals_total(self):
        rows = fetch(self.conn, self.queries["Q3 干员伤害占比排行（json_each 展开 dmg_by_op，跨局聚合）"])
        total_by_query = sum(r["total_damage"] for r in rows)
        sql = "SELECT SUM(dmg_total) AS t FROM sim_runs"
        self.assertEqual(total_by_query, fetch(self.conn, sql)[0]["t"])

    def test_q4_recruit_pity_effect_rows(self):
        rows = fetch(self.conn, self.queries["Q4 保底开关对整体 6★ 率的影响（招募）"])
        by_pity = {r["pity_enabled"]: r for r in rows}
        self.assertIn(0, by_pity)
        self.assertIn(1, by_pity)
        self.assertGreater(by_pity[1]["rate6_pct"], by_pity[0]["rate6_pct"])

    def test_schema_roundtrip_records(self):
        n_sim = fetch(self.conn, "SELECT COUNT(*) AS n FROM sim_runs")[0]["n"]
        n_rec = fetch(self.conn, "SELECT COUNT(*) AS n FROM recruit_runs")[0]["n"]
        self.assertEqual(n_sim, 12)
        self.assertEqual(n_rec, 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
