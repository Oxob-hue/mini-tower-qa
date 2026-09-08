"""招募（抽卡）概率系统 —— 被测对象 SUT 的概率域模块（W3）。

设计哲学与战斗引擎一致：唯一的随机源是 random.Random(seed)，
固定 seed → 整条出货序列逐次可复现（REQ-PRB-001）。

规则（对应 docs/requirements.md REQ-PRB-00x）：
- 稀有度档位：6★ / 5★ / 4★，基础概率来自配置（p4 = 1 - p6 - p5）；
- 软保底：距上次 6★ 满 soft_pity_start 抽后，6★ 概率每抽 +soft_pity_step；
- 硬保底：距上次 6★ 达 pity_cap 抽仍未出 → 第 pity_cap 抽强制 6★（REQ-PRB-003）；
- 出 6★ 后计数归零重新累计（REQ-PRB-005）。
- pity_cap = 0 表示关闭保底（用于对"声明基础概率"做纯假设检验，REQ-PRB-002）。
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

DATA_DIR = Path(__file__).resolve().parent / "data"


class RecruitConfigError(Exception):
    """招募配置校验失败。"""


@dataclass(frozen=True)
class RecruitSummary:
    seed: int
    pulls: int
    n6: int
    n5: int
    n4: int
    max_gap_6: int        # 单次序列内最大 6★ 间隔
    rate_6: float
    #: 每次 6★ 出现时的抽数位置（1 起）与 6★ 前后间隔，供深度分析
    pity_gaps: Tuple[int, ...] = field(default_factory=tuple, compare=False)


class RecruitPool:
    """一个招募池。构造即校验配置域。"""

    def __init__(
        self,
        p6: float,
        p5: float,
        pity_cap: int = 100,       # 0 = 关闭保底
        soft_pity_start: int = 50,  # 第 50 抽起进入软保底
        soft_pity_step: float = 0.02,
        name: str = "演示招募池",
    ):
        p4 = 1.0 - p6 - p5
        if not (0 < p6 < 1) or not (0 < p5 < 1) or not (0 < p4 < 1):
            raise RecruitConfigError(f"概率必须在 (0,1) 且 p4=1-p6-p5>0：p6={p6} p5={p5} p4={p4}")
        if pity_cap < 0 or not isinstance(pity_cap, int):
            raise RecruitConfigError(f"pity_cap 必须是非负整数，实际 {pity_cap!r}")
        if soft_pity_start < 0 or soft_pity_step < 0:
            raise RecruitConfigError("soft_pity_start / soft_pity_step 不得为负")
        if pity_cap and soft_pity_start > pity_cap:
            raise RecruitConfigError(f"soft_pity_start({soft_pity_start}) 不能大于 pity_cap({pity_cap})")
        self.name = name
        self.p6, self.p5, self.p4 = p6, p5, p4
        self.pity_cap = pity_cap
        self.soft_pity_start = soft_pity_start
        self.soft_pity_step = soft_pity_step

    def _rate6(self, pity: int) -> float:
        """当前抽数的 6★ 概率（含软保底递增；硬保底：连续 cap-1 抽未出 → 本抽必出）。"""
        if self.pity_cap and pity >= self.pity_cap - 1:
            return 1.0                                   # REQ-PRB-003 硬保底（第 cap 抽必出）
        if self.pity_cap and self.soft_pity_start > 0 and pity >= self.soft_pity_start:
            return min(self.p6 + (pity - self.soft_pity_start + 1) * self.soft_pity_step, 1.0)
        return self.p6

    def draw(self, seed: int, pulls: int) -> List[int]:
        """依序抽取 pulls 次，返回稀有度序列（元素 ∈ {6,5,4}）。REQ-PRB-001 可复现。"""
        rng = random.Random(seed)
        out: List[int] = []
        pity = 0
        for _ in range(pulls):
            rate6 = self._rate6(pity)
            roll = rng.random()
            if roll < rate6:
                out.append(6)
                pity = 0                               # REQ-PRB-005 归零
            elif roll < rate6 + self.p5:
                out.append(5)
                pity += 1
            else:
                out.append(4)
                pity += 1
        return out

    def simulate(self, seed: int, pulls: int) -> RecruitSummary:
        seq = self.draw(seed, pulls)
        n6 = seq.count(6)
        gaps: List[int] = []
        last = 0
        for i, r in enumerate(seq, start=1):
            if r == 6:
                gaps.append(i - last)
                last = i
        if gaps:
            gaps.append(pulls + 1 - last)      # 序列尾部未出 6★ 的截断间隔
        return RecruitSummary(
            seed=seed, pulls=pulls, n6=n6, n5=seq.count(5), n4=seq.count(4),
            max_gap_6=max(gaps) if gaps else pulls,
            rate_6=n6 / pulls,
            pity_gaps=tuple(gaps),
        )


def load_recruit_pool(path=None) -> RecruitPool:
    """从 data/recruit.json 加载招募池。"""
    p = Path(path) if path else DATA_DIR / "recruit.json"
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise RecruitConfigError(f"{p.name} 加载失败: {exc}") from exc
    pool = raw.get("pool", {})
    tiers = {t["rarity"]: t["rate"] for t in pool.get("tiers", [])}
    if set(tiers) != {6, 5, 4}:
        raise RecruitConfigError("tiers 必须包含且仅包含 6/5/4 三档")
    return RecruitPool(
        p6=float(tiers[6]),
        p5=float(tiers[5]),
        pity_cap=int(pool.get("pity_cap", 100)),
        soft_pity_start=int(pool.get("soft_pity_start", 50)),
        soft_pity_step=float(pool.get("soft_pity_step", 0.02)),
        name=str(pool.get("name", "招募池")),
    )
