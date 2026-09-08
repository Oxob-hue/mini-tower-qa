"""W2 规则与边界用例矩阵（对齐 docs/requirements.md 的 REQ 条目）。

设计原则：
1. 用例从「需求条目」出发构造被测场景，断言的期望值 = 需求文档手工推导的结果
   （黄金样本），不是"看实现抄出来的值"——这样才能让测试真正抓住实现缺陷；
2. 只依赖引擎公开 API（run_battle / physical_damage / 数据模型），
   随机源关闭（无暴击）或 seed 固定，全部可复现；
3. 用例编号见 docs/test-case-matrix.md，与 REQ 形成追踪矩阵（RTM）。

本文件用 unittest 编写（与 tests/test_smoke.py 一致），装有 pytest 的环境可直接运行。
"""

import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mini_tower.combat import physical_damage, run_battle  # noqa: E402
from mini_tower.models import EnemyDef, OperatorDef, StageDef, WaveDef  # noqa: E402


# --------------------------------------------------------------------------
# 场景构造小工具：直接构造被测对象实例，精确可控
# --------------------------------------------------------------------------

def O(oid="op", atk=100, interval=1.0, range_lo=0.0, range_hi=10.0,
      dmg_type="physical", crit_rate=0.0, crit_mult=1.5,
      skill_every=0, skill_mult=1.0, rarity=5, name="测试干员"):
    return OperatorDef(oid=oid, name=name, rarity=rarity, atk=atk, interval=interval,
                       range_lo=range_lo, range_hi=range_hi, dmg_type=dmg_type,
                       crit_rate=crit_rate, crit_mult=crit_mult,
                       skill_every=skill_every, skill_mult=skill_mult)


def E(eid="e", hp=1000, defense=0, speed=1.0, leak=1, name="测试敌人"):
    return EnemyDef(eid=eid, name=name, hp=hp, defense=defense, speed=speed, leak=leak)


def W(eid, count=1, start=0.0, interval=1.0):
    return WaveDef(enemy_id=eid, count=count, start_time=start, interval=interval)


def S(waves, path=50.0, base_hp=10, three_star_lives=8, sid="s"):
    return StageDef(sid=sid, name="测试关卡", path_length=path,
                    base_hp=base_hp, three_star_lives=three_star_lives,
                    waves=tuple(waves))


def battle(team, stage, enemies, seed=0, max_time=600.0):
    """跑一局，返回 BattleResult。enemies: {eid: EnemyDef}"""
    return run_battle(enemies, stage, list(team), seed=seed, max_time=max_time)


def landed(result, kind=("attack", "skill")):
    """取全部命中事件（attack/skill），返回 [(t, kind, dmg), ...]，dmg 从 detail 解析。"""
    out = []
    for ev in result.events:
        if ev.kind in kind:
            dmg = int(ev.detail.split("dmg=")[1].split()[0]) if "dmg=" in ev.detail else 0
            out.append((ev.t, ev.kind, dmg))
    return out


# --------------------------------------------------------------------------
# 伤害结算 DMG
# --------------------------------------------------------------------------

class TestDamageRules(unittest.TestCase):
    """REQ-DMG-001..005：伤害公式与结算顺序。"""

    def test_dmg001_physical_armor_subtraction(self):
        """atk100 vs def30 → 70（减法减免，黄金样本）。"""
        r = battle([O(atk=100)], S([W("e")], path=50),
                   {"e": E(hp=70, defense=30)})
        hits = landed(r)
        self.assertEqual(hits[0][2], 70)
        self.assertEqual(r.kills, 1)
        self.assertTrue(r.clear)

    def test_dmg001_floor_5pct_when_armor_wins(self):
        """REQ-DMG-004：物理伤害下限 = ⌈atk×5%⌉。atk95 vs def100 → 5。"""
        r = battle([O(atk=95)], S([W("e")], path=50),
                   {"e": E(hp=5, defense=100)})
        self.assertEqual(landed(r)[0][2], 5)

    def test_dmg004_floor_never_below_one(self):
        """atk20 vs def1000 → 下限 ⌈1.0⌉=1，绝不为 0/负。"""
        r = battle([O(atk=20)], S([W("e")], path=50),
                   {"e": E(hp=1, defense=1000)})
        self.assertEqual(landed(r)[0][2], 1)

    def test_dmg002_true_damage_ignores_armor(self):
        """真实伤害：atk300 vs def1000 → 每击 300（两次击杀 hp600）。"""
        r = battle([O(atk=300, dmg_type="true")], S([W("e")], path=50),
                   {"e": E(hp=600, defense=1000)})
        hits = landed(r)
        self.assertEqual([d for _, _, d in hits], [300, 300])
        self.assertEqual(r.kills, 1)

    def test_dmg003_crit_multiplies_after_armor(self):
        """REQ-DMG-003：先减免后暴击。(100-30)×2=140，而不是 100×2-30=170。"""
        r = battle([O(atk=100, crit_rate=1.0, crit_mult=2.0)],
                   S([W("e")], path=50), {"e": E(hp=140, defense=30)})
        self.assertEqual(landed(r)[0][2], 140)

    def test_dmg005_first_attack_delay_equals_interval(self):
        """REQ-DMG-005：首次攻击前摇 = interval（2.5s）。"""
        r = battle([O(atk=100, interval=2.5)], S([W("e")], path=50),
                   {"e": E(hp=1, defense=0)})
        self.assertEqual(r.end_time, 2.5)
        self.assertEqual(r.events[1].t, 2.5)   # 事件0=spawn, 事件1=首次命中

    def test_dmg005_attack_interval_kept_after_miss(self):
        """射程外空挥不改节拍、不产生伤害；敌人到达仍按原计划（漏怪 1 只通关）。"""
        r = battle([O(atk=100, range_hi=1.0)], S([W("e")], path=10),
                   {"e": E(hp=1000, defense=0)})
        hits = landed(r)
        self.assertEqual(len(hits), 1)          # 只有 t=1 命中，其余全部空挥
        self.assertEqual(hits[0][0], 1.0)
        self.assertEqual(r.reason, "victory")   # 关键：空挥不能导致空转到超时
        self.assertEqual(r.end_time, 10.0)      # 敌人到达即清场 → 正常判胜
        self.assertEqual(r.leaked, 1)


# --------------------------------------------------------------------------
# 技能 SKL
# --------------------------------------------------------------------------

class TestSkillRules(unittest.TestCase):
    """REQ-SKL-001..004：技能触发时机、无视防御、暴击叠加。"""

    def test_skl001_skill_on_every_nth_landed_hit(self):
        """skill_every=3：命中序列应为 普通,普通,技能,普通,普通,技能…（第 3/6 次）。"""
        r = battle([O(atk=100, skill_every=3, skill_mult=2.0)],
                   S([W("e")], path=50), {"e": E(hp=20_000, defense=30, speed=0.1)},
                   max_time=6.5)
        hits = landed(r)[:6]
        self.assertEqual([k for _, k, _ in hits],
                         ["attack", "attack", "skill", "attack", "attack", "skill"])
        # 技能无视防御（REQ-SKL-001）：100×2=200；普攻 100-30=70
        self.assertEqual([d for _, _, d in hits], [70, 70, 200, 70, 70, 200])

    def test_skl002_skill_every_one_fires_every_hit(self):
        """skill_every=1 → 每次成功命中都是技能（边界：N=1）。"""
        r = battle([O(atk=100, skill_every=1, skill_mult=2.0)],
                   S([W("e")], path=50), {"e": E(hp=200, defense=0)})
        hits = landed(r)
        self.assertEqual(hits[0][1], "skill")
        self.assertEqual(hits[0][2], 200)

    def test_skl001_no_skill_when_disabled(self):
        """skill_every=0 → 永不触发技能。"""
        r = battle([O(atk=100)], S([W("e")], path=50),
                   {"e": E(hp=100, defense=0)})
        self.assertTrue(all(k == "attack" for _, k, _ in landed(r)))

    def test_skl003_skill_affected_by_crit(self):
        """技能同样吃暴击乘区：skill 200 × crit 1.5 = 300。"""
        r = battle([O(atk=100, skill_every=1, skill_mult=2.0,
                      crit_rate=1.0, crit_mult=1.5)],
                   S([W("e")], path=50), {"e": E(hp=300, defense=30)})
        self.assertEqual(landed(r)[0][2], 300)   # 200 × 1.5（技能无视防御后暴击）

    def test_skl001_missed_attack_does_not_advance_skill_counter(self):
        """只有“成功命中”计入技能计数：敌方晚入场 → 空挥期不推进计数。"""
        r = battle([O(atk=100, interval=1.0, skill_every=2, skill_mult=2.0)],
                   S([W("e", start=3.0)], path=50),
                   {"e": E(hp=10_000, defense=0, speed=0.1)}, max_time=6.5)
        hits = landed(r)
        # 敌方 t=3 入场：t=3(#1 普攻) → t=4(#2 技能) → t=5(#3 普攻) → t=6(#4 技能)
        self.assertEqual(hits[0][0], 3.0)
        self.assertEqual([k for _, k, _ in hits[:4]],
                         ["attack", "skill", "attack", "skill"])


# --------------------------------------------------------------------------
# 索敌 TGT
# --------------------------------------------------------------------------

class TestTargetingRules(unittest.TestCase):
    """REQ-TGT-001：攻击范围内最接近我方终点（位置最大）的敌人。"""

    def test_tgt001_targets_furthest_enemy_first(self):
        """e0 先入场走得更远；两敌同在场时优先攻击 e0，且 e0 先于 e1 阵亡。"""
        e0, e1 = E(eid="a", hp=300, speed=0.5), E(eid="b", hp=300, speed=0.5)
        enemies = {"a": e0, "b": e1}
        stage = S([W("a", start=0.0), W("b", start=5.0)], path=50)
        r = battle([O(atk=100, interval=0.5)], stage, enemies)
        kill_a = next(i for i, ev in enumerate(r.events) if ev.kind == "kill" and ev.subject.startswith("a"))
        first_dmg_b = next(i for i, ev in enumerate(r.events)
                           if ev.kind in ("attack", "skill") and ev.subject.startswith("b"))
        self.assertLess(kill_a, first_dmg_b)     # a 被杀时 b 还没挨过打
        self.assertEqual(r.kills, 2)


# --------------------------------------------------------------------------
# 关卡规则 STG
# --------------------------------------------------------------------------

class TestStageRules(unittest.TestCase):
    """REQ-STG-001..006：波次/漏怪/胜负/三星/超时。"""

    def test_stg002_leak_deducts_enemy_leak_value(self):
        """漏怪按 enemy.leak 扣生命：leak=3 → lives 10-3=7。"""
        r = battle([O(atk=10)], S([W("e")], path=10),
                   {"e": E(hp=1000, defense=0, leak=3)})
        self.assertEqual(r.lives_left, 7)
        self.assertEqual(r.leaked, 1)
        self.assertTrue(r.clear)
        self.assertFalse(r.three_star)

    def test_stg005_three_star_lives_equal_boundary(self):
        """三星边界：剩余生命 == three_star_lives(8) → 三星。"""
        r = battle([O(atk=10)], S([W("e"), W("e", start=5.0)], path=10),
                   {"e": E(hp=1000, defense=0, leak=1)})
        self.assertEqual(r.lives_left, 8)
        self.assertTrue(r.three_star)

    def test_stg005_three_star_lives_below_boundary(self):
        """三星边界：剩余生命 7 < 8 → 非三星（但通关）。"""
        r = battle([O(atk=10)], S([W("e"), W("e", start=5.0), W("e", start=10.0)], path=10),
                   {"e": E(hp=1000, defense=0, leak=1)})
        self.assertEqual(r.lives_left, 7)
        self.assertTrue(r.clear)
        self.assertFalse(r.three_star)

    def test_stg003_defeat_when_base_reaches_zero(self):
        """base_hp=3，三只 leak=1 依序漏怪 → 第三只到达瞬间判负（defeat_leak）。"""
        stage = S([W("e", start=0.0), W("e", start=5.0), W("e", start=10.0)],
                  path=10, base_hp=3, three_star_lives=2)
        r = battle([O(atk=10)], stage, {"e": E(hp=1000, defense=0, leak=1)})
        self.assertFalse(r.clear)
        self.assertEqual(r.reason, "defeat_leak")
        self.assertEqual(r.lives_left, 0)
        self.assertEqual(r.leaked, 3)
        self.assertEqual(r.end_time, 20.0)      # 第三只敌人到达时刻（10+10）

    def test_stg004_no_premature_victory_between_waves(self):
        """两波间隔 20s：第一波清空后不得提前判胜，必须等第二波处理完。"""
        r = battle([O(atk=100)], S([W("e", start=0.0), W("e", start=20.0)], path=50),
                   {"e": E(hp=1, defense=0)})
        self.assertEqual(r.kills, 2)
        self.assertTrue(r.clear)
        self.assertGreaterEqual(r.end_time, 20.0)

    def test_stg006_timeout_guard_returns_defeat(self):
        """超时守卫：敌人打不死且 600s 内到不了终点 → 判负 timeout 而非死循环。"""
        r = battle([O(atk=1)], S([W("e")], path=100_000, base_hp=10),
                   {"e": E(hp=10**9, defense=0, speed=0.01)})
        self.assertFalse(r.clear)
        self.assertEqual(r.reason, "timeout")
        self.assertEqual(r.end_time, 600.0)

    def test_victory_reason_and_leak_count_when_single_leak(self):
        """一只打不死的敌人漏怪后：清场即 victory，lives>0。"""
        r = battle([O(atk=10, range_hi=2.0)], S([W("e")], path=10),
                   {"e": E(hp=1000, defense=0, speed=1.0)})
        self.assertEqual(r.reason, "victory")
        self.assertEqual(r.leaked, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
