"""JSON 配置加载与校验（配置层 / 测试左移入口）。

REQ-CFG-004：坏配置在“加载期”直接拒绝，问题数据不允许进入战斗引擎 ——
这就是测试左移的体现：配置本身也是被测对象的一部分（W2 将针对它写配置测试）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .models import DAMAGE_TYPES, Catalog, EnemyDef, OperatorDef, StageDef, WaveDef

DATA_DIR = Path(__file__).resolve().parent / "data"


class ConfigError(Exception):
    """配置加载/校验失败；message 汇总全部问题，便于一次性修复。"""


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{path.name} JSON 解析失败: {exc}") from exc


def _num(value, name, errs, *, integer=False, minimum=None, maximum=None):
    """数值域校验（REQ-CFG-002）。integer=True 时强制 int 类型（防 1.0 混入）。"""
    if integer and not isinstance(value, int):
        errs.append(f"{name} 必须是整数，实际 {value!r}")
        return
    if not integer and not isinstance(value, (int, float)):
        errs.append(f"{name} 必须是数值，实际 {value!r}")
        return
    if minimum is not None and value < minimum:
        errs.append(f"{name} 不得小于 {minimum}，实际 {value}")
    if maximum is not None and value > maximum:
        errs.append(f"{name} 不得大于 {maximum}，实际 {value}")


def _build_operators(raw, problems: List[str]) -> Dict[str, OperatorDef]:
    if not isinstance(raw, list):
        problems.append("operators 必须是数组")
        return {}
    out: Dict[str, OperatorDef] = {}
    for i, item in enumerate(raw):
        errs: List[str] = []
        where = f"operators[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} 必须是对象")
            continue
        oid = item.get("oid")
        if not isinstance(oid, str) or not oid:
            errs.append(f"{where}.oid 缺失或非字符串")
        elif oid in out:
            errs.append(f"{where}.oid 重复: {oid}")
        _num(item.get("rarity"), f"{where}.rarity", errs, integer=True, minimum=3, maximum=6)
        _num(item.get("atk"), f"{where}.atk", errs, integer=True, minimum=1, maximum=1_000_000)
        _num(item.get("interval"), f"{where}.interval", errs, minimum=0.01, maximum=600.0)
        _num(item.get("range_lo"), f"{where}.range_lo", errs, minimum=0.0)
        _num(item.get("range_hi"), f"{where}.range_hi", errs, minimum=0.0)
        _num(item.get("crit_rate"), f"{where}.crit_rate", errs, minimum=0.0, maximum=1.0)
        _num(item.get("crit_mult"), f"{where}.crit_mult", errs, minimum=1.0)
        _num(item.get("skill_every"), f"{where}.skill_every", errs, integer=True, minimum=0)
        _num(item.get("skill_mult"), f"{where}.skill_mult", errs, minimum=1.0)
        lo, hi = item.get("range_lo"), item.get("range_hi")
        if (
            isinstance(lo, (int, float))
            and isinstance(hi, (int, float))
            and hi <= lo
        ):
            errs.append(f"{where}.range_hi 必须大于 range_lo")
        dmg = item.get("dmg_type")
        if dmg not in DAMAGE_TYPES:
            errs.append(f"{where}.dmg_type 必须是 {DAMAGE_TYPES} 之一，实际 {dmg!r}")
        if errs:
            problems.extend(f"{where}: {e}" for e in errs)
            continue
        out[oid] = OperatorDef(
            oid=oid,
            name=str(item.get("name") or oid),
            rarity=int(item["rarity"]),
            atk=int(item["atk"]),
            interval=float(item["interval"]),
            range_lo=float(item["range_lo"]),
            range_hi=float(item["range_hi"]),
            dmg_type=dmg,
            crit_rate=float(item.get("crit_rate", 0.0)),
            crit_mult=float(item.get("crit_mult", 1.5)),
            skill_every=int(item.get("skill_every", 0)),
            skill_mult=float(item.get("skill_mult", 1.0)),
        )
    return out


def _build_enemies(raw, problems: List[str]) -> Dict[str, EnemyDef]:
    if not isinstance(raw, list):
        problems.append("enemies 必须是数组")
        return {}
    out: Dict[str, EnemyDef] = {}
    for i, item in enumerate(raw):
        errs: List[str] = []
        where = f"enemies[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} 必须是对象")
            continue
        eid = item.get("eid")
        if not isinstance(eid, str) or not eid:
            errs.append(f"{where}.eid 缺失或非字符串")
        elif eid in out:
            errs.append(f"{where}.eid 重复: {eid}")
        _num(item.get("hp"), f"{where}.hp", errs, integer=True, minimum=1, maximum=1_000_000_000)
        _num(item.get("defense"), f"{where}.defense", errs, integer=True, minimum=0, maximum=1_000_000)
        _num(item.get("speed"), f"{where}.speed", errs, minimum=0.01, maximum=1000.0)
        _num(item.get("leak"), f"{where}.leak", errs, integer=True, minimum=1)
        if errs:
            problems.extend(f"{where}: {e}" for e in errs)
            continue
        out[eid] = EnemyDef(
            eid=eid,
            name=str(item.get("name") or eid),
            hp=int(item["hp"]),
            defense=int(item.get("defense", 0)),
            speed=float(item["speed"]),
            leak=int(item.get("leak", 1)),
        )
    return out


def _build_stages(raw, problems: List[str], enemies: Dict[str, EnemyDef]) -> Dict[str, StageDef]:
    if not isinstance(raw, list):
        problems.append("stages 必须是数组")
        return {}
    out: Dict[str, StageDef] = {}
    for i, item in enumerate(raw):
        errs: List[str] = []
        where = f"stages[{i}]"
        if not isinstance(item, dict):
            problems.append(f"{where} 必须是对象")
            continue
        sid = item.get("sid")
        if not isinstance(sid, str) or not sid:
            errs.append(f"{where}.sid 缺失或非字符串")
        elif sid in out:
            errs.append(f"{where}.sid 重复: {sid}")
        _num(item.get("path_length"), f"{where}.path_length", errs, minimum=0.1, maximum=1_000_000.0)
        _num(item.get("base_hp"), f"{where}.base_hp", errs, integer=True, minimum=1)
        _num(item.get("three_star_lives"), f"{where}.three_star_lives", errs, integer=True, minimum=1)
        base_hp = item.get("base_hp")
        three_star = item.get("three_star_lives")
        if isinstance(base_hp, int) and isinstance(three_star, int) and three_star > base_hp:
            errs.append(f"{where}.three_star_lives({three_star}) 不能大于 base_hp({base_hp})")
        waves_raw = item.get("waves")
        if not isinstance(waves_raw, list) or not waves_raw:
            errs.append(f"{where}.waves 必须是非空数组")
        else:
            waves: List[WaveDef] = []
            for j, w in enumerate(waves_raw):
                ww = f"{where}.waves[{j}]"
                werrs: List[str] = []
                if not isinstance(w, dict):
                    werrs.append(f"{ww} 必须是对象")
                else:
                    enemy_id = w.get("enemy_id")
                    if not isinstance(enemy_id, str) or not enemy_id:
                        werrs.append(f"{ww}.enemy_id 缺失")
                    elif enemy_id not in enemies:
                        werrs.append(f"{ww}.enemy_id 引用了不存在的敌人 {enemy_id!r}（REQ-CFG-003）")
                    _num(w.get("count"), f"{ww}.count", werrs, integer=True, minimum=1)
                    _num(w.get("start_time"), f"{ww}.start_time", werrs, minimum=0.0)
                    _num(w.get("interval"), f"{ww}.interval", werrs, minimum=0.001)
                if werrs:
                    errs.extend(werrs)
                    continue
                waves.append(
                    WaveDef(
                        enemy_id=w["enemy_id"],
                        count=int(w["count"]),
                        start_time=float(w.get("start_time", 0.0)),
                        interval=float(w.get("interval", 1.0)),
                    )
                )
        if errs:
            problems.extend(f"{where}: {e}" for e in errs)
            continue
        out[sid] = StageDef(
            sid=sid,
            name=str(item.get("name") or sid),
            path_length=float(item["path_length"]),
            base_hp=int(item["base_hp"]),
            three_star_lives=int(item["three_star_lives"]),
            waves=tuple(waves),
        )
    return out


def load_catalog(data_dir=None) -> Catalog:
    """加载并校验全部配置；任一问题 → 抛 ConfigError（汇总所有问题）。"""
    base = Path(data_dir) if data_dir else DATA_DIR
    problems: List[str] = []
    files = {
        "operators": base / "operators.json",
        "enemies": base / "enemies.json",
        "stages": base / "stages.json",
    }
    raw = {}
    for key, path in files.items():
        if not path.exists():
            problems.append(f"缺少配置文件: {path}")
        else:
            raw[key] = _read_json(path)

    ops = _build_operators(raw.get("operators", []), problems) if "operators" in raw else {}
    enems = _build_enemies(raw.get("enemies", []), problems) if "enemies" in raw else {}
    stgs = _build_stages(raw.get("stages", []), problems, enems) if "stages" in raw else {}

    if problems:
        raise ConfigError(
            "配置校验失败（共 %d 项问题）:\n" % len(problems)
            + "\n".join(f"  - {p}" for p in problems)
        )
    return Catalog(operators=ops, enemies=enems, stages=stgs)
