"""战斗引擎：单路径时间轴模拟（被测对象 SUT 的核心）。

规则实现与 docs/requirements.md 中 REQ-DMG / REQ-SKL / REQ-TGT / REQ-STG 逐条对应。
确定性：唯一的随机源是“暴击判定”，受 seed 控制（REQ-SIM-001）。

缺陷修复记录（v0.1.1）：
  清场判胜（REQ-STG-004）原先只挂在“击杀”路径上；若场上最后一只是
  “漏怪到达终点”离场（或离场后干员仍在空挥），战斗会空转到 max_time 超时、
  把本应通关的局误判为失败。现改为在每个事件处理后统一做“场上无敌人且无待生成
  敌人 → 胜利”的判定，覆盖 击杀 / 漏怪 / 空挥 三条路径。
"""

from __future__ import annotations

import heapq
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

from .models import EnemyDef, OperatorDef, StageDef

#: REQ-DMG-001：物理伤害下限 = 攻击力的 5%（向上取整），避免“高防完全免伤”
PHYS_MIN_PCT = 0.05


def physical_damage(atk: int, defense: int) -> int:
    """REQ-DMG-001 / REQ-DMG-004：物理伤害 = max(atk - def, ⌈atk × 5%⌉)。"""
    return max(atk - defense, math.ceil(atk * PHYS_MIN_PCT))


@dataclass(frozen=True)
class BattleEvent:
    """单条战斗日志。kind ∈ {spawn, attack, skill, kill, leak, end}。"""

    t: float
    kind: str
    subject: str
    detail: str = ""


@dataclass(frozen=True)
class BattleResult:
    stage_id: str
    clear: bool
    reason: str            # victory | defeat_leak | timeout
    lives_left: int
    three_star: bool
    end_time: float
    kills: int
    leaked: int
    total_damage: int
    events: List[BattleEvent] = field(default_factory=list, compare=False)


@dataclass
class _OpState:
    op: OperatorDef
    landed: int = 0   # 累计成功命中次数（技能计数用，REQ-SKL-001）


@dataclass
class _EnemyState:
    idx: int
    tag: str           # 例如 walker#3
    enemy: EnemyDef
    spawn_t: float
    hp: int


def _make_result(stage: StageDef, t: float, clear: bool, reason: str,
                 lives: int, kills: int, leaked: int, dmg_total: int,
                 events: List[BattleEvent]) -> "BattleResult":
    return BattleResult(
        stage_id=stage.sid,
        clear=clear,
        reason=reason,
        lives_left=lives,
        three_star=bool(clear and lives >= stage.three_star_lives),  # REQ-STG-005
        end_time=t,
        kills=kills,
        leaked=leaked,
        total_damage=dmg_total,
        events=events,
    )


def run_battle(
    enemies_map: Mapping[str, EnemyDef],
    stage: StageDef,
    team: Sequence[OperatorDef],
    seed: Optional[int] = None,
    max_time: float = 600.0,
) -> BattleResult:
    """跑一局。seed 固定 → 逐事件完全一致（REQ-SIM-001）。"""
    rng = random.Random(seed)
    seq = 0
    heap: List[tuple] = []
    events: List[BattleEvent] = []

    def push(t: float, kind: str, subject: str, detail: str = "") -> None:
        nonlocal seq
        seq += 1
        heapq.heappush(heap, (float(t), seq, kind, subject, detail))

    # 预排：全部波次的生成事件（REQ-STG-001）
    total_to_spawn = sum(w.count for w in stage.waves)
    for wave in stage.waves:
        for i in range(wave.count):
            push(wave.start_time + i * wave.interval, "spawn", wave.enemy_id)

    # 干员全部“开局在场”，首次攻击前摇 = 攻击间隔（REQ-DMG-005）
    ops: List[_OpState] = []
    op_by_oid: Dict[str, _OpState] = {}
    for op in team:
        st = _OpState(op=op)
        ops.append(st)
        op_by_oid[op.oid] = st
        push(op.interval, "attack", op.oid)

    enemies: Dict[int, _EnemyState] = {}
    next_idx = 0
    lives = stage.base_hp
    kills = leaked = dmg_total = 0
    last_t = 0.0
    result: Optional[BattleResult] = None

    while heap and result is None:
        t, _, kind, subject, detail = heapq.heappop(heap)
        last_t = t

        if t > max_time:
            # REQ-STG-006：超时守卫（防止无解编队让模拟无限跑）
            result = _make_result(stage, max_time, False, "timeout",
                                  lives, kills, leaked, dmg_total, events)
            break

        if kind == "spawn":
            # REQ-STG-001：生成敌人并预排“到达终点”事件
            total_to_spawn -= 1
            edef = enemies_map[subject]
            enemy = _EnemyState(idx=next_idx, tag=f"{subject}#{next_idx}",
                                enemy=edef, spawn_t=t, hp=edef.hp)
            next_idx += 1
            enemies[enemy.idx] = enemy
            push(t + stage.path_length / edef.speed, "arrive", enemy.tag)
            events.append(BattleEvent(t, "spawn", enemy.tag))

        elif kind == "arrive":
            hit = next((e for e in enemies.values() if e.tag == subject), None)
            if hit is not None:
                # REQ-STG-002：到达终点 → 损失 leak 点生命并离场
                del enemies[hit.idx]
                leaked += 1
                lives -= hit.enemy.leak
                events.append(BattleEvent(t, "leak", hit.tag, f"lives={lives}"))
                if lives <= 0:
                    # REQ-STG-003：生命归零立即判负
                    result = _make_result(stage, t, False, "defeat_leak",
                                          lives, kills, leaked, dmg_total, events)
                    break

        else:  # attack
            opst = op_by_oid[subject]
            op = opst.op
            # REQ-TGT-001：范围内选择“最接近我方终点”的敌人（位置最大）
            target_idx: Optional[int] = None
            target_pos = -1.0
            for eidx, e in enemies.items():
                pos = (t - e.spawn_t) * e.enemy.speed
                if op.range_lo <= pos <= op.range_hi and pos > target_pos:
                    target_idx, target_pos = eidx, pos
            if target_idx is None:
                # 射程内无目标 → 攻击落空，节拍照常（REQ-DMG-005）
                push(t + op.interval, "attack", op.oid)
                continue  # 空挥不产生伤害；底部统一做清场判定

            enemy = enemies[target_idx]
            opst.landed += 1
            is_skill = bool(op.skill_every) and opst.landed % op.skill_every == 0
            if is_skill:
                # REQ-SKL-001：技能伤害 = atk × skill_mult，无视防御
                eff = float(op.atk * op.skill_mult)
                kind_label = "skill"
            elif op.dmg_type == "true":
                # REQ-DMG-002：真实伤害全额结算
                eff = float(op.atk)
                kind_label = "attack"
            else:
                # REQ-DMG-001：物理伤害 = max(atk-def, ⌈5%×atk⌉)
                eff = float(physical_damage(op.atk, enemy.enemy.defense))
                kind_label = "attack"
            is_crit = rng.random() < op.crit_rate
            if is_crit:
                eff *= op.crit_mult    # REQ-DMG-003：暴击作用于减免后伤害
            dmg = int(eff)
            if dmg < 1:
                dmg = 1                # REQ-DMG-004 下限
            enemy.hp -= dmg
            dmg_total += dmg
            flags = (" crit" if is_crit else "") + (" skill" if is_skill else "")
            events.append(BattleEvent(t, kind_label, enemy.tag,
                                      f"dmg={dmg}{flags} by={op.oid}"))
            if enemy.hp <= 0:
                del enemies[target_idx]
                kills += 1
                events.append(BattleEvent(t, "kill", enemy.tag, f"by={op.oid}"))
            push(t + op.interval, "attack", op.oid)

        # 统一清场判定（REQ-STG-004）：场上无敌人 且 无待生成敌人 → 胜利
        # 覆盖“最后一只是漏怪离场 / 击杀后空挥”等所有路径
        if result is None and not enemies and total_to_spawn == 0:
            result = _make_result(stage, t, True, "victory",
                                  lives, kills, leaked, dmg_total, events)
            break

    if result is None:
        # 兜底：事件队列耗尽仍未分胜负（正常流程不应到达）
        result = _make_result(stage, last_t, not enemies,
                              "victory" if not enemies else "timeout",
                              lives, kills, leaked, dmg_total, events)
    return result
