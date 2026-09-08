"""SQLite 落库与查询层（W3，REQ-DATA-001..004）。

“测试产出数据 → SQL 反哺调优建议”闭环的底座：
- 每局模拟落 sim_runs（含每名干员伤害占比 JSON，来自事件日志二次聚合）；
- 招募模拟落 recruit_runs（分保底开关汇总）；
- 查询语句统一放 sql/analysis.sql，支持在任何 SQLite 客户端回放。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Sequence

from .recruit import RecruitSummary
from .simulator import BatchSummary

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sim_runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts          TEXT    NOT NULL,
  stage_id    TEXT    NOT NULL,
  team_id     TEXT    NOT NULL,
  seed        INTEGER NOT NULL,
  clear       INTEGER NOT NULL,
  three_star  INTEGER NOT NULL,
  lives_left  INTEGER NOT NULL,
  end_time    REAL    NOT NULL,
  kills       INTEGER NOT NULL,
  leaked      INTEGER NOT NULL,
  dmg_total   INTEGER NOT NULL,
  dmg_by_op   TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS recruit_runs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT    NOT NULL,
  run_seed     INTEGER NOT NULL,
  pulls        INTEGER NOT NULL,
  n6           INTEGER NOT NULL,
  n5           INTEGER NOT NULL,
  n4           INTEGER NOT NULL,
  pity_enabled INTEGER NOT NULL,
  rate6        REAL    NOT NULL
);
"""


def open_db(path: str = ":memory:") -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


def insert_sim_batch(conn: sqlite3.Connection, stage_id: str, team_id: str,
                     batch: BatchSummary, ts: str = "") -> int:
    """把一个批量模拟（BatchSummary）整体落库。"""
    ts = ts or _now()
    rows = [
        (ts, stage_id, team_id, r.seed, int(r.clear), int(r.three_star),
         r.lives_left, r.end_time, r.kills, r.leaked, r.total_damage,
         json.dumps(r.dmg_by_op, ensure_ascii=False))
        for r in batch.records
    ]
    conn.executemany(
        "INSERT INTO sim_runs (ts, stage_id, team_id, seed, clear, three_star,"
        " lives_left, end_time, kills, leaked, dmg_total, dmg_by_op)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return len(rows)


def insert_recruit_runs(conn: sqlite3.Connection, runs: Sequence[RecruitSummary],
                        pity_enabled: bool, ts: str = "") -> int:
    ts = ts or _now()
    rows = [
        (ts, r.seed, r.pulls, r.n6, r.n5, r.n4, int(pity_enabled), r.rate_6)
        for r in runs
    ]
    conn.executemany(
        "INSERT INTO recruit_runs (ts, run_seed, pulls, n6, n5, n4,"
        " pity_enabled, rate6) VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return len(rows)


def fetch(conn: sqlite3.Connection, sql: str) -> List[dict]:
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def load_queries(path=None) -> Dict[str, str]:
    """解析 sql/analysis.sql：以 `-- ### 名称` 注释切分查询块。"""
    p = Path(path) if path else SQL_DIR / "analysis.sql"
    queries: Dict[str, str] = {}
    name = None
    buf: List[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("-- ###"):
            if name and buf:
                queries[name] = "\n".join(buf)
            name = stripped[len("-- ###"):].strip()
            buf = []
        else:
            buf.append(line)
    if name and buf:
        queries[name] = "\n".join(buf)
    if not queries:
        raise ValueError(f"{p.name} 中没有解析到任何查询")
    return queries
