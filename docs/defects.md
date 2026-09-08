# 缺陷复盘记录（Defect Retrospective）

> 定位：本仓库的「发现缺陷 → 定位根因 → 推动修复 → 回归验证」闭环记录，是面试讲
> JD 职责④⑤（"发现和推动解决项目中的风险"）的**一手证据链**。
> 原则：每个缺陷都要有 ① 可复现用例 ② 变红证据 ③ 根因 ④ 修复 ⑤ 回归用例 ⑥ 对测试方法的启示。

---

## BUG-001 清场判胜漏路径 → 漏怪清场误判超时失败【真实缺陷】

| 项 | 内容 |
|---|---|
| 编号 / 严重度 | BUG-001 / 高（胜负判定错误，直接导致通关误判） |
| 状态 | 已修复（v0.1.1）；回归用例锁定 |
| 发现方式 | W1 演示「场景3：单近卫打 1-2」（输出漏怪 3 只、生命 4 > 0，却 `reason=timeout, clear=False`） |
| 现象 | 最后一只敌人「漏怪到达终点」离场后，干员持续空挥；事件队列永不为空，模拟空转到 600s 触发超时守卫，把本应 **通关** 的局判成 **失败** |

**根因**：胜利判定（场上无敌人 且 无待生成敌人 → victory）只写在"击杀（kill）"分支里；
清场路径共有三条（击杀 / 漏怪离场 / 击杀后空挥），后两条没有覆盖。

**修复**（combat.py）：在每个事件处理结束后做**统一清场判定**，覆盖三条路径：
```python
if result is None and not enemies and total_to_spawn == 0:
    result = victory(...)
```

**回归验证（红 → 绿）**：
- 修复前：`clear=False reason=timeout`（600.0s）
- 修复后：`clear=True reason=victory lives=4 三星=-- 时长≈58.0s`
- 锁定用例：
  - `tests/test_smoke.py::TestEngineSmoke::test_weak_team_leaks_but_survives`（场景3）
  - `tests/test_rules.py::TestStageRules::test_victory_reason_and_leak_count_when_single_leak`
  - `tests/test_rules.py::TestDamageRules::test_dmg005_attack_interval_kept_after_miss`

**启示**：胜负/状态迁移类逻辑的测试不能只测"主路径"，要枚举**所有可能的清场路径**；
凡是"循环靠自我续命事件驱动"的实现，必须考虑事件源不会耗尽的场景（这就是边界测试的价值）。

---

## BUG-002 物理伤害把"5% 下限"实现成"固定 1"【W2 演练缺陷】

> 说明：按需求文档 §2"诚实设计建议"做的受控演练——真实开发中"写错一处公式"很常见，
> 这里完整演示它如何被**黄金样本测试**当场抓住。

| 项 | 内容 |
|---|---|
| 编号 / 严重度 | BUG-002 / 中（高防目标下物理伤害系统性偏低 → 数值预期失真） |
| 状态 | 已修复（v0.1.2）；回归用例锁定 |
| 发现方式 | 由需求推导的黄金样本用例执行失败 |

**错误实现**（`combat.py::physical_damage`）：实现时把下限 ⌈atk×5%⌉ 偷懒写成 1
```python
return max(atk - defense, 1)   # 错误：atk95/def100 → 1
```

**变红证据**（真实输出）：
```
FAIL: test_dmg001_floor_5pct_when_armor_wins
REQ-DMG-004：物理伤害下限 = ⌈atk×5%⌉。atk95 vs def100 → 5。
AssertionError: 1 != 5
```

**影响面**：低攻物理干员打高防敌人（如铁壳 def=100）时，下限伤害从 5 掉到 1，
导致物理 DPS 被系统性低估/高估（视场景），W3 的平衡蒙特卡洛若基于此会得出**错误平衡结论**。

**修复**：还原为需求公式
```python
return max(atk - defense, math.ceil(atk * PHYS_MIN_PCT))   # 正确：atk95/def100 → 5
```

**回归验证**：修复后 7/7 绿；锁定用例 `test_dmg001_floor_5pct_when_armor_wins`、
`test_dmg004_floor_never_below_one`。

**启示**：数值规则必须**先手算黄金样本再写断言**（期望值来自需求文档，不是来自实现），
公式类缺陷（下限/取整/减免方式）才能被 1 条用例精准锁定。

---

## BUG-003 技能触发 off-by-one：第 N−1 次命中提前触发【W2 演练缺陷】

| 项 | 内容 |
|---|---|
| 编号 / 严重度 | BUG-003 / 中（技能节奏错误 → 技能覆盖率与设计不符 → 数值测算失真） |
| 状态 | 已修复（v0.1.2）；回归用例锁定 |
| 发现方式 | 规则序列用例执行失败（需求规定第 N/2N/3N 次触发） |

**错误实现**（`combat.py` 技能判定）：触发条件写成 `(landed + 1) % N == 0`
（等价于第 N−1、2N−1… 次提前触发）
```python
is_skill = bool(op.skill_every) and (opst.landed + 1) % op.skill_every == 0  # 错误
```

**变红证据**（真实输出，N=3 应得 普通,普通,技能…，实际提前一枪）：
```
FAIL: test_skl001_skill_on_every_nth_landed_hit
AssertionError: Lists differ: ['attack','skill','attack','attack','skill','attack']
                                != ['attack','attack','skill','attack','attack','skill']
FAIL: test_skl001_missed_attack_does_not_advance_skill_counter
AssertionError: Lists differ: ['skill','attack','skill','attack'] != ['attack','skill','attack','skill']
```

**影响面**：技能提前触发 → 单局 DPS 与技能覆盖率偏离设计值；属于"单看不明显、
批量统计才放大"的缺陷（W3 数值回归正是它的克星）。

**修复**：还原为 `landed % skill_every == 0`（第 N、2N、3N 次命中触发）。

**回归验证**：修复后全量 32/32 绿；锁定用例 `test_skl001_skill_on_every_nth_landed_hit`、
`test_skl001_missed_attack_does_not_advance_skill_counter`。

**启示**：周期性触发（每第 N 次）是 off-by-one 高发区，测试必须断言**完整序列**而非单个事件；
边界（N=1、命中计数是否含空挥）值得单独用例锁定。

---

## 复盘小结

| 缺陷 | 类别 | 发现手段 | 若漏掉会怎样 |
|---|---|---|---|
| BUG-001 | 状态机/清场路径遗漏 | 场景演示 + 结局语义测试 | 通关误判为失败，胜负功能不可信 |
| BUG-002 | 数值公式偷懒 | 黄金样本（期望值来自需求） | 数值模型失真 → W3 平衡结论全错 |
| BUG-003 | 周期边界 off-by-one | 序列断言 + 计数语义用例 | 技能节奏与设计不符，平衡测算偏差 |

共性结论：**凡数值/规则，先有需求文档条目与手工推导的黄金样本，再有实现与断言**；
**凡状态迁移，测试必须枚举所有可能路径**。这就是"用例-需求追踪矩阵"（docs/test-case-matrix.md）
存在的意义。
