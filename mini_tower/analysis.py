"""数值平衡分析（静态理论模型，W3 数值膨胀/克制校验）。

口径说明：
- 理论 DPS = 平均每次成功命中伤害 ÷ 攻击间隔，假定目标持续在射程内（上限值）；
  用于**相对比较**（膨胀比、克制比），绝对值以模拟实测为准（REQ-BAL）；
- 与战斗引擎同源规则：物理伤害含 5% 下限、技能每 N 次命中触发且无视防御、
  暴击作用于减免后伤害——保证"理论口径 = 引擎口径"，分析结论可信。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

from .combat import PHYS_MIN_PCT
from .models import Catalog, OperatorDef


def expected_damage_per_landed(op: OperatorDef, defense: int = 0) -> float:
    """平均每次成功命中的期望伤害（含技能周期与暴击期望）。"""
    if op.dmg_type == "true":
        base = float(op.atk)                              # REQ-DMG-002 真实伤害
    else:
        base = float(max(op.atk - defense, math.ceil(op.atk * PHYS_MIN_PCT)))
    if op.skill_every > 0:
        # REQ-SKL-001：N 次命中一个周期：N-1 次普攻 + 1 次技能（无视防御）
        skill = float(op.atk * op.skill_mult)
        per_cycle = base * (op.skill_every - 1) + skill
        per_landed = per_cycle / op.skill_every
    else:
        per_landed = base
    crit_factor = 1.0 + op.crit_rate * (op.crit_mult - 1.0)   # REQ-DMG-003
    return per_landed * crit_factor


def theoretical_dps(op: OperatorDef, defense: int = 0) -> float:
    """连续输出上限（每秒期望伤害）。"""
    return expected_damage_per_landed(op, defense) / op.interval


@dataclass(frozen=True)
class RosterAnalysis:
    """编队外全部干员的理论强度画像（按给定防御目标）。"""

    defense: int
    dps: Dict[str, float]                 # oid -> dps
    max_oid: str
    min_oid: str
    spread_ratio: float                   # max/min
    rarity_mean_dps: Dict[int, float]     # 各稀有度平均 dps


def analyze_roster(catalog: Catalog, defense: int = 0) -> RosterAnalysis:
    dps = {oid: theoretical_dps(op, defense) for oid, op in catalog.operators.items()}
    max_oid = max(dps, key=dps.get)
    min_oid = min(dps, key=dps.get)
    by_rarity: Dict[int, List[float]] = {}
    for oid, op in catalog.operators.items():
        by_rarity.setdefault(op.rarity, []).append(dps[oid])
    return RosterAnalysis(
        defense=defense,
        dps=dps,
        max_oid=max_oid,
        min_oid=min_oid,
        spread_ratio=dps[max_oid] / dps[min_oid],
        rarity_mean_dps={r: sum(v) / len(v) for r, v in by_rarity.items()},
    )


def true_damage_advantage(catalog: Catalog, defense: int) -> float:
    """克制校验（REQ-BAL-003）：高防下真实伤害/技能 dps 对物理低攻 dps 的优势倍数。"""
    true_ops = [op for op in catalog.operators.values() if op.dmg_type == "true"]
    if not true_ops:
        return 1.0
    best_true = max(theoretical_dps(op, defense) for op in true_ops)
    worst_phys_low = min(
        theoretical_dps(op, defense)
        for op in catalog.operators.values()
        if op.dmg_type == "physical"
    )
    return best_true / worst_phys_low if worst_phys_low > 0 else float("inf")
