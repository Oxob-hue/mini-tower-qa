# Allure 报告接入指南（W6 / 审查后更新 / 已内置 .venv）

> 仓库已随附 **`.venv`（Python venv，已装 pytest 9.x + pytest-xdist + allure-pytest）**，
> 开箱即可运行 pytest 路径；同时保留一条**不依赖 pytest/allure-pytest** 的导出路径
> （scripts/export_allure.py）。两条路径产出的 allure-results 等价。

## 0. 已经生成好的报告

`allure-report/index.html`（pytest 路径最新生成：79/79 passed）。查看方式：

```bash
allure open D:\GameProtect\mini-tower-qa\allure-report   # 起本地服务打开
# 或直接用浏览器打开 allure-report/index.html（静态页面）
```

## 0b. 激活仓库自带环境（Windows PowerShell）

```powershell
D:\GameProtect\mini-tower-qa\.venv\Scripts\Activate.ps1   # 激活后直接 python -m pytest ...
# 或不用激活，直接全路径调用：
D:\GameProtect\mini-tower-qa\.venv\Scripts\python.exe -m pytest tests -q
```

## 1. （可选）自行重建环境

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # pytest/pytest-xdist/allure-pytest
# Allure 命令行（Windows 可用 scoop: scoop install allure；macOS: brew install allure）
allure --version
```

## 2. 生成并打开报告（路径 A：无 pytest，仓库自带导出器）

```bash
# 直接运行 unittest 并把结果写成标准 allure-results（纯标准库）
python scripts/export_allure.py --out allure-results
# 生成静态站点并打开
allure generate allure-results -o allure-report --clean
allure open allure-report
```

## 2b. 生成并打开报告（路径 B：pytest + allure-pytest）

```bash
# 执行全量用例并把结果写到 allure-results/
python -m pytest tests --alluredir=allure-results

# 生成静态站点并打开
allure generate allure-results -o allure-report --clean
allure open allure-report          # 或直接浏览器打开 allure-report/index.html
```

> 两条路径产出的 allure-results 结构一致（result + container + environment），
> 层级（epic/feature/marker）共用 tests/allure_map.py 单一来源。

按需求域筛选（标记已通过 tests/conftest.py 自动打到用例上）：

```bash
python -m pytest tests -m balance -v            # 只看数值/平衡域
python -m pytest tests -m "ai or perf" -v       # 组合筛选
python -m pytest tests -m rules -v --alluredir=allure-results
```

## 3. 报告里会看到什么（层次 = 用例-需求追踪矩阵）

| Allure 层级 | 内容 | 示例 |
|---|---|---|
| **epic** | 测试域 | 战斗规则 / 数值质量 / 性能 / AI 辅助 |
| **feature** | 规则域 | 伤害结算 DMG / 平衡回归 BAL / 交叉验证 AI |
| **story** | 类 docstring 首行 | “REQ-DMG-001：先减免后暴击…” |
| 单条用例 | 断言+步骤 | 每条测试名即"REQ/用例矩阵"编号的检索入口 |

即：面试官可以从 **epic → feature → 单条用例** 逐层钻到任意一条需求及其断言，
与 `docs/test-case-matrix.md` 一一对应。

## 4. CI 定时生成（GitHub Actions）

`.github/workflows/daily-balance.yml` 已预留；本地/自建 runner 加两步即可：

```bash
python -m pytest tests --alluredir=allure-results
allure generate allure-results -o allure-report --clean
```

并把 `allure-report/` 作为 artifact 上传，或发布到 GitHub Pages（方案文档 W6 原始设想）。

> 说明：仓库本体（引擎/测试/报告脚本）零第三方运行时依赖，pytest/allure 只影响
> "执行方式与展示"；因此本仓库在无 pytest 环境下用 unittest 也能全量回归（79/79）。
