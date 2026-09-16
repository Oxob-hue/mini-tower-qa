# MiniTower QA —— 产物全景展示（SHOWCASE）

> 一份"点开就能看懂"的作品集导览：所有产物真实存在、数字可复跑、文件位置可直达。
> 展示顺序建议：先看 ①目录与文档 → ②跑一次 10 分钟自证 → ③对照报告看数字。

---

## 1. 一句话是什么

自研轻量塔防数值引擎（纯 Python / headless / JSON 数据驱动 / seed 逐事件可复现）
＋ 覆盖 功能·数值·概率·性能·数据·AI 六面的完整质量保障体系；79 条自动化用例全绿。

## 2. 产物清单（文件即产物）

### 代码（被测对象 SUT，全部在 `mini_tower/`，零第三方运行时依赖）
| 产物 | 职责 | 亮点 |
|---|---|---|
| `models.py` | 干员/敌人/关卡/招募 数据模型 | 逻辑与数据分离 |
| `loader.py` | JSON 加载+域校验 | 坏配置加载期整体拒绝（测试左移） |
| `combat.py` | 战斗引擎（时间轴模拟） | 伤害/技能/索敌/波次/三星/超时守卫；确定性 |
| `simulator.py` | 单局/批量模拟 + 伤害占比聚合 | 蒙特卡洛底座；种子逐局推进 |
| `recruit.py` | 招募概率（软/硬保底） | 20 万抽级引擎，可复现 |
| `stats.py` | χ² / 二项 CI（纯 stdlib） | 无 scipy 也能做假设检验 |
| `analysis.py` | 理论 DPS / 膨胀 / 克制 | 静态数值校验 |
| `db.py` | SQLite 落库 | sim_runs / recruit_runs |
| `perf.py` | 性能基准/伸缩曲线/基线 | baseline.json 防回归 |
| `ai.py` | AI 三条线 + 三道闸 | schema→引擎交叉验证→审计 |

### 测试（79 条，`tests/`）
| 文件 | 条数 | 测什么 |
|---|---|---|
| test_smoke | 12 | 冒烟：引擎可跑/确定性/结局语义 |
| test_rules | 20 | W2 规则与边界（黄金样本） |
| test_probability | 10 | 招募概率 + χ²/置信区间 |
| test_balance | 10 | 平衡回归 + 膨胀/克制校验 |
| test_db | 6 | SQLite 层与 6 条 SQL 回放 |
| test_perf | 6 | 性能守卫/伸缩曲线/基线机制 |
| test_tuning | 4 | 改数值→红→调参→绿 故事线 |
| test_ai | 11 | AI 三道闸 |

### 数据与报告（docs/，均含真实运行数字）
| 报告 | 核心内容 | 关键真数 |
|---|---|---|
| `requirements.md` | 13 个 REQ 域条目 | 测试断言唯一出处 |
| `test-case-matrix.md` | 用例↔需求追踪矩阵 | 79 条全对应 |
| `defects.md` | 缺陷复盘 | BUG-001 真实 + 002/003 演练 |
| `w3-report.md` | SQL 反哺 | 高防关带真伤 0 漏怪 vs 漏 1200/1400 |
| `w4-report.md` | 性能+调参 | 0.09ms/局、伸缩比 9.9、atk≥109 |
| `w5-report.md` | AI 三道闸 | 建议 100 被实测 109 驳回 |
| `review-report.md` | 项目审查 | 清理 5 处未用导入，79/79 |
| `jd-review.md` | 逐条对照 JD | 职责①◐ ②~④● ⑤◐ |
| `internship-pack.md` | 实习投递包 | 简历摘要/话术/讲解 |
| `github-publish-guide.md` | 发布指引 | git→GitHub→简历 |

### 可执行产物（scripts/）
| 脚本 | 一键产出 |
|---|---|
| `python -m mini_tower` | headless 引擎演示 + 确定性校验 |
| `python scripts/w3_report.py` | 3600 局 → SQLite → 6 条 SQL 结论 |
| `python scripts/w4_bench.py` | 性能基线 + baseline.json |
| `python scripts/w4_tune_demo.py` | 「红→建议→绿」完整故事线 |
| `python scripts/w5_ai_demo.py` | AI 三条线 + 审计闭环 |
| `python scripts/ci_daily_balance.py` | 平衡回归/漂移检测（退出码驱动 CI 红绿） |
| `python scripts/export_allure.py` | 无 pytest 的 Allure 结果导出 |
| `.github/workflows/daily-balance.yml` | main 提交即回归 + 每日 02:00 UTC 定时；摘要进 Job Summary、产物归档 artifact |

### 已生成的环境与产物目录
| 路径 | 内容 | 是否入库 |
|---|---|---|
| `.venv/` | pytest 9.1.1 + pytest-xdist + allure-pytest | 否（.gitignore） |
| `allure-report/` | **Allure HTML 报告（79/79 passed）**，浏览器经 HTTP 打开 | 否 |
| `allure-results/` | Allure 标准结果（101 文件） | 否 |
| `git 仓库` | main @ e44a960，56 个源码/文档文件 | — |

## 3. 关键数字（可复跑对照表）

| 指标 | 实测值 | 复现命令 | 出处 |
|---|---|---|---|
| 自动化用例 | 79/79 passed | `.venv\Scripts\python.exe -m pytest tests -q` | — |
| 招募 6★ 率（无保底） | 2.0033%（CI 含 2%） | tests/test_probability.py（200 万抽） | w3 |
| χ² 拟合优度 | 0.146 < 5.991 | 同上 | w3 |
| 单局耗时 | 0.092 ms（1-1/A） | `python scripts/w4_bench.py` | w4 |
| 伸缩比（×10 敌人） | 9.3~9.9（近线性） | 同上 | w4 |
| 调参红线 | 砍30%→三星43% | `python scripts/w4_tune_demo.py` | w4 |
| 建议区间 | atk ≥ 109（≈原值 77%） | 同上（二分） | w4 |
| SQL 结论 | 高防关 0 vs 1200 漏怪 | `python scripts/w3_report.py` | w3 |
| AI 对抗 | 建议 100 → 实测 109 驳回 | tests/test_ai.py | w5 |

## 4. 面试现场 10 分钟展示流程

```powershell
cd mini-tower-qa                          # 进入仓库根目录
python -m mini_tower                       # ① 引擎演示（3 场景 + 确定性）
python -m unittest discover -s tests       # ② 79 条全绿（5 秒）
python scripts/w4_tune_demo.py             # ③ 改数值→红→建议→绿
python scripts/w5_ai_demo.py               # ④ AI 三道闸 + 审计
python scripts/ci_daily_balance.py         # ⑤ 平衡回归/漂移检测
# 浏览器(HTTP)打开 allure-report/index.html  # ⑥ 报告按 epic→feature 钻取
```

## 5. 使用建议

- **给 HR/面试官**：先 README（一句定位）→ jd-review.md（逐条对 JD）→ 跑上面 ①
- **给自己复述**：internship-pack.md（讲解+话术）→ w6-demo-script.md（视频脚本）
- **自证数字**：全部走 ③④ 与 tests，禁止背不出来的数

> 复现前提：`cd mini-tower-qa`（进入**仓库根目录**再执行；在上一级目录会找不到 `mini_tower` 模块）。
