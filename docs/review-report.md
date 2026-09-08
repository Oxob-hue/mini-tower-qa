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

## 5. 结论

项目工程状态健康：单模块职责清晰（engine/SUT 与 QA 体系分层），79 条用例与 13 个 REQ 域
可追踪，里程碑文档齐备；本轮仅清理 5 处低危未用导入。建议后续按 §4 的 backlog 条目
（refs 抽取 → lint 进 CI）渐进打磨即可。
