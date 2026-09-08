"""统计工具（纯标准库实现，无 scipy 依赖）。

面试口径：概率断言要讲清"样本量 / 置信水平 / 检验假设"，
而不是"模拟 1000 次约等于 2%"。CI 用正态近似，χ² 用临界值比较
（df=2, α=0.05 → 5.991）。后续如引入 scipy 可换精确 p 值，结论一致。
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple


def binomial_ci(count: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """二项比例的正态近似置信区间：p̂ ± z·√(p̂(1-p̂)/n)。要求 n·p̂ 与 n·(1-p̂) 均较大。"""
    if n <= 0:
        raise ValueError("n 必须 > 0")
    p = count / n
    se = math.sqrt(p * (1 - p) / n)
    return (p - z * se, p + z * se)


def chi2_gof_statistic(observed: Sequence[int], expected: Sequence[float]) -> float:
    """χ² 拟合优度统计量 Σ(o-e)²/e。调用方按自由度查临界值比较（无外部库时）。"""
    if len(observed) != len(expected):
        raise ValueError("observed 与 expected 长度必须一致")
    stat = 0.0
    for o, e in zip(observed, expected):
        if e <= 0:
            raise ValueError("期望频数必须 > 0")
        stat += (o - e) ** 2 / e
    return stat


#: df=2、α=0.05 的 χ² 临界值（供三档稀有度拟合优度检验使用）
CHI2_CRITICAL_DF2_95 = 5.991
