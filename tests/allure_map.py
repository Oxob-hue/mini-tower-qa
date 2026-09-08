"""unittest 测试类 → Allure 层级（epic/feature）+ pytest marker 的共享映射。

供两处使用（保持单一来源，避免漂移）：
- tests/conftest.py：pytest 收集时给用例打 Allure 动态标签与 marker；
- scripts/export_allure.py：脱离 pytest 直接运行 unittest 并导出 Allure JSON。

本文件禁止 import pytest（导出器需在无 pytest 环境运行）。
"""

#: 测试类名 → (Allure epic, Allure feature, pytest marker)
CLASS_MAP = {
    "TestLoader":                 ("配置与数据", "CFG 加载校验", "rules"),
    "TestEngineSmoke":            ("基础", "引擎冒烟 Smoke", "smoke"),
    "TestDamageFormula":          ("基础", "伤害公式黄金样本", "smoke"),
    "TestDamageRules":            ("战斗规则", "伤害结算 DMG", "rules"),
    "TestSkillRules":             ("战斗规则", "技能 SKL", "rules"),
    "TestTargetingRules":         ("战斗规则", "索敌 TGT", "rules"),
    "TestStageRules":             ("战斗规则", "关卡规则 STG", "rules"),
    "TestRecruitEngine":          ("数值质量", "招募引擎 PRB", "probability"),
    "TestHypothesisTests":        ("数值质量", "概率假设检验 PRB", "probability"),
    "TestBalanceRegression":      ("数值质量", "平衡回归 BAL", "balance"),
    "TestInflationAndCountercheck": ("数值质量", "膨胀/克制校验 ANL", "balance"),
    "TestDataLayer":              ("数据工程", "SQLite 数据层 DATA", "data"),
    "TestPerformanceGuards":      ("性能", "绝对守卫 PERF", "perf"),
    "TestScaleCurve":             ("性能", "伸缩曲线 PERF", "perf"),
    "TestBaselineMachinery":      ("性能", "基线机制 PERF", "perf"),
    "TestTuningStory":            ("数值质量", "调参故事线 BAL", "tuning"),
    "TestSchemaGate":             ("AI 辅助", "schema 闸 AI", "ai"),
    "TestTestPointsGeneration":   ("AI 辅助", "需求→测试点 AI", "ai"),
    "TestRiskCrossValidation":    ("AI 辅助", "交叉验证 AI", "ai"),
    "TestFailureClustering":      ("AI 辅助", "失败聚类 AI", "ai"),
    "TestAuditPersistence":       ("AI 辅助", "审计留痕 AI", "ai"),
}
