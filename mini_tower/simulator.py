"""批量模拟入口（W3 数值平衡断言的底座）。

REQ-SIM-001..004：确定性 / headless / 批量 seed 规则 / 全量事件日志。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .combat import BattleResult, run_battle
from .models import Catalog, OperatorDef


@dataclass(frozen=True)
class RunRecord:
    """单局结果（W3 起落 SQLite，供 SQL 关联分析）。"""

    seed: int
    clear: bool
    three_star: bool
    lives_left: int
    end_time: float
    kills: int
    leaked: int
    total_damage: int
    dmg_by_op: Dict[str, int] = field(default_factory=dict, compare=False)


def extract_dmg_by_operator(events) -> Dict[str, int]:
    """从事件日志聚合每名干员造成的伤害（REQ-SIM-004 日志的二次使用）。"""
    out: Dict[str, int] = {}
    for ev in events:
        if ev.kind not in ("attack", "skill"):
            continue
        marker = "by="
        idx = ev.detail.find(marker)
        if idx < 0:
            continue
        oid = ev.detail[idx + len(marker):]
        dmg = int(ev.detail.split("dmg=")[1].split()[0])
        out[oid] = out.get(oid, 0) + dmg
    return out


@dataclass(frozen=True)
class BatchSummary:
    stage_id: str
    team_ids: Tuple[str, ...]
    rounds: int
    clear_count: int
    three_star_count: int
    clear_rate: float
    three_star_rate: float
    avg_lives_left: float
    avg_duration: float
    p99_duration: float
    records: List[RunRecord] = field(default_factory=list, compare=False)


def resolve_team(catalog: Catalog, team_ids: Sequence[str]) -> Tuple[OperatorDef, ...]:
    """校验编队：干员必须存在且不重复（重复会破坏战斗引擎的 oid 映射）。"""
    seen = set()
    team: List[OperatorDef] = []
    for tid in team_ids:
        if tid in seen:
            raise ValueError(f"编队内干员重复: {tid}")
        seen.add(tid)
        op = catalog.operators.get(tid)
        if op is None:
            raise ValueError(f"编队引用了不存在的干员: {tid}")
        team.append(op)
    if not team:
        raise ValueError("编队不能为空")
    return tuple(team)


def _stage(catalog: Catalog, stage_id: str):
    stage = catalog.stages.get(stage_id)
    if stage is None:
        raise ValueError(f"不存在的关卡: {stage_id}")
    return stage


def run_once(
    catalog: Catalog,
    stage_id: str,
    team_ids: Sequence[str],
    seed: Optional[int] = None,
    max_time: float = 600.0,
) -> BattleResult:
    """跑一局（保留全量事件日志，供 W2 规则断言 / 覆盖率统计）。"""
    stage = _stage(catalog, stage_id)
    team = resolve_team(catalog, team_ids)
    return run_battle(catalog.enemies, stage, team, seed=seed, max_time=max_time)


def run_batch(
    catalog: Catalog,
    stage_id: str,
    team_ids: Sequence[str],
    rounds: int,
    master_seed: int = 0,
    max_time: float = 600.0,
) -> BatchSummary:
    """批量 N 局，每局 seed = master_seed + i（REQ-SIM-003）。"""
    if rounds < 1:
        raise ValueError(f"rounds 必须 >= 1，实际 {rounds}")
    stage = _stage(catalog, stage_id)
    team = resolve_team(catalog, team_ids)
    records: List[RunRecord] = []
    for i in range(rounds):
        seed = master_seed + i
        r = run_battle(catalog.enemies, stage, team, seed=seed, max_time=max_time)
        records.append(
            RunRecord(
                seed=seed, clear=r.clear, three_star=r.three_star,
                lives_left=r.lives_left, end_time=r.end_time,
                kills=r.kills, leaked=r.leaked, total_damage=r.total_damage,
                dmg_by_op=extract_dmg_by_operator(r.events),
            )
        )
    durations = sorted(rec.end_time for rec in records)
    p99 = durations[int(0.99 * (len(durations) - 1))] if durations else 0.0
    return BatchSummary(
        stage_id=stage_id,
        team_ids=tuple(team_ids),
        rounds=rounds,
        clear_count=sum(rec.clear for rec in records),
        three_star_count=sum(rec.three_star for rec in records),
        clear_rate=sum(rec.clear for rec in records) / rounds,
        three_star_rate=sum(rec.three_star for rec in records) / rounds,
        avg_lives_left=sum(rec.lives_left for rec in records) / rounds,
        avg_duration=sum(rec.end_time for rec in records) / rounds,
        p99_duration=p99,
        records=records,
    )
