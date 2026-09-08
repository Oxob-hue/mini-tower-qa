# MiniTower QA —— 塔防数值引擎的质量保障体系（游戏测试作品集）

> **MiniTower QA** 是一套可完整运行、结论可复现的**游戏数值质量保障体系**作品集：
> 以自研轻量塔防数值引擎（纯 Python、headless、JSON 数据驱动、seed 逐事件可复现）为被测对象，
> 覆盖 需求条目化 → 用例设计 → 自动化 → 蒙特卡洛与假设检验 → 性能基线 → SQL 数据反哺 → AI 辅助校验 的
> 全链路，并在其上完整演练了「发现缺陷 → 定位根因 → 给出可执行修复建议 → 回归验证」的闭环。

> 关键数字（全部可在本仓库复跑）：**79 条自动化用例** · 招募概率 **200 万抽**假设检验 ·
> **3600 局**模拟落库与 SQL 分析 · 单局 **0.09ms** 性能基准 · 调参案例给出 **atk ≥ 109** 可执行区间。

---

## 内容速览

| 想了解 | 看这里 |
|---|---|
| 被测对象规则与 13 个需求域 | [docs/requirements.md](docs/requirements.md) |
| 用例 ↔ 需求 追踪矩阵 | [docs/test-case-matrix.md](docs/test-case-matrix.md) |
| 缺陷复盘（红 → 根因 → 修复 → 回归） | [docs/defects.md](docs/defects.md) |
| 真实数据报告（SQL / 性能 / AI） | [docs/w3-report.md](docs/w3-report.md) · [w4-report.md](docs/w4-report.md) · [w5-report.md](docs/w5-report.md) |
| 产物全景与演示流程 | [docs/SHOWCASE.md](docs/SHOWCASE.md) |
| 项目质量审查 | [docs/review-report.md](docs/review-report.md) |

## 为什么选择"塔防数值引擎"作为被测对象

塔防/肉鸽品类天然具备**可数值化的规则系统**——伤害公式与防御结算、暴击乘区、技能触发节奏、
索敌规则、波次生成、保底与克制设计、三星/胜负条件——每一类都适合用"测试与统计"去验证，
也最能体现游戏测试岗位需要的**数值测试**能力。

设计原则：

- **确定性**：唯一随机源为暴击判定且受 seed 控制 → 每一条统计结论都可逐事件复现；
- **数据驱动**：干员/敌人/关卡/招募全部 JSON 外置，改一行配置即一次可回归的数值改动；
- **黄金样本先行**：用例期望值来自需求文档手工推导，而非看实现抄写；
- **可复跑交付**：79 条测试 + 各报告脚本一条命令运行。

## 当前状态（79/79 测试全绿）

- 测试组成：冒烟 12 · 规则/边界 20 · 概率 10 · 平衡/膨胀 10 · 数据层 6 · 性能 6 · 调参 4 · AI 11（`tests/`）
- 运行器：stdlib `unittest` 零依赖全量回归；`.venv`（pytest + allure-pytest）用于 marker 筛选与 Allure 报告
- 环境：`.venv` 已就绪；`allure-report/` 可在本地生成（见 [w6-allure-guide.md](docs/w6-allure-guide.md)，HTML 需以 HTTP 方式打开）
- 版本：0.5.1（变更记录见 [requirements.md](docs/requirements.md) 文末）

## 目录结构

```
mini-tower-qa/
├── docs/                          # 需求说明书 / 追踪矩阵 / 缺陷复盘 / 数据报告 / 导览
├── mini_tower/                    # 被测对象 SUT（纯 Python，无第三方运行时依赖）
│   ├── models.py · loader.py · combat.py · simulator.py
│   ├── recruit.py · stats.py · analysis.py
│   ├── db.py · perf.py · ai.py · cli.py
│   └── data/                      # operators / enemies / stages / recruit JSON 配置
├── sql/analysis.sql               # 6 条平衡/概率分析查询
├── scripts/                       # 报告与演示脚本（w3_report / w4_bench / w4_tune_demo / w5_ai_demo / ci_daily_balance / export_allure）
├── tests/                         # 79 条用例（8 个测试文件 + conftest/allure_map）
├── .github/workflows/daily-balance.yml   # 每日定时全量回归 + 平衡漂移检测
├── results/ · allure-results/ · allure-report/ · .venv/   # 运行产物（gitignore）
└── pytest.ini                     # marker 注册
```

## 快速开始

```bash
# 0) 进入项目目录（模块基于当前目录导入）
cd D:\GameProtect\mini-tower-qa

# 1) 引擎演示：3 个参考场景 + 确定性校验
python -m mini_tower

# 2) 全量测试（79 条，两条运行器等价）
python -m unittest discover -s tests
.venv\Scripts\python.exe -m pytest tests -q

# 3) 数据报告：模拟/招募 → SQLite → 6 条分析 SQL
python scripts/w3_report.py

# 4) 性能基线 + 「改数值→红→建议→绿」调参演示
python scripts/w4_bench.py
python scripts/w4_tune_demo.py

# 5) AI 辅助（本地规则提供者离线可跑；配 AI_HTTP_URL + AI_API_KEY 可切真实 LLM）
python scripts/w5_ai_demo.py

# 6) 每日回归（CI 用，退出码驱动红绿）
python scripts/ci_daily_balance.py
```

> 引擎/测试/脚本本体零第三方依赖（Python ≥ 3.10，stdlib 即可全量回归）；
> `.venv` 仅用于 pytest 生态（marker 筛选、Allure），已 gitignore。

## 引擎规则速览（完整条目见需求说明书）

| 规则 | 内容 |
|---|---|
| 物理伤害 | `max(atk − def, ⌈atk×5%⌉)`（REQ-DMG-001/004） |
| 真实伤害 | 全额 = atk，无视防御（REQ-DMG-002） |
| 暴击 | 防御结算后 × crit_mult，向下取整（REQ-DMG-003） |
| 技能 | 累计成功命中 skill_every 次后，下次命中 = atk×skill_mult 且无视防御（REQ-SKL-001） |
| 索敌 | 范围内选最接近我方终点的敌人；无目标则攻击落空（REQ-TGT-001） |
| 波次 | start_time 起按 interval 生成 count 个（REQ-STG-001） |
| 胜负 | 漏怪扣生命、归零判负；清场胜利；剩余生命 ≥ 三星线得三星（REQ-STG-003/004/005） |
| 确定性 | seed 固定 → 逐事件一致（REQ-SIM-001） |
| 招募 | 基础概率 + 软保底 + 第 cap 抽硬保底（REQ-PRB-001..007） |

## 迭代说明

本作品按「需求 → 规则测试 → 数值/概率/数据 → 性能/调参 → AI 辅助/CI → 报告收尾」六个阶段迭代完成，
每阶段均有独立交付与真实数据报告（docs/w3~w5-report.md、review-report.md）。所有内容为原创实现，
玩法规则仅作方法学载体，不包含任何第三方游戏素材。

---

## 面向游戏测试岗位

本仓库定位为**游戏测试方向的作品集**，聚焦游戏 QA 的几项核心能力：功能与边界用例设计、
数值与概率验证、性能基准、自动化与 CI、数据反哺调优、AI 辅助（含防幻觉校验）。
对目标岗位要求（职责/技能）的**逐条对照**见 [docs/jd-review.md](docs/jd-review.md)；
作品集讲解与常见问答见 [docs/SHOWCASE.md](docs/SHOWCASE.md)。
