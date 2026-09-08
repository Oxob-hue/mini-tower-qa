# MiniTower 需求说明书（v0.1）

| 项 | 内容 |
|---|---|
| 文档版本 | v0.1（W1 初版） |
| 被测对象 | MiniTower 塔防数值引擎（纯 Python headless，JSON 数据驱动） |
| 文档定位 | 需求条目化 + 用例-需求追踪（RTM）的依据；测试断言的**唯一出处** |
| 编号规则 | REQ-{域}-{序号}；域 = CFG 配置 / DMG 伤害 / SKL 技能 / TGT 索敌 / STG 关卡 / SIM 模拟 / BAL 设计目标 |

> 变更原则：任何“改需求”必须先改本文档并留评审记录（见文末变更记录），测试随之更新。
> 标注 **[W2/W3/W4 实现]** 的条目为后续迭代计划，本期（W1）不实现。

---

## 1. 被测对象概述

一条路径：敌人从出生点（位置 0）以 `speed` 米/秒走向我方终点（`path_length`），
到达则造成 `leak` 点生命损失；干员全程在场，按攻击间隔对**射程区间内最接近终点**的敌人输出。
关卡在我方生命归零前清空全部敌人即胜利，胜利时剩余生命 ≥ `three_star_lives` 得三星。
随机性仅来自暴击判定，受 seed 控制（整局可复现）。

---

## 2. 需求条目

### 2.1 配置与数据（CFG）

| 编号 | 需求 |
|---|---|
| REQ-CFG-001 | 干员/敌人/关卡 id 在同一文件内全局唯一且非空 |
| REQ-CFG-002 | 数值域校验：干员 rarity∈{3..6}、atk∈[1,10⁶] 整数、interval∈(0.01,600]、0≤range_lo<range_hi、crit_rate∈[0,1]、crit_mult≥1、skill_every≥0 整数、skill_mult≥1；敌人 hp≥1/defense≥0/speed>0/leak≥1 整数；关卡 path_length>0、1≤base_hp、1≤three_star_lives≤base_hp；波次 count≥1、start_time≥0、interval>0 |
| REQ-CFG-003 | 引用完整性：关卡波次的 enemy_id 必须存在于敌人表；编队引用的干员 id 必须存在且不重复 |
| REQ-CFG-004 | 校验失败 = 加载失败：坏配置在加载期以 ConfigError 拒绝，不允许进入战斗引擎（测试左移） |
| REQ-CFG-005 | 数值类型严格：atk/hp/defense/leak/count 等必须为 int，禁止 1.0 混入（防止隐性取整 bug） |

### 2.2 伤害结算（DMG）

| 编号 | 需求 |
|---|---|
| REQ-DMG-001 | 物理伤害 = max(atk − defense, ⌈atk×5%⌉)，结算顺序：先减免后暴击，最终向下取整 |
| REQ-DMG-002 | 真实伤害（dmg_type=true）不参与防御减免，全额 = atk |
| REQ-DMG-003 | 暴击：每次攻击独立判定（概率 crit_rate），命中后最终伤害 ×crit_mult 向下取整；伤害下限 1 |
| REQ-DMG-004 | 任何一次有效命中伤害 ≥ 1（物理下限 5% 与暴击乘区共同保证） |
| REQ-DMG-005 | 攻击节拍：两次攻击间隔恒为 interval；首次攻击前摇 = interval；射程内无目标时攻击落空但不改节拍 |
| REQ-DMG-006 | 攻击选定目标后锁定结算：目标中途死亡则该次伤害不转移（无“鞭尸转移”） |
| REQ-DMG-007 | 同一时刻事件顺序按入队先后：生成 < 到达/攻击；敌人到达终点即结算 leak 并离场，不再受攻击影响 |

### 2.3 技能（SKL）

| 编号 | 需求 |
|---|---|
| REQ-SKL-001 | 干员累计**成功命中** skill_every 次后，下一次成功命中结算为技能：伤害 = atk×skill_mult 且**无视防御**；命中计数含技能命中本身（即第 N、2N、3N… 次命中均为技能） |
| REQ-SKL-002 | skill_every=0 表示无技能，永不触发 |
| REQ-SKL-003 | 技能同样受暴击判定影响（REQ-DMG-003 的乘区叠加） |
| REQ-SKL-004 | 技能不改变攻击节拍（REQ-DMG-005） |

### 2.4 索敌（TGT）

| 编号 | 需求 |
|---|---|
| REQ-TGT-001 | 开火瞬间，在 [range_lo, range_hi]（米）内选择**位置最大**（最接近我方终点）的存活敌人；区间内无敌人则本次攻击落空 |
| REQ-TGT-002 | 敌人位置 = (当前时刻 − 生成时刻) × speed，线性推进 |

### 2.5 关卡规则（STG）

| 编号 | 需求 |
|---|---|
| REQ-STG-001 | 波次生成：每波从 start_time 起按 interval 生成 count 个同种敌人 |
| REQ-STG-002 | 敌人到达 path_length → 我方损失 leak 点生命，敌人离场 |
| REQ-STG-003 | 我方生命归零 → 立即判负（defeat_leak），终止模拟 |
| REQ-STG-004 | 全部敌人已生成且场上无存活敌人 → 胜利（victory），结束时刻 = 最后一击时刻 |
| REQ-STG-005 | 三星：胜利时剩余生命 ≥ three_star_lives |
| REQ-STG-006 | 模拟超过 max_time（默认 600s 游戏内时间）仍未分胜负 → 判负（timeout），防死循环守卫 |

### 2.6 模拟器（SIM）

| 编号 | 需求 |
|---|---|
| REQ-SIM-001 | 确定性：固定 seed → 同一配置逐事件完全一致（事件含 t/kind/subject/detail） |
| REQ-SIM-002 | headless：不依赖 GUI/网络；引擎仅用 Python 标准库 |
| REQ-SIM-003 | 批量 N 局：每局 seed = master_seed + i；汇总 通关率/三星率/平均剩余生命/平均时长/p99 时长 |
| REQ-SIM-004 | 全量事件日志（spawn/attack/skill/kill/leak/end）保留，供规则断言与覆盖率统计 **[W2 用于覆盖率]** |
| REQ-SIM-005 | 单局默认 600s 上限内时间与内存有界，批量化可扩展（pytest-xdist / 多进程） **[W4]** |

### 2.7 设计目标与参考编队（BAL，数值基线初稿）

> 定位：W3 数值回归断言的“区间来源”。W1 先固化**可复现的定性结论**，
> 数值区间在 W3 用蒙特卡洛 + 基线校准后锁定为正式断言。

| 编号 | 设计目标 |
|---|---|
| REQ-BAL-001 | 关卡 1-1：参考编队 A（苍羽 sniper_a / 磐石 guard_b / 焰雀 caster_c / 惊雷 storm_d）确定性三星通关；通关时长基准 ≈28.0s（W3 以 2000 局锁定区间 [24,33]，防"过快=数值超标/过慢=输出不足"） |
| REQ-BAL-002 | 关卡 1-2：参考编队 B（苍羽 / 焰雀 / 惊雷 / 寒潭 frost_f）确定性通关且三星（W3 锁定：clear_rate/star_rate ≥0.99，时长基准 ≈55.2s ∈ (52,58)） |
| REQ-BAL-003 | 数值克制关系成立：铁壳 armor（defense=100）显著压制低攻物理干员（单近卫输出不足 → 漏怪），真实伤害/技能是克制手段（量化见 REQ-ANL-002） |
| REQ-BAL-004 | 参考编队全流程耗时 < 60s 游戏时间（供 W4 性能基线参考） |
| REQ-BAL-005 | 临界编队（磐石 guard_b + 惊雷 storm_d）@1-2 三星率设计目标 ≥95%；惊雷 atk 建议下限 ≥109（≈ 原值 77%，由 1000 局二分模拟给出）。**数值改动若把三星率压到目标线以下 → 平衡测试红**，须回滚或按建议区间调整（实测：atk 140→98 时三星率 100%→43.1%；采纳 112 → 100%） |

### 2.8 招募概率（PRB，W3 新增）

| 编号 | 需求 |
|---|---|
| REQ-PRB-001 | 确定性：固定 seed → 出货序列逐次可复现 |
| REQ-PRB-002 | 关闭保底时，各档位总体出货率与声明概率一致（χ² 拟合优度 df=2、α=0.05；6★ 观测率落在声明值 95% 二项置信区间内） |
| REQ-PRB-003 | 硬保底：距上次 6★ 连续 cap−1 抽未出 → 第 cap 抽强制 6★；任意含首尾的 6★ 间隔 ≤ cap |
| REQ-PRB-004 | 软保底：soft_pity_start 起 6★ 概率每抽 +soft_pity_step，单调不减，封顶 1.0 |
| REQ-PRB-005 | 出货 6★ 后保底计数归零，重新累计 |
| REQ-PRB-006 | 配置校验：p6+p5+p4=1、稀有度越高概率越低、cap=0 表示禁用或 cap≥1、soft_pity_start ≤ cap |
| REQ-PRB-007 | 开启保底后整体 6★ 率 > 基础概率（保底确实抬升出货，防"声明与实现不一致"） |

### 2.9 数值分析口径（ANL，W3 新增）

| 编号 | 需求 |
|---|---|
| REQ-ANL-001 | 强度跨度受控（防数值膨胀）：0 防目标全干员理论 DPS max/min < 3.2；6★ 均值 / 4★ 均值 ≤ 3.0 |
| REQ-ANL-002 | 克制量化（承接 REQ-BAL-003）：def=100 下真实伤害干员相对物理低攻干员理论 DPS 优势 ≥ 10 倍 |
| REQ-ANL-003 | 环境区分度：def=100 下全干员理论跨度 ≥ 8 倍（高防图有战术分层，而非全员同质） |
| REQ-ANL-004 | 理论口径一致性：分析公式与引擎同源（同公式/同取整/同触发规则）；真实伤害 dps 与目标防御无关 |

### 2.10 数据落库与分析（DATA，W3 新增）

| 编号 | 需求 |
|---|---|
| REQ-DATA-001 | 每局模拟落 sim_runs：stage/team/seed/结局/剩余生命/时长/漏怪/总伤/干员伤害占比（JSON），seed 固定可回放 |
| REQ-DATA-002 | 招募模拟落 recruit_runs，按保底开关分组汇总 |
| REQ-DATA-003 | 分析 SQL 以文件维护（sql/analysis.sql），可在任意 SQLite 客户端回放 |
| REQ-DATA-004 | 聚合自洽：json_each 展开的 Σ干员伤害 == 明细 dmg_total（Q3 与表一致） |

### 2.11 性能基线（PERF，W4 新增）

| 编号 | 需求 |
|---|---|
| REQ-PERF-001 | 绝对守卫：参考编队单局墙钟 < 5ms（实测 ≈0.09–0.19ms），防灾难性回归（如死循环） |
| REQ-PERF-002 | 单局峰值内存有界（tracemalloc，参考场景 ≈9–17KB；断言 <100MB） |
| REQ-PERF-003 | 基线防回归：当前 ms/局 ≤ baseline.json 记录 ×1.5（容忍系数防机器波动误报） |
| REQ-PERF-004 | 伸缩曲线：同构压力关敌人 ×10 → 总耗时近 ×10（实测伸缩比 ≈9.3–9.9；断言 ∈(5,25)，防 O(n²) 退化） |
| REQ-PERF-005 | 基线文件含机器指纹（machine_info），跨机器不得混用比对 |
| REQ-PERF-006 | 基线生成/比对脚本化（scripts/w4_bench.py），供 CI 每日对比（W5 落地） |

### 2.12 AI 辅助测试（AI，W5 新增）

| 编号 | 需求 |
|---|---|
| REQ-AI-001 | 结构化输出 + schema 校验：AI 回复必须为合法 JSON 且字段/类型/枚举符合契约；非法输出拒绝并记审计，不进入后续流程 |
| REQ-AI-002 | 需求→测试点/边界：产出含 req_hint/focus/boundary/test；与人已覆盖集合比对，**量化"AI 补充的新检查点数"**；人工复核后采纳入库 |
| REQ-AI-003 | 数值改动→风险评估：输出 risk∈{high,medium,low}、理由、建议数值区间 |
| REQ-AI-004 | 引擎交叉验证（防幻觉核心）：AI 建议区间须经真实模拟校准；AI 下限低于实测达标线 → 标记不一致并自动修正（correction 留痕） |
| REQ-AI-005 | 失败日志聚类：按根因倾向聚类（漏怪/崩盘/超时等）；与真实根因比对输出准确率 |
| REQ-AI-006 | 审计日志：每条产出记录 capability/provider/prompt/raw/schema_ok/engine_verified/human_review（pending→approved/rejected），可落盘 jsonl |
| REQ-AI-007 | 提供者可插拔：默认本地规则提供者（离线确定性，CI/演示可复现）；配置 AI_HTTP_URL+AI_API_KEY 后切换真实 LLM，三道闸不变 |

### 2.13 每日回归（CI，W5 新增）

| 编号 | 需求 |
|---|---|
| REQ-CI-001 | 每日定时（02:00 UTC）跑全量测试 + 平衡回归（GitHub Actions，.github/workflows/daily-balance.yml） |
| REQ-CI-002 | 平衡漂移检测脚本（scripts/ci_daily_balance.py）以退出码驱动 CI 红绿；seed 固定、机器无关 |
| REQ-CI-003 | CI 产物（SQLite 库/基线/报告）作为 artifact 归档，支持事后比对 |

---

## 3. 迭代状态（W1–W6 全部完成）

| 迭代 | 完成内容 |
|---|---|
| W1 | 需求条目化、引擎核心、确定性、冒烟 12 条；修复真实缺陷 BUG-001 |
| W2 | 规则/边界用例矩阵 20 条（DMG/SKL/TGT/STG）、缺陷演练 BUG-002/003、RTM 与复盘文档 |
| W3 | 招募概率系统与假设检验 10 条、平衡回归与膨胀校验 10 条、SQLite 数据层 6 条、6 条分析 SQL、数据报告 |
| W4 | 性能基准与基线机制 6 条（perf.py + scripts/w4_bench.py）；「改数值→平衡红→调参→绿」故事线 4 条（REQ-BAL-005，scripts/w4_tune_demo.py）；伸缩曲线近线性 |
| W5 | AI 辅助三条线 + 三道闸 11 条（ai.py + scripts/w5_ai_demo.py）；每日回归 CI（ci_daily_balance.py + GitHub Actions 工作流） |
| W6 | Allure 报告接入（pytest.ini + tests/conftest.py + w6-allure-guide）；演示视频脚本（w6-demo-script）；简历/面试工具包（w6-interview-kit） |

---

## 4. 变更记录

| 版本 | 日期 | 变更 | 评审 |
|---|---|---|---|
| v0.1 | W1 | 初版：战斗/关卡/模拟规则条目化；锁定参考编队 A/B 与克制关系设计目标 | 作者自评通过（面试前由导师/同行二次评审） |
| v0.1.1 | W1 | **缺陷修复（引擎）**：清场判胜（REQ-STG-004）原先只挂在“击杀”路径，最后一只是“漏怪离场”时会空转到 max_time 误判失败；改为每事件后统一判定。由场景 3（单近卫打 1-2）暴露，修复后回归通过（见 combat.py 头注） | 修复人：作者；回归：tests 12/12 通过 |
| v0.1.2 | W2 | 新增规则/边界用例矩阵 20 条（DMG/SKL/TGT/STG 行为级，见 docs/test-case-matrix.md）；缺陷演练与复盘 BUG-002/003 全部修复并锁定回归用例（docs/defects.md）；引擎最终代码相对 v0.1.1 无净变更 | 回归：tests 32/32 通过 |
| v0.2.0 | W3 | 新增 PRB/ANL/DATA 需求域；实现招募概率系统（recruit.py + recruit.json）与假设检验；平衡回归/膨胀校验（test_balance 10 条）；SQLite 数据层 + sql/analysis.sql（test_db 6 条）；REQ-BAL-001/002 锁定实测区间 | 回归：tests 58/58 通过 |
| v0.3.0 | W4 | 新增 PERF 需求域与 REQ-BAL-005；性能基准 perf.py + scripts/w4_bench.py（基线机制 6 条）；「改数值→红→调参→绿」故事线（test_tuning 4 条 + scripts/w4_tune_demo.py）；伸缩曲线近线性验证 | 回归：tests 68/68 通过 |
| v0.4.0 | W5 | 新增 AI/CI 需求域；AI 辅助三条线 + 三道闸（ai.py + scripts/w5_ai_demo.py，test_ai 11 条）；每日回归 CI（ci_daily_balance.py + GitHub Actions）；AI 新增检查点已审纳入 W6 backlog | 回归：tests 79/79 通过 |
| v0.5.0 | W6 | Allure 接入（pytest.ini 标记 + tests/conftest.py epic/feature/story 映射 + w6-allure-guide）；演示视频脚本（w6-demo-script）；简历与面试工具包（w6-interview-kit）；顶层方案文档定稿（真实数字填表） | 回归：tests 79/79 通过 |
| v0.5.1 | 审查+Allure 报告 | 项目审查：清理 5 处未用导入、抽取 allure_map 单一来源；新增无 pytest 的 Allure 导出器 scripts/export_allure.py 并生成 allure-results + allure-report（79/79 passed）；审查报告 docs/review-report.md | 回归：tests 79/79 通过 |
