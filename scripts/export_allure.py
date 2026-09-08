"""Allure 报告数据导出器（纯标准库，脱离 pytest/allure-pytest 也能产出 allure-results/）。

背景：Allure 报告的 HTML 由 `allure generate` 生成，但它消费的是 allure-results/
目录里的标准 JSON 文件。本脚本直接运行 unittest 套件并把每条用例写成 Allure v2
格式 JSON（结果文件 + 按测试类的容器文件 + environment.properties），因此：
  - 无 pytest / 无 allure-pytest 的环境也能产出标准输入（本仓库一直如此）；
  - 层级（epic/feature/marker）与 tests/allure_map.py 单一来源，与 pytest 路径一致。

用法：
  python scripts/export_allure.py [--out allure-results] [--dry-run]
  allure generate allure-results -o allure-report --clean && allure open
"""

import argparse
import io
import json
import os
import sys
import time
import unittest
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from tests.allure_map import CLASS_MAP  # noqa: E402  (路径已注入)


class _Recorder(unittest.TextTestResult):
    """记录每个测试的开始/结束时间与状态。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started: Dict[str, float] = {}
        self.timing: Dict[str, Tuple[float, float]] = {}

    def startTest(self, test):
        self.started[test.id()] = time.time()
        super().startTest(test)

    def stopTest(self, test):
        started = self.started.get(test.id(), time.time())
        self.timing[test.id()] = (started, time.time())
        super().stopTest(test)


def _flatten(suite) -> List[unittest.TestCase]:
    out: List[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out


def _labels_for(test: unittest.TestCase) -> Tuple[str, str, List[dict]]:
    """返回 (类名, docstring首行, labels列表)。"""
    module = type(test).__module__
    cls = type(test).__name__
    meta = CLASS_MAP.get(cls)
    doc = (type(test).__doc__ or "").strip().splitlines()
    labels = [
        {"name": "suite", "value": cls},
        {"name": "testClass", "value": f"{module}.{cls}"},
        {"name": "package", "value": module},
        {"name": "framework", "value": "unittest"},
        {"name": "language", "value": "python"},
        {"name": "host", "value": os.environ.get("COMPUTERNAME", "localhost")},
    ]
    if meta:
        epic, feature, marker = meta
        labels.append({"name": "epic", "value": epic})
        labels.append({"name": "feature", "value": feature})
        labels.append({"name": "tag", "value": marker})
    return cls, (doc[0] if doc else ""), labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(REPO_ROOT / "allure-results"))
    parser.add_argument("--dry-run", action="store_true",
                        help="只统计计划写出的文件，不写盘（沙箱/预览用）")
    args = parser.parse_args()

    loader = unittest.TestLoader()
    suite = loader.discover(str(REPO_ROOT / "tests"), pattern="test_*.py")
    tests = _flatten(suite)

    runner = unittest.TextTestRunner(
        stream=io.StringIO(), resultclass=_Recorder, verbosity=0)
    result = runner.run(suite)
    statuses: Dict[str, str] = {}
    for t, _ in result.failures:
        statuses[t.id()] = "failed"
    for t, _ in result.errors:
        statuses[t.id()] = "broken"
    for t, _ in result.skipped:
        statuses[t.id()] = "skipped"
    for test in tests:
        statuses.setdefault(test.id(), "passed")

    containers: Dict[str, List[str]] = {}   # 类名 -> [test uuids]
    out_dir = Path(args.out)
    plan = {"results": [], "containers": [], "environment": 1}
    base_ms = int(time.time() * 1000)

    for i, test in enumerate(tests):
        tid = test.id()
        u = str(uuid.uuid5(uuid.NAMESPACE_URL, f"mini-tower:{tid}"))
        cls, story, labels = _labels_for(test)
        start, stop = result.timing.get(tid, (time.time() - 0.001, time.time()))
        payload = {
            "uuid": u,
            "historyId": uuid.uuid5(uuid.NAMESPACE_URL, f"h:{tid}").hex,
            "fullName": tid,
            "name": tid.split(".")[-1],
            "status": statuses.get(tid, "passed"),
            "statusDetails": {},
            "stage": "finished",
            "start": int(start * 1000),
            "stop": int(stop * 1000),
            "labels": labels + ([{"name": "story", "value": story}] if story else []),
            "links": [],
        }
        fname = f"{u}-result.json"
        plan["results"].append((out_dir / fname, payload))
        containers.setdefault(cls, []).append(u)

    for cls, children in containers.items():
        cu = str(uuid.uuid5(uuid.NAMESPACE_URL, f"container:{cls}"))
        plan["containers"].append((out_dir / f"{cu}-container.json", {
            "uuid": cu, "name": cls, "children": children,
            "befores": [], "afters": [],
        }))

    env = ("allure.environment=generated-by-export_allure\n"
           f"machine={os.environ.get('COMPUTERNAME', 'unknown')}\n"
           f"python={sys.version.split()[0]}\n")
    plan["environment"] = (out_dir / "environment.properties", env)

    if args.dry_run:
        print(f"[dry-run] 测试 {len(tests)} 条 | "
              f"result 文件 {len(plan['results'])} | "
              f"container 文件 {len(plan['containers'])} | environment 1")
        for r, _ in plan["results"][:3]:
            print("  ", r.name)
        print("  ...")
        print("通过/失败/错误/跳过 = "
              f"{len(statuses)-sum(s!='passed' for s in statuses.values())}/"
              f"{sum(s=='failed' for s in statuses.values())}/"
              f"{sum(s=='broken' for s in statuses.values())}/"
              f"{sum(s=='skipped' for s in statuses.values())}")
        return

    if not args.dry_run and out_dir.exists():
        import shutil
        shutil.rmtree(out_dir)          # 防多次导出累积陈旧结果（曾致 summary 重复计数）
    out_dir.mkdir(parents=True, exist_ok=True)
    for path, payload in plan["results"]:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    for path, payload in plan["containers"]:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    path, text = plan["environment"]
    path.write_text(text, encoding="utf-8")
    print(f"已导出 {len(plan['results'])} 条用例 + "
          f"{len(plan['containers'])} 个容器 + environment.properties → {out_dir}")
    print("下一步：allure generate <out> -o allure-report --clean")


if __name__ == "__main__":
    main()
