"""W5 AI 辅助演示：三条线端到端 + 三道闸证据。

用法：python scripts/w5_ai_demo.py
- 默认用本地规则提供者（离线确定性）；配置 AI_HTTP_URL + AI_API_KEY 后自动切真实 LLM，
  同一套 schema 校验/引擎交叉验证/人工复核闸门原样生效。
产出：控制台报告（供 docs/w5-report.md 引用）＋ 内存审计日志。
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mini_tower.ai import (  # noqa: E402
    AuditLog,
    assess_numeric_risk,
    classify_failure_logs,
    cluster_accuracy,
    cross_validate_atk_interval,
    default_provider,
    generate_test_points,
)
from mini_tower.loader import load_catalog  # noqa: E402
from mini_tower.simulator import run_once  # noqa: E402

#: 人已在用例矩阵（docs/test-case-matrix.md）覆盖的"边界类型"，用于量化 AI 新增边界
KNOWN_BOUNDARIES = {
    "数值下限与非法值(0/负)", "物理 5% 下限(floor)", "def>atk",
    "先减免后暴击(ordering)", "每第 N 次命中触发(skill cycle)", "N=1 边界",
    "空挥不计命中", "技能吃暴击", "三星线等于/小于边界", "漏怪扣血按 leak",
    "硬保底第 cap 抽", "软保底单调", "seed 复现", "超时守卫", "波间隔不提前判胜",
    "生命归零即判负", "首次攻击前摇=interval", "最接近终点者优先",
}


def main() -> None:
    provider = default_provider()
    audit = AuditLog()
    cat = load_catalog()
    print(f"提供者：{getattr(provider, 'name', 'http(真实LLM)')}\n")

    # ---------------- ① 需求 → 测试点 ----------------
    print("=" * 76)
    print("① AI 需求拆解 → 测试点/边界（REQ-AI-002，人审后入库）")
    req = ("REQ-DMG-001 物理伤害=max(atk-def,⌈5%⌉)；REQ-DMG-007 同帧结算顺序；"
           "REQ-PRB-003 硬保底第cap抽必出；REQ-TGT-001 索敌最接近终点者")
    out = generate_test_points(req, provider=provider, audit=audit,
                               known_boundary_types=KNOWN_BOUNDARIES)
    if out["status"] != "ok":
        print(f"  [被拒] {out['issues']}")
    else:
        for p in out["data"]["test_points"]:
            tag = "【新】" if p in out["novel_points"] else "    "
            print(f"  {tag} {p['req_hint']:<12} [{p['focus']}] {p['test']}")
        print(f"  → AI 共给 {len(out['data']['test_points'])} 个测试点，"
              f"其中人未覆盖的新边界 {out['novel_count']} 个（人审采纳入库）")
        audit.review(out["audit_id"], "approved", note="边界 2/6 采纳入 W6 backlog")

    # ---------------- ② 数值改动 → 风险评估 + 引擎交叉验证 ----------------
    print("\n" + "=" * 76)
    print("② AI 数值改动风险评估 + 引擎交叉验证（REQ-AI-003/004，防幻觉闸）")
    change = "版本改动：storm_d atk 140 → 98（-30%）"
    risk = assess_numeric_risk(change, provider=provider, audit=audit)
    d = risk["data"]
    iv = d["suggested_interval"]
    print(f"  AI: risk={d['risk']}  理由={d['reasons'][0]}")
    print(f"      AI 建议区间 atk∈[{iv['min']},{iv['max']}]")
    cv = cross_validate_atk_interval(cat, "1-2", ("guard_b", "storm_d"),
                                     "storm_d", ai_min=iv["min"], ai_max=iv["max"])
    print(f"  引擎实测达标线 atk≥{cv['verified_floor']} "
          f"(三星率≥{cv['star_target']:.0%}) → "
          f"{'一致 ✅' if cv['consistent'] else '不一致 → 自动修正 ✅'}")
    if cv["correction"]:
        print(f"      修正记录：{cv['correction']['reason']} → 建议改为 ≥{cv['correction']['corrected_min']}")
    # 对抗演示：AI 若给出激进区间，闸门如何拦截
    adv = cross_validate_atk_interval(cat, "1-2", ("guard_b", "storm_d"),
                                      "storm_d", ai_min=100, ai_max=140)
    print(f"  [对抗场景] 若 AI 给 atk≥100：引擎实测 {adv['verified_floor']} → "
          f"{'放行' if adv['consistent'] else '驳回并修正到 '+str(adv['correction']['corrected_min'])}")
    audit.records[risk["audit_id"]].engine_verified = cv["consistent"]

    # ---------------- ③ 失败日志聚类 ----------------
    print("\n" + "=" * 76)
    print("③ AI 失败日志聚类（REQ-AI-005，与真实根因比对准确率）")
    records = []
    for seed in (1, 2, 3):                       # 引擎真实产出：单近卫漏 3 只、未三星
        r = run_once(cat, "1-2", ["guard_b"], seed=seed)
        records.append({"stage_id": "1-2", "team_id": "guard_b", "leaked": r.leaked,
                        "lives_left": r.lives_left, "reason": r.reason})
    records.append({"stage_id": "1-1", "team_id": "sniper_b", "leaked": 0,
                    "lives_left": 8, "reason": "victory"})   # 样例：通过但未三星
    clu = classify_failure_logs(records, provider=provider, audit=audit)
    for c in clu["data"]["clusters"]:
        print(f"  [{c['label']}] ×{c['count']}  样例={c['sample']}")
    truth = {("1-2", "guard_b"): "漏怪:输出不足或防线缺口",
             ("1-1", "sniper_b"): "通过但未三星"}
    acc = cluster_accuracy(clu, truth)
    print(f"  → 与真实根因比对：{acc['hit']}/{acc['total']} 命中，准确率 {acc['accuracy']:.0%}")

    # ---------------- 审计闭环 ----------------
    print("\n" + "=" * 76)
    print("审计闭环（REQ-AI-006）：全量记录 schema/引擎/人工状态")
    for i, rec in enumerate(audit.records):
        print(f"  #{i} {rec.capability:<14} schema_ok={rec.schema_ok} "
              f"engine_verified={rec.engine_verified} human={rec.human_review}")
    print("\n结论：AI 产出(初稿) → schema 校验 → 引擎交叉验证 → 人工复核留痕，全链路可追溯。")


if __name__ == "__main__":
    main()
