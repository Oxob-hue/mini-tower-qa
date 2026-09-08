"""AI 辅助测试（W5）：需求→测试点 / 数值改动→风险评估 / 失败日志聚类。

设计（面试口径）：**"会用 AI" ≠ "把 AI 输出当结论"。**
本模块把 AI 当作"初稿生成器"，产出必须过三道闸（REQ-AI-001..007）：
  ① 结构化 JSON + schema 校验 —— 非法/缺失字段的输出直接拒绝，不进入后续流程；
  ② 数值类建议与引擎模拟交叉验证 —— 建议区间用真实模拟校准，不一致自动驳回/修正；
  ③ 人工复核留痕 —— 每条 AI 产出落审计日志（pending → approved），prompt/输出/校验结果全程可追溯。

提供者可插拔（REQ-AI-007）：
  - 默认 StubProvider：本地规则"仿 AI"初稿（确定性、离线可复现，供测试/CI/无 Key 演示）；
  - 配置 AI_HTTP_URL + AI_API_KEY（+ AI_MODEL）后使用 HttpProvider 调真实 LLM；
  管线与三道闸完全一致，切换提供者不改变任何下游逻辑。
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

# --------------------------------------------------------------------------
# 一、提供者层
# --------------------------------------------------------------------------


class AIUnavailable(RuntimeError):
    """真实 LLM 不可用（无 Key/网络失败），调用方可降级 StubProvider。"""


def _extract_json(text: str) -> object:
    """从模型回复中稳健提取 JSON（容忍 markdown 围栏与前后缀文字）。"""
    text = re.sub(r"```(?:json)?", "", text)
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
            return obj
        except json.JSONDecodeError:
            continue
    raise AIUnavailable(f"回复中未找到合法 JSON: {text[:120]!r}")


class HttpProvider:
    """OpenAI 兼容 Chat Completions 客户端（urllib，零第三方依赖）。"""

    def __init__(self, url: str, api_key: str, model: str = "gpt-4o-mini",
                 timeout: float = 30.0):
        self.url, self.api_key, self.model, self.timeout = url, api_key, model, timeout

    def complete(self, system: str, user: str) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            raise AIUnavailable(f"LLM 请求失败: {exc}") from exc


class StubProvider:
    """本地规则"仿 AI"提供者：确定性、离线可复现，用于测试/CI/无 Key 演示。

    它不是真 AI，而是让"三道闸 + 交叉验证"流水线可以脱离网络被验证与演示；
    接入真实 LLM（HttpProvider）时，同样的产出契约与闸门直接复用。
    """

    name = "stub(本地规则)"

    def complete(self, system: str, user: str) -> str:
        intent = "test_points" if "测试点" in user else (
            "risk" if "风险" in user else "cluster")
        if intent == "test_points":
            return self._points(user)
        if intent == "risk":
            return self._risk(user)
        return self._cluster(user)

    # ---- 需求 → 测试点（启发式：把需求文本里的数值/时序词映射到边界类型）----
    def _points(self, user: str) -> str:
        library = [
            ("数值下限与非法值(0/负)", "异常", "数值字段为 0/负/非整数应被校验层拒绝，测试点应在加载期断言抛错"),
            ("恰好相等边界(def==atk)", "边界", "物理伤害 max(atk-def,⌈5%⌉) 在 def==atk 与 def=atk-1 处应给出不同结果"),
            ("同频共振(攻击间隔==敌人生成间隔)", "边界", "攻击节拍与波次生成同频时可能整波一个不漏/全漏，需专门验证"),
            ("极限攻速(interval 取允许最小)", "边界", "interval 下界附近事件密度最高，验证无事件丢失/乱序"),
            ("技能在击杀当帧触发", "顺序", "技能命中恰好击杀目标时，技能计数与 kill 事件顺序需符合 REQ"),
            ("暴击概率端点 0 与 1", "边界", "crit_rate=0 永不暴击、=1 必暴击，验证判定与乘区"),
            ("保底计数归零后首抽", "边界", "出 6★ 后 pity 归零：下一抽不继承上一段软保底进度"),
            ("超大数值压力(1e9)", "异常", "hp/atk 达上限数量级时无溢出/取整异常，结果仍在 int 域内"),
            ("多目标同位置排序稳定", "顺序", "两敌同帧同一位置时索敌结果确定（种子固定可复现）"),
            ("最后一只敌人恰好贴脸被杀/漏", "边界", "终点前最后一击与到达同帧的结算顺序（REQ-DMG-007）"),
        ]
        m = re.search(r"REQ-[A-Z]+-\d+", user)
        req_hint = m.group(0) if m else "REQ-?"
        shown = min(6, len(library))
        pts = [{
            "req_hint": req_hint,
            "focus": focus,                                  # 边界/异常点的名称（用于与已知覆盖比对）
            "boundary": category == "边界",
            "test": test,
            "priority": 1 if category == "边界" else 2,
        } for focus, category, test in library[:shown]]
        return json.dumps({"test_points": pts, "meta": {"provider": self.name}}, ensure_ascii=False)

    # ---- 数值改动 → 风险评估（刻意给出"略激进"的区间，供引擎交叉验证纠偏）----
    def _risk(self, user: str) -> str:
        m = re.search(r"atk[：:=\s]*(\d+)\s*[-→]\s*(\d+)", user)
        old = int(m.group(1)) if m else 140
        new = int(m.group(2)) if m else 98
        drop = (old - new) / old
        if drop >= 0.25:
            risk, reason = "high", [f"攻击力下调 {drop:.0%}，临界编队很可能跌破三星设计目标"]
            floor = int(old * 0.78)   # 刻意偏低，交叉验证会纠正
        elif drop >= 0.10:
            risk, reason = "medium", ["下调幅度中等，需回归临界关卡确认"]
            floor = int(old * 0.9)
        else:
            risk, reason = "low", ["下调幅度小，风险可控"]
            floor = int(old * 0.95)
        return json.dumps({
            "risk": risk,
            "reasons": reason,
            "suggested_interval": {"operator": "storm_d", "field": "atk",
                                   "min": floor, "max": old},
            "meta": {"provider": self.name},
        }, ensure_ascii=False)

    # ---- 失败日志聚类 ----
    def _cluster(self, user: str) -> str:
        rows = json.loads(user.split("记录=", 1)[1]) if "记录=" in user else []
        buckets: Dict[str, list] = {}
        for r in rows:
            if r.get("reason") == "timeout":
                key = "清场能力不足(timeout)"
            elif r.get("leaked", 0) > 0 and r.get("lives_left", 9) <= 0:
                key = "防线崩盘(defeat_leak)"
            elif r.get("leaked", 0) > 0:
                key = "漏怪:输出不足或防线缺口"
            else:
                key = "通过但未三星"
            buckets.setdefault(key, []).append(r)
        clusters = [{"label": k, "count": len(v),
                     "sample": {kk: v[0][kk] for kk in ("stage_id", "team_id", "leaked", "reason")}
                     if v else {}}
                    for k, v in buckets.items()]
        return json.dumps({"clusters": clusters, "meta": {"provider": self.name}},
                          ensure_ascii=False)


def default_provider():
    """有 Key/URL 配置则用真实 LLM，否则本地规则提供者（离线可复现）。"""
    url, key = os.environ.get("AI_HTTP_URL"), os.environ.get("AI_API_KEY")
    if url and key:
        return HttpProvider(url, key, os.environ.get("AI_MODEL", "gpt-4o-mini"))
    return StubProvider()


# --------------------------------------------------------------------------
# 二、schema 校验（防幻觉第一道闸：结构化 + 类型 + 枚举）
# --------------------------------------------------------------------------


class AIOutputError(ValueError):
    """AI 输出未通过 schema 校验。"""


def _type_ok(val, kind: str) -> bool:
    if kind == "list":
        return isinstance(val, list)
    if kind == "dict":
        return isinstance(val, dict)
    if kind == "str":
        return isinstance(val, str)
    if kind == "bool":
        return isinstance(val, bool)
    if kind == "int":
        return isinstance(val, int) and not isinstance(val, bool)
    if kind == "float":
        return isinstance(val, (int, float)) and not isinstance(val, bool)
    if kind.startswith("enum:"):
        return val in kind.split(":", 1)[1].split("|")
    return True


def _errs_validate(payload: object, spec: Dict[str, tuple]) -> List[str]:
    """极简 schema：spec[k]=(kind, required)。kind ∈ str/int/float/bool/list/dict/enum:a|b"""
    errs: List[str] = []
    if not isinstance(payload, dict):
        return ["输出不是 JSON 对象"]
    for key, (kind, required) in spec.items():
        if key not in payload:
            if required:
                errs.append(f"缺少必填字段 {key}")
            continue
        if not _type_ok(payload[key], kind):
            errs.append(f"字段 {key} 类型不符: 期望 {kind}, 实际 {type(payload[key]).__name__}")
    return errs


_POINTS_SPEC = {
    "test_points": ("list", True),
    "meta": ("dict", True),
}
_POINT_SPEC = {
    "req_hint": ("str", True),
    "focus": ("str", True),
    "boundary": ("bool", True),
    "test": ("str", True),
    "priority": ("int", True),
}
_RISK_SPEC = {
    "risk": ("enum:high|medium|low", True),
    "reasons": ("list", True),
    "suggested_interval": ("dict", True),
}
_CLUSTER_SPEC = {"clusters": ("list", True), "meta": ("dict", True)}


def _validate(payload: object, spec: Dict[str, tuple], item_spec: Optional[Dict[str, tuple]] = None) -> None:
    errs = _errs_validate(payload, spec)
    if item_spec and isinstance(payload, dict):
        for key in payload:
            if isinstance(payload[key], list) and isinstance(item_spec, dict):
                for item in payload[key]:
                    if isinstance(item, dict):
                        errs += _errs_validate(item, item_spec)
    if errs:
        raise AIOutputError("; ".join(errs))


# --------------------------------------------------------------------------
# 三、审计日志（人工复核留痕）
# --------------------------------------------------------------------------


@dataclass
class AuditRecord:
    capability: str            # test_points | risk_assessment | log_cluster
    provider: str
    user_prompt: str
    raw_output: str
    schema_ok: bool = False
    engine_verified: Optional[bool] = None
    human_review: str = "pending"   # pending | approved | rejected
    note: str = ""
    ts: float = field(default_factory=time.time)


class AuditLog:
    """内存审计日志；可选落盘 results/ai-audit.jsonl（无写权限时忽略）。"""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.records: List[AuditRecord] = []

    def append(self, rec: AuditRecord) -> int:
        self.records.append(rec)
        if self.path:
            try:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec.__dict__, ensure_ascii=False) + "\n")
            except OSError:
                pass          # 无写权限时审计仍保留在内存，演示/CI 不受影响
        return len(self.records) - 1

    def review(self, idx: int, verdict: str, note: str = "") -> None:
        self.records[idx].human_review = verdict
        self.records[idx].note = note


# --------------------------------------------------------------------------
# 四、三条 AI 能力（能力管线：生成 → schema 校验 → 审计；数值类再交叉验证）
# --------------------------------------------------------------------------


def _complete_checked(provider, system: str, user: str, capability: str,
                      spec: Dict, item_spec: Dict, audit: AuditLog) -> Dict:
    raw = provider.complete(system, user)
    rec = AuditRecord(capability=capability, provider=getattr(provider, "name", "http"),
                      user_prompt=user, raw_output=raw)
    try:
        payload = _extract_json(raw)
        _validate(payload, spec, item_spec)
        rec.schema_ok = True
        audit.append(rec)
        return {"status": "ok", "data": payload, "audit_id": len(audit.records) - 1}
    except (AIUnavailable, AIOutputError) as exc:
        rec.note = str(exc)
        rec.schema_ok = False
        audit.append(rec)
        return {"status": "rejected", "issues": str(exc), "audit_id": len(audit.records) - 1}


def generate_test_points(requirement_text: str, provider=None, audit: Optional[AuditLog] = None,
                         known_boundary_types: Optional[set] = None) -> Dict:
    """AI 需求 → 测试点/边界；统计相对已知边界的"新增边界数"（人审后纳入用例库）。"""
    provider = provider or default_provider()
    audit = audit or AuditLog()
    sysp = "你是资深游戏 QA。只输出 JSON：{\"test_points\":[{req_hint,focus,boundary,test,priority}], \"meta\":{}}"
    out = _complete_checked(provider, sysp, f"给以下需求条目拆测试点与边界：{requirement_text}",
                            "test_points", _POINTS_SPEC, _POINT_SPEC, audit)
    if out["status"] == "ok":
        points = out["data"]["test_points"]
        known = known_boundary_types or set()
        # 口径：凡"AI 提出的检查点名称"不在人已覆盖集合内，即视为"补充的新点"（人审后入库）
        novel = [p for p in points if p["focus"] not in known]
        out["novel_count"] = len(novel)
        out["novel_points"] = novel
    return out


def assess_numeric_risk(change_summary: str, provider=None, audit: Optional[AuditLog] = None) -> Dict:
    """AI 数值改动 → 风险评估（risk/reasons/建议区间）。数值建议须再过引擎交叉验证。"""
    provider = provider or default_provider()
    audit = audit or AuditLog()
    sysp = ("你是数值策划顾问。只输出 JSON：{\"risk\":\"high|medium|low\",\"reasons\":[...],"
            "\"suggested_interval\":{\"operator\":..,\"field\":\"atk\",\"min\":..,\"max\":..}}")
    return _complete_checked(provider, sysp, f"评估以下数值改动风险：{change_summary}",
                             "risk_assessment", _RISK_SPEC, None, audit)


def classify_failure_logs(records: Sequence[dict], provider=None,
                          audit: Optional[AuditLog] = None) -> Dict:
    """AI 失败日志聚类。records: [{stage_id, team_id, leaked, lives_left, reason}...]"""
    provider = provider or default_provider()
    audit = audit or AuditLog()
    sysp = ("你是测试分析助手。只输出 JSON：{\"clusters\":[{\"label\",count,sample}], \"meta\":{}}")
    user = "对以下失败/未三星批次聚类，给出根因倾向标签；记录=" + json.dumps(list(records), ensure_ascii=False)
    return _complete_checked(provider, sysp, user, "log_cluster", _CLUSTER_SPEC,
                             {"label": ("str", True), "count": ("int", True),
                              "sample": ("dict", True)}, audit)


def cluster_accuracy(result: Dict, ground_truth: Dict[str, str]) -> Dict:
    """聚类准确率：把 AI 聚类标签与"真实根因"比对（样本级）。"""
    if result.get("status") != "ok":
        return {"accuracy": 0.0, "total": 0, "hit": 0}
    predicted = {}
    for c in result["data"]["clusters"]:
        s = c.get("sample") or {}
        sid = (s.get("stage_id"), s.get("team_id"))
        if sid != (None, None):
            predicted[sid] = c["label"]
    hits = sum(1 for sid, truth in ground_truth.items() if predicted.get(sid) == truth)
    total = len(ground_truth)
    return {"accuracy": hits / total if total else 0.0, "total": total, "hit": hits,
            "predicted": predicted}


# --------------------------------------------------------------------------
# 五、引擎交叉验证（防幻觉第二道闸：数值建议必须被真实模拟校准）
# --------------------------------------------------------------------------


def cross_validate_atk_interval(catalog, stage_id: str, team: Sequence[str],
                                operator_id: str, ai_min: int, ai_max: int,
                                star_target: float = 0.95,
                                rounds: int = 400, seed: int = 20240301) -> Dict:
    """把 AI 建议的 atk 区间 [ai_min, ai_max] 用引擎实测校准。

    返回 verified_floor：三星率≥star_target 的最小 atk（实测）。
    若 ai_min < verified_floor → 建议偏激进，标记 mismatch 并给出修正后的区间。
    """
    from dataclasses import replace
    from .simulator import run_batch

    def star_at(atk: int) -> float:
        base = catalog.operators[operator_id]
        op = replace(base, atk=atk)
        cat = replace(catalog, operators={**catalog.operators, operator_id: op})
        return run_batch(cat, stage_id, team, rounds=rounds, master_seed=seed).three_star_rate

    lo, hi = min(ai_min, ai_max), max(ai_min, ai_max)
    verified = hi
    found = False
    for atk in range(lo, hi + 1):
        if star_at(atk) >= star_target:
            verified = atk
            found = True
            break
    if not found:
        verified = hi + 1
    ok = ai_min >= verified
    return {
        "ai_interval": {"min": ai_min, "max": ai_max},
        "verified_floor": verified,
        "verified_interval": {"min": verified, "max": ai_max},
        "consistent": bool(ok),
        "correction": None if ok else {"reason": "AI 下限低于实测达标线",
                                       "corrected_min": verified},
        "star_target": star_target,
    }
