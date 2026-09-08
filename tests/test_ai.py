"""W5 AI 辅助测试：三道闸（schema 校验 / 引擎交叉验证 / 人工复核留痕）。

对应 REQ-AI-001..007。默认用 StubProvider（本地规则，确定性离线），
同一套闸门在接入真实 LLM（HttpProvider）时原样生效。
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from dataclasses import replace  # noqa: E402

from mini_tower.ai import (  # noqa: E402
    AuditLog,
    AIOutputError,
    StubProvider,
    assess_numeric_risk,
    classify_failure_logs,
    cluster_accuracy,
    cross_validate_atk_interval,
    generate_test_points,
)
from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.simulator import run_batch  # noqa: E402


class _BrokenProvider(StubProvider):
    """返回非法 JSON / 缺字段 —— 用于验证"非法输出被 schema 拒绝"。"""

    def __init__(self, mode: str):
        self.mode = mode
        self.name = "stub(非法输出)"

    def complete(self, system: str, user: str) -> str:
        if self.mode == "not-json":
            return "抱歉我不能…（非结构化文本）"
        if self.mode == "missing-field":
            return '{"test_points": [{"focus": 123}]}'      # focus 应为 str + 缺字段
        return '{"risk": "fatal"}'                            # 枚举外值


class TestSchemaGate(unittest.TestCase):
    """REQ-AI-001：结构化输出 + schema 校验，非法输出直接拒绝并留痕。"""

    def setUp(self):
        self.audit = AuditLog()

    def test_non_json_output_rejected(self):
        out = generate_test_points("REQ-DMG-001 测试", provider=_BrokenProvider("not-json"),
                                   audit=self.audit)
        self.assertEqual(out["status"], "rejected")
        self.assertFalse(self.audit.records[-1].schema_ok)
        self.assertEqual(self.audit.records[-1].human_review, "pending")

    def test_missing_and_wrong_field_types_rejected(self):
        with self.assertRaises(AIOutputError):
            from mini_tower.ai import _extract_json, _validate, _POINTS_SPEC, _POINT_SPEC
            payload = _extract_json(_BrokenProvider("missing-field").complete("", ""))
            _validate(payload, _POINTS_SPEC, _POINT_SPEC)

    def test_enum_out_of_domain_rejected(self):
        with self.assertRaises(AIOutputError):
            from mini_tower.ai import _extract_json, _validate, _RISK_SPEC
            payload = _extract_json(_BrokenProvider("enum").complete("", ""))
            _validate(payload, _RISK_SPEC, None)

    def test_valid_stub_output_passes_and_audited(self):
        out = generate_test_points("REQ-DMG-001", provider=StubProvider(), audit=self.audit)
        self.assertEqual(out["status"], "ok")
        self.assertTrue(self.audit.records[-1].schema_ok)


class TestTestPointsGeneration(unittest.TestCase):
    """REQ-AI-002：需求→测试点，量化"AI 补充的新边界"，人审后入库。"""

    def test_novel_boundaries_quantified(self):
        covered = {"crit_rate 端点", "数值下限与非法值(0/负)"}   # 模拟"人已覆盖的检查点"
        out = generate_test_points(
            "REQ-DMG-001：物理伤害 = max(atk-def, ⌈atk×5%⌉)。",
            provider=StubProvider(),
            known_boundary_types=covered)
        self.assertEqual(out["status"], "ok")
        self.assertGreater(out["novel_count"], 0)          # AI 确实补充了新检查点
        for p in out["novel_points"]:
            self.assertNotIn(p["focus"], covered)
            self.assertTrue(p["test"])

    def test_human_review_workflow(self):
        audit = AuditLog()
        out = generate_test_points("REQ-STG-001", provider=StubProvider(), audit=audit)
        aid = out["audit_id"]
        self.assertEqual(audit.records[aid].human_review, "pending")
        audit.review(aid, "approved", note="边界 2/5 已采纳入库")
        self.assertEqual(audit.records[aid].human_review, "approved")


class TestRiskCrossValidation(unittest.TestCase):
    """REQ-AI-003/004：数值建议必须被引擎模拟校准（防幻觉关键闸）。"""

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def _star_at(self, atk: int) -> float:
        op = replace(self.catalog.operators["storm_d"], atk=atk)
        cat = replace(self.catalog, operators={**self.catalog.operators, "storm_d": op})
        return run_batch(cat, "1-2", ("guard_b", "storm_d"), rounds=400,
                         master_seed=20240301).three_star_rate

    def test_ai_over_aggressive_interval_is_corrected_by_engine(self):
        """AI 若给偏低下限(100) → 引擎实测驳回并修正到真实达标线。"""
        c = cross_validate_atk_interval(self.catalog, "1-2", ("guard_b", "storm_d"),
                                        "storm_d", ai_min=100, ai_max=140)
        self.assertFalse(c["consistent"])                  # 偏激进 → 不一致
        floor = c["verified_floor"]
        self.assertEqual(c["correction"]["corrected_min"], floor)
        # 自证引擎测得的 floor 是真边界
        self.assertGreaterEqual(self._star_at(floor), 0.95)
        self.assertLess(self._star_at(max(90, floor - 1)), 0.95)

    def test_sane_ai_interval_passes_consistency(self):
        """AI 若给达标区间（如 ≥115）→ 与引擎一致，无需纠正。"""
        c = cross_validate_atk_interval(self.catalog, "1-2", ("guard_b", "storm_d"),
                                        "storm_d", ai_min=115, ai_max=140)
        self.assertTrue(c["consistent"])

    def test_risk_assessment_pipeline_shape(self):
        audit = AuditLog()
        out = assess_numeric_risk("版本改动：storm_d atk 140 → 98（-30%）",
                                  provider=StubProvider(), audit=audit)
        self.assertEqual(out["status"], "ok")
        d = out["data"]
        self.assertIn(d["risk"], ("high", "medium", "low"))
        iv = d["suggested_interval"]
        self.assertEqual((iv["operator"], iv["field"]), ("storm_d", "atk"))
        self.assertTrue(self.audit_schema_ok(audit))

    def audit_schema_ok(self, audit: AuditLog) -> bool:
        return audit.records[-1].schema_ok


class TestFailureClustering(unittest.TestCase):
    """REQ-AI-005：失败日志聚类 + 与真实根因比对准确率。"""

    def test_cluster_and_accuracy(self):
        records = [
            {"stage_id": "1-2", "team_id": "guard_b", "leaked": 3, "lives_left": 4,
             "reason": "victory"},
            {"stage_id": "1-2", "team_id": "guard_b", "leaked": 3, "lives_left": 4,
             "reason": "victory"},
            {"stage_id": "1-1", "team_id": "sniper_b", "leaked": 0, "lives_left": 8,
             "reason": "victory"},
        ]
        out = classify_failure_logs(records, provider=StubProvider())
        self.assertEqual(out["status"], "ok")
        total = sum(c["count"] for c in out["data"]["clusters"])
        self.assertEqual(total, len(records))
        truth = {("1-2", "guard_b"): "漏怪:输出不足或防线缺口",
                 ("1-1", "sniper_b"): "通过但未三星"}
        acc = cluster_accuracy(out, truth)
        self.assertEqual(acc["total"], 2)
        self.assertEqual(acc["accuracy"], 1.0)


class TestAuditPersistence(unittest.TestCase):
    """REQ-AI-006：审计日志可落盘（无写权限时静默降级，不影响流程）。"""

    def test_append_with_unwritable_path_does_not_break(self):
        audit = AuditLog(path=os.path.join(REPO_ROOT, "results", "ai-audit.jsonl"))
        out = generate_test_points("REQ-PRB-003", provider=StubProvider(), audit=audit)
        self.assertEqual(out["status"], "ok")
        self.assertGreaterEqual(len(audit.records), 1)   # 内存审计始终保留


if __name__ == "__main__":
    unittest.main(verbosity=2)
