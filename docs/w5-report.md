# W5 AI 辅助与每日回归报告（真实运行数据）

> 复现：`python scripts/w5_ai_demo.py`（AI 三条线）、`python scripts/ci_daily_balance.py`（每日回归）。
> 设计立场（面试口径）：**AI 是"初稿生成器"，不是"结论来源"**——所有产出必须过三道闸：
> ① schema 结构化校验（非法输出拒绝）→ ② 数值建议与引擎模拟交叉验证（防幻觉）→ ③ 人工复核留痕。
> 本环境默认本地规则提供者（确定性、离线），配 `AI_HTTP_URL`+`AI_API_KEY` 后同一套闸门接入真实 LLM。

---

## ① 需求 → 测试点/边界（REQ-AI-002）

输入：REQ-DMG-001/007、REQ-PRB-003、REQ-TGT-001 条目文本。
输出（本地规则提供者初稿，真实 LLM 同一契约）：

```
REQ-DMG-001  [数值下限与非法值(0/负)]      （人已覆盖，不重复计）
【新】 REQ-DMG-001 [恰好相等边界(def==atk)]    def==atk 与 def=atk-1 应给出不同结果
【新】 REQ-DMG-001 [同频共振(攻击间隔==生成间隔)]  整波不漏/全漏场景
【新】 REQ-DMG-001 [极限攻速(interval 取最小)]   事件密度最高处无丢失/乱序
【新】 REQ-DMG-001 [技能在击杀当帧触发]         技能计数与 kill 顺序
【新】 REQ-DMG-001 [暴击概率端点 0 与 1]        crit_rate 端点行为
→ AI 共 6 个检查点，人未覆盖的新点 5 个（人审"approved"后纳入 W6 用例库）
```

**量化口径**：与人已覆盖集合比对逐项 diff，给出"AI 补了多少我没想到的边界"——
这条量化本身比"我用了 AI"更值钱。

## ② 数值改动 → 风险评估 + 引擎交叉验证（REQ-AI-003/004）

```
改动：storm_d atk 140 → 98（-30%）
AI: risk=high，理由=临界编队很可能跌破三星设计目标
    AI 建议区间 atk∈[109,140]
引擎实测达标线 atk≥109（三星率≥95%）→ 一致 ✅（放行）
[对抗场景] 若 AI 给 atk≥100：引擎实测 109 → 不一致 → 驳回并自动修正到 109
```

**防幻觉证据**：AI 建议的数值区间永远先过 `cross_validate_atk_interval`——
用 400 局×N 个候选值的真实模拟校准；AI 下限低于实测达标线时自动修正并记录
`engine_verified=False`。这就是"数值改动合入前被测试拦下"的 AI 版。

## ③ 失败日志聚类（REQ-AI-005）

输入：引擎真实产出的非三星局日志（单近卫×3 seed + 样例行）。

```
[漏怪:输出不足或防线缺口] ×3   样例={stage:1-2, team:guard_b, leaked:3}
[通过但未三星]            ×1
→ 与真实根因比对：2/2 命中，准确率 100%
```

## 审计闭环（REQ-AI-006）

| # | capability | schema_ok | engine_verified | human_review |
|---|---|---|---|---|
| 0 | test_points | True | — | approved（备注：边界 2/6 采纳入 W6） |
| 1 | risk_assessment | True | True | pending |
| 2 | log_cluster | True | — | pending |

每条记录含 prompt/原始回复/校验结果，可落盘 `results/ai-audit.jsonl`（无写权限时保持内存审计）。

## ④ 每日回归与 CI（REQ-CI-001..003）

`scripts/ci_daily_balance.py`（确定性，seed 固定，机器无关）：

```
[PASS] REQ-BAL-001 编队A     clear=1.000 star=1.000 avg=28.00s
[PASS] REQ-BAL-002 编队B     clear=1.000 star=1.000 avg=55.18s
[PASS] REQ-BAL-003 弱编队     clear=1.000 star=0.000   （漏怪语义正确）
[PASS] REQ-BAL-005 临界编队   clear=1.000 star=1.000
[PASS] 最强编队漂移检测：满星率=1.000（冠军=编队A）
全部通过 ✅  （exit 0；任一 FAIL → exit 1，CI 红）
```

GitHub Actions 工作流 `.github/workflows/daily-balance.yml`：每日 02:00 UTC 定时 →
全量 79 条测试 + 平衡回归 + W3 数据报告 → 产物（SQLite/基线）归档。

## 面试口径

- "AI 输出怎么防幻觉？" → 三道闸 + 引擎交叉验证 + 审计留痕，任何一步不过都进不了结论；
- "无 Key 时怎么演示？" → 提供者可插拔，本地规则提供者让整条流水线离线可复现，
  真实 LLM 只换"初稿生成器"，闸门一字不改；
- "和别人的 AI 用法有何不同？" → 多数人拿 AI 结论直接用；我做的是**AI 初稿 + 可验证闭环**。
