# 项目审查报告（Review Report）

> 审查对象：MiniTower QA 仓库（v0.5.0 → 修复后 v0.5.1）
> 审查方式：静态扫描（AST/文本）+ 全量运行验证 + 产物验收
> 结论：**通过**（79/79 全绿）；发现 5 处低危问题已当场修复；给出 4 条改进建议 backlog。

---

## 1. 审查方法

| 检查项 | 手段 | 结果 |
|---|---|---|
| 未使用导入 | AST 遍历 mini_tower/*.py 的 Import 节点与 Name 引用 | 发现 5 处（见下） |
| TODO/FIXME/调试残留 | 文本扫描 | 0 处（demo/CLI 中的 print 为有意的报告输出） |
| 版本一致性 | grep 全部版本号 | __init__/变更记录一致至 v0.5.0 |
| 全量回归 | unittest discover | 79/79 通过（4.8s） |
| 语法完整性 | 全模块 import + 套件执行 | 无 SyntaxError/ImportError |
| Allure 产物验收 | 导出 → allure generate → 检查 summary/UTF-8 | 79 passed/0 failed；中文标签 UTF-8 正确 |

## 2. 发现并已修复（低危，无行为影响）

| 文件 | 问题 | 处理 |
|---|---|---|
| mini_tower/ai.py | 未使用导入 `Callable`；`cross_validate_atk_interval` 内重复 import `load_catalog` | 已删除 |
| mini_tower/analysis.py | 未使用导入 `Sequence` | 已删除 |
| mini_tower/models.py | 未使用导入 `field` | 已删除 |
| mini_tower/recruit.py | 未使用导入 `Dict` | 已删除 |

同时把"测试类 → Allure 层级"映射从 conftest 抽到 `tests/allure_map.py` 单一来源，
供 pytest 路径与 export_allure.py 共用，消除重复定义（防漂移）。

## 3. 运行验证（本机实测）

- `python -m unittest discover -s tests` → **Ran 79 tests, OK**；
- `python scripts/export_allure.py` → 导出 79 result + 21 container + environment；
- `allure generate` → `allure-report/index.html`，summary：passed=79，failed/broken/skipped=0；
- 各里程碑脚本（w3_report / w4_bench / w4_tune_demo / w5_ai_demo / ci_daily_balance）均可确定性运行。

## 4. 已知限制与建议（backlog，均为 P2/P3）

1. **参考编队与阈值常量重复**：test_balance.py / test_tuning.py / ci_daily_balance.py /
   w4_tune_demo.py 各自定义了 REQ-BAL 阈值与参考编队 → 建议抽到 `mini_tower/refs.py`
   单点维护，防口径漂移（当前各副本数值一致，已人工核对）。
2. **"写盘失败降级内存"模式三处重复**：w3_report / w4_bench / AuditLog → 可抽 `io_fallback`
   util 统一（不影响真机，纯整洁度）。
3. **可选增强**：引入 ruff + mypy 进 CI；数值域断言从 χ² 临界值表升级为 scipy 精确 p 值
   （结论不变，语义更强）；补 coverage 报告。
4. **运行环境说明**：Windows 控制台请加 `PYTHONUTF8=1` 或使用 UTF-8 终端（仓库文件均为 UTF-8）；
   pytest/allure 为可选执行层，引擎与测试本体零第三方依赖。

## 5. 对外可见性审查（README 面向招聘/访客视角，追加）

> 背景：作品集将作为简历附带的 GitHub 链接被 HR/面试官公开查看，需从"陌生访客第一眼"角度审查 README。

**发现（原文）→ 处置（README v0.5.2 招聘强化版，commit 1007ad8）**

| 原文片段 | 问题 | 处置 |
|---|---|---|
| 标题含"审查通过 v0.5.1" | 自我认证措辞 + 无意义版本号 | 删除，标题改为"塔防数值引擎的质量保障体系（作品集）" |
| 开头"简历叙事：把会测 Web 的测试升级…对标鹰角…可放心面试展示" | 求职营销话，稀释工程感 | 顶部改为纯工程定位 + 关键数字 |
| 顶部"面向招聘→jd-review→SHOWCASE"锚点 | 求职意图前置过重 | 改为"内容速览"文档索引 |
| "为什么是塔防"点名鹰角/明日方舟 | 与特定公司强绑定，限制复用 | 泛化为品类方法论表述 |
| 状态/路线区散落"演示视频/简历/面试工具包" | 暴露"应试物料" | 合并为测试组成 + 环境一条；迭代说明中性化 |
| 求职说明 | 无唯一落点 | **文末新增唯一一节**"面向游戏测试岗位"（能力定位 + jd-review/SHOWCASE 链接） |

**结论与遗留**：README 顶部 3 屏已工程化、数字可复跑；求职意图收敛为文末一节。
遗留可选优化：docs/ 中 `jd-review.md / internship-pack.md / w6-interview-kit.md` 的文件名
仍含"求职痕迹"（README 已不主动链接首页）；若需彻底中性化，可重命名并同步内部引用（P3）。

## 6. 结论

项目工程状态健康：单模块职责清晰（engine/SUT 与 QA 体系分层），79 条用例与 13 个 REQ 域
可追踪，里程碑文档齐备；对外可见性已完成"工程化优先"调整。建议后续按 §4 的 backlog 条目
（refs 抽取 → lint 进 CI）与 §5 遗留项（可选重命名）渐进打磨即可。
