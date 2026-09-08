# MiniTower QA —— 游戏数值质量保障作品集项目（W1–W6 全部完成，审查通过 v0.5.1）

> **一句话**：自研轻量塔防数值引擎 **MiniTower** 及其质量保障体系。
> 简历叙事：把「会测 Web 的测试」升级为「懂游戏、会用数据说话的游戏测试」——
> 对标鹰角网络「游戏测试」校招 JD 的 功能 / **数值** / **性能** / 自动化 / **AI 辅助** 能力面。
> 规则设计全部原创（玩法框架致敬塔防品类），不涉及任何游戏素材或协议，可放心面试展示。

> 🔗 GitHub：https://github.com/Oxob-hue/mini-tower-qa（作品集仓库）
> 🎯 面向招聘：先看 [docs/jd-review.md](docs/jd-review.md)（逐条对照岗位 JD）→
> [docs/SHOWCASE.md](docs/SHOWCASE.md)（产物全景展示）→ 79 条测试全部可现场复跑

---

## 为什么是塔防？

鹰角是塔防赛道最具代表性的厂商（《明日方舟》）。塔防天然具备
**可数值化的规则系统**（伤害公式、防御结算、技能触发、波次生成、三星条件），
是「用测试与统计验证数值」的最佳题材——这正是通用 Web 测试简历里最稀缺的能力。

## 当前状态（W1–W6 全部完成 ✅，79 条测试全绿）

- ✅ 需求说明书（13 个需求域 REQ-CFG/DMG/SKL/TGT/STG/SIM/BAL/PRB/ANL/DATA/PERF/AI/CI）
- ✅ W1 引擎核心 + 确定性 + 冒烟 12 条（真实缺陷 BUG-001 修复）
- ✅ W2 规则/边界用例矩阵 20 条 + 缺陷复盘 BUG-002/003
- ✅ W3 数值三件套 + 数据层 26 条（概率假设检验 / 平衡回归 / 膨胀校验 / SQLite + 6 SQL）
- ✅ W4 性能与调参 10 条（基准 0.09–0.19ms/局、伸缩比 9.9、baseline 防回归、调参故事线）
- ✅ W5 AI 辅助 + CI 11 条（三道闸：schema / 引擎交叉验证 / 审计；每日回归 GitHub Actions）
- ✅ W6 收尾：Allure 报告接入（pytest.ini + tests/conftest.py 层级映射）、演示视频脚本、
  简历/面试工具包（`docs/w6-*.md`）
- ✅ 审查通过（v0.5.1）：静态扫描清理 5 处未用导入、Allure 报告已生成于 `allure-report/`
  （79/79 passed），审查报告 `docs/review-report.md`
- ✅ 自带测试环境 `.venv`（pytest 9.1.1 + pytest-xdist + allure-pytest）：开箱即用 pytest
  marker 筛选与 allure-pytest 报告；引擎/测试本体仍零第三方依赖（stdlib unittest 可全量回归）
- 追踪矩阵：`docs/test-case-matrix.md`；里程碑报告：`docs/w3-report.md`~`docs/w6-*.md`

## 目录结构

```
mini-tower-qa/
├── docs/
│   ├── requirements.md          # 需求说明书（13 域条目编号，测试断言引用出处）
│   ├── test-case-matrix.md      # 用例-需求追踪矩阵（RTM，W1~W5）
│   ├── defects.md               # 缺陷复盘（BUG-001~003）
│   ├── review-report.md         # 项目审查报告（v0.5.1）
│   ├── w3-report.md / w4-report.md / w5-report.md   # 真实数据报告
│   ├── w6-allure-guide.md       # Allure 报告生成指南
│   ├── w6-demo-script.md        # 2–3 分钟演示视频脚本
│   ├── w6-interview-kit.md      # 简历条目 / 15 条追问应答 / 行为准备
│   ├── jd-review.md             # 按招聘信息逐条对照审查
│   ├── internship-pack.md       # 实习版简历摘要 + 执行导向话术 + 项目深度讲解
│   └── SHOWCASE.md              # 产物全景展示（文件清单/真实数字/展示流程）
├── mini_tower/                  # 被测对象 SUT（纯 Python，无第三方依赖）
│   ├── models.py                #   数据模型（逻辑与数据分离）
│   ├── loader.py                #   JSON 加载 + 域校验（坏配置加载期拒绝）
│   ├── combat.py                #   战斗引擎（伤害/技能/索敌/波次/三星）
│   ├── simulator.py             #   单局/批量统计 + 干员伤害占比聚合
│   ├── recruit.py               #   招募概率系统（保底/软保底，seed 可复现）
│   ├── stats.py                 #   统计工具（χ² 拟合优度、二项 CI，纯 stdlib）
│   ├── analysis.py              #   数值分析（理论 DPS/膨胀比/克制比）
│   ├── db.py                    #   SQLite 落库与查询层
│   ├── perf.py                  #   性能基准/伸缩曲线/基线比对（REQ-PERF）
│   ├── ai.py                    #   AI 辅助三条线 + 三道闸（schema/引擎交叉验证/审计）
│   ├── cli.py                   #   headless 命令行入口
│   └── data/                    #   全部数值配置（改一行 = 一次数值改动）
│       ├── operators.json       #   干员
│       ├── enemies.json         #   敌人
│       ├── stages.json          #   关卡（波次/生命/三星线）
│       └── recruit.json         #   招募池（概率/保底规则）
├── .github/workflows/
│   └── daily-balance.yml        # 每日 02:00 UTC 全量测试 + 平衡回归 + 产物归档
├── sql/
│   └── analysis.sql             # 6 条平衡/概率分析查询（Q1~Q6）
├── scripts/
│   ├── export_allure.py         # Allure 结果导出器（无 pytest，纯 stdlib）
│   ├── w3_report.py             # 模拟/招募 → SQLite → SQL 回放（报告生成）
│   ├── w4_bench.py              # 性能基线生成/比对（baseline.json）
│   ├── w4_tune_demo.py          # 「改数值→红→调参→绿」故事线演示
│   ├── w5_ai_demo.py            # AI 三条线 + 三道闸演示
│   └── ci_daily_balance.py      # 每日平衡回归 + 漂移检测（退出码驱动 CI）
├── results/                     # 运行产物（w3.db 等，不入库）
├── .venv/                       # 自带 pytest/allure-pytest 环境（Python venv，不入库）
├── allure-results/              # Allure 原始结果（可再生成，不入库）
├── allure-report/               # Allure HTML 报告（已生成：79/79 passed，不入库）
└── tests/
    ├── allure_map.py            # 测试类 → epic/feature/marker 单一来源（conftest 与导出器共用）
    ├── conftest.py              # pytest 钩子：Allure 层级/标记映射（无 allure 时静默）
    ├── test_smoke.py            # W1 冒烟（12 条）
    ├── test_rules.py            # W2 规则/边界用例矩阵（20 条）
    ├── test_probability.py      # W3 概率域（10 条）
    ├── test_balance.py          # W3 平衡/膨胀（10 条）
    ├── test_db.py               # W3 数据层（6 条）
    ├── test_perf.py             # W4 性能守卫/伸缩/基线机制（6 条）
    ├── test_tuning.py           # W4 调参故事线回归（4 条）
    ├── test_ai.py               # W5 AI 三道闸（11 条）
    └── fixtures/bad_config/     # 坏配置夹具（验证加载期拦截）

pytest.ini                          # 标记注册（smoke/rules/probability/balance/data/perf/tuning/ai）
```

## 快速开始

```bash
# 1) 演示模式：参考编队通关 + 确定性校验 + 批量吞吐（无需任何安装）
python -m mini_tower

# 2) 指定一局
python -m mini_tower --stage 1-2 --team sniper_a,caster_c,storm_d,frost_f --seed 42

# 3) 批量统计（W3 平衡断言的雏形：通关率/三星率/耗时分布）
python -m mini_tower --stage 1-2 --team sniper_a,caster_c,storm_d,frost_f --rounds 200

# 4) 测试（两套运行器等价）
python -m unittest discover -s tests -v               # stdlib（零依赖）
#    全量 79 条 = 12 冒烟 + 20 规则 + 10 概率 + 10 平衡 + 6 数据层 + 6 性能 + 4 调参 + 11 AI
.venv\Scripts\python.exe -m pytest tests -q           # pytest（仓库自带 .venv，含 allure-pytest）
.venv\Scripts\python.exe -m pytest tests -m balance -q   # 按需求域筛选（标记由 conftest 自动打）

# 5) W3 数据报告：模拟/招募 → SQLite → 6 条 SQL 回放（results/w3.db）
python scripts/w3_report.py

# 6) W4 性能基线（results/baseline.json）与调参故事线
python scripts/w4_bench.py
python scripts/w4_tune_demo.py

# 7) W5 AI 三条线 + 每日平衡回归（CI 用；配 AI_HTTP_URL+AI_API_KEY 可切真实 LLM）
python scripts/w5_ai_demo.py
python scripts/ci_daily_balance.py

# 8) W6 Allure 报告（路径 A/B 等价；报告已生成于 allure-report/）
python scripts/export_allure.py --out allure-results   # 路径A：无 pytest 的导出器（纯 stdlib）
allure generate allure-results -o allure-report --clean
# 路径B：.venv 自带 pytest + allure-pytest
#   .venv\Scripts\python.exe -m pytest tests --alluredir=allure-results
#   allure generate allure-results -o allure-report --clean
```

- 引擎/测试/脚本本体**零第三方依赖**（stdlib unittest 即可全量回归）；
  `.venv` 仅在需要 pytest 生态（marker 筛选、allure-pytest 报告）时使用，已 gitignore。

引擎只依赖 Python 标准库，`python>=3.10` 即可（开发于 3.14）。

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

## 数据驱动：怎么加一个干员 / 一张关卡

1. 在 `mini_tower/data/operators.json` 追加一个对象（id 全局唯一、数值在域内）；
2. 在 `stages.json` 引用新敌人/新波次；
3. 重新跑 `python -m unittest discover -s tests -v` —— loader 的校验就是
   「坏配置不允许进引擎」的第一道测试门（REQ-CFG-004）；
4. W2 起，规则测试将逐条断言每个新配置的行为与设计目标一致。

## Roadmap

- ✅ **W1–W6 全部完成 + 审查通过（v0.5.1，79 条测试全绿）**：引擎/冒烟 → 规则矩阵与缺陷复盘 →
  数值三件套 + SQLite → 性能基线/调参故事线 → AI 三道闸 + 每日回归 CI →
  Allure 报告（`allure-report/index.html`）/演示脚本/面试工具包
- 面试素材索引：`docs/w6-demo-script.md`（演示视频）、`docs/w6-interview-kit.md`（简历+追问）、
  `docs/test-case-matrix.md`（用例↔REQ）、`docs/defects.md`（缺陷复盘）、`docs/review-report.md`（审查）

---

> 参考：求职定位与完整制作方案见仓库外文档《鹰角游戏测试校招-项目方向与制作方案.md》。
