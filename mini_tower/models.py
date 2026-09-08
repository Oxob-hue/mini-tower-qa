"""MiniTower 数据模型（被测对象 SUT 的“数据定义”层）。

工程原则：逻辑与数据分离 —— 干员/敌人/关卡全部外置为 JSON 配置，
使「改一行配置 = 一次数值改动」成为可回归的测试事件（REQ-CFG-004）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

#: 伤害类型枚举：physical=物理（受防御减免），true=真实（无视防御）
DAMAGE_TYPES = ("physical", "true")


@dataclass(frozen=True)
class OperatorDef:
    """干员定义（高台输出型简化模型）。

    range_lo / range_hi：攻击覆盖的路径区间（米，从敌方出生点起算）。
    技能（REQ-SKL）：每累计成功命中 skill_every 次，下一次命中结算为技能
    （伤害 = atk * skill_mult 且无视防御）；skill_every=0 表示无技能。
    """

    oid: str
    name: str
    rarity: int = 5
    atk: int = 100
    interval: float = 1.0
    range_lo: float = 0.0
    range_hi: float = 10.0
    dmg_type: str = "physical"
    crit_rate: float = 0.0
    crit_mult: float = 1.5
    skill_every: int = 0
    skill_mult: float = 1.0


@dataclass(frozen=True)
class EnemyDef:
    """敌人定义：沿路径从出生点走向我方终点（W1 不含攻击型敌人）。"""

    eid: str
    name: str
    hp: int = 100
    defense: int = 0
    speed: float = 1.0      # 米/秒
    leak: int = 1           # 到达终点时对我方生命造成的损失


@dataclass(frozen=True)
class WaveDef:
    """一波敌人：start_time 起，每隔 interval 生成 count 个。"""

    enemy_id: str
    count: int
    start_time: float
    interval: float = 1.0


@dataclass(frozen=True)
class StageDef:
    sid: str
    name: str
    path_length: float       # 米
    base_hp: int             # 我方生命
    three_star_lives: int    # 三星所需剩余生命
    waves: Tuple[WaveDef, ...] = ()


@dataclass
class Catalog:
    """一次加载完成的全部配置（ops/enemies/stages 均以 id 为键）。"""

    operators: Dict[str, OperatorDef]
    enemies: Dict[str, EnemyDef]
    stages: Dict[str, StageDef]

    def team_operators(self, team_ids):
        return [self.operators[i] for i in team_ids]
