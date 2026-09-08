"""pytest 钩子：把 unittest 用例自动映射到 Allure 层级（epic/feature/story）与 pytest marker。

- 未安装 allure-pytest 时静默跳过（不影响 unittest / pytest 正常运行）；
- 安装 allure-pytest 后执行 `pytest --alluredir=allure-results` 即得按
  "测试域 → 规则 → 单条用例" 组织的 Allure 报告；
- 类→层级映射与 scripts/export_allure.py 共用 tests/allure_map.py（单一来源）。
"""

import pytest

from allure_map import CLASS_MAP  # noqa: E402（tests 目录在 pytest 的 rootdir 路径上）

try:
    import allure  # noqa: F401
except Exception:  # pragma: no cover - 未安装时降级
    allure = None


def pytest_collection_modifyitems(config, items):  # noqa: ANN001
    if allure is None:
        return
    for item in items:
        cls = getattr(item, "cls", None)
        if cls is None:
            continue
        meta = CLASS_MAP.get(cls.__name__)
        if not meta:
            continue
        epic, feature, marker = meta
        allure.dynamic.epic(epic)
        allure.dynamic.feature(feature)
        doc = (cls.__doc__ or "").strip().splitlines()
        if doc:
            allure.dynamic.story(doc[0][:60])
        item.add_marker(getattr(pytest.mark, marker))
