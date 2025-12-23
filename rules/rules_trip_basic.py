# rules_trip_basic.py（摘要）
# import re, core.registry as R, core.builder as gb
# from core.registry import register_rule

# # --- 抽取速度/时间/距离/间距/时间差 ---
# SPEED = [
#     (r'(\d+(?:\.\d+)?)\s*(千?米|公里|km)\s*/\s*(小时|h)', lambda m,g: g.add_node(type="Speed", value=float(m.group(1)), unit="km/h")),
#     (r'(\d+(?:\.\d+)?)\s*(米|m)\s*/\s*(秒|s)',           lambda m,g: g.add_node(type="Speed", value=float(m.group(1)), unit="m/s")),
# ]
# TIME  = [
#     (r'(\d+(?:\.\d+)?)\s*(小时|h)',     lambda m,g: g.add_node(type="Time", value=float(m.group(1)), unit="h")),
#     (r'(\d+(?:\.\d+)?)\s*(分钟|min)',   lambda m,g: g.add_node(type="Time", value=float(m.group(1)), unit="min")),
#     (r'(\d+(?:\.\d+)?)\s*(秒|s)',       lambda m,g: g.add_node(type="Time", value=float(m.group(1)), unit="s")),
# ]
# LENGTH = [
#     (r'(相距|距离)\s*(\d+(?:\.\d+)?)\s*(千?米|公里|km)', lambda m,g: g.add_node(type="Length", value=float(m.group(2)), unit="km")),
#     (r'(相距|距离)\s*(\d+(?:\.\d+)?)\s*(米|m)',         lambda m,g: g.add_node(type="Length", value=float(m.group(2)), unit="m")),
# ]
# GAP = [
#     (r'(领先|落后|相差|间隔|相距)\s*(\d+(?:\.\d+)?)\s*(千?米|公里|km|米|m)', lambda m,g: g.add_node(type="Length", value=float(m.group(2)), role="gap", unit=m.group(3))),
#     (r'(早|晚).*?(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s)',                    lambda m,g: g.add_node(type="Time",   value=float(m.group(2)), role="delta_t", unit=m.group(3))),
# ]

# def detect_mode(text):
#     if re.search(r'(相向|迎面).*?(行|驶)|相遇', text): return "join"
#     if re.search(r'(同向|追及|追上|赶上)', text):       return "chase"
#     return "join"

# def hook(m, g):
#     t = g.graph.get("raw_text","")
#     for pat, fn in SPEED + TIME + LENGTH + GAP:
#         for mm in re.finditer(pat, t): fn(mm, g)
#     g.graph["topic"] = "trip"
#     g.graph["mode"]  = detect_mode(t)

# R.register_rule("trip", ("__AUTO__", hook))
import re
from core.registry import register_route, register_rule

# ==== Phase-1：路由（只加候选，不写 pattern） ====
register_route("trip", (
    r"(相向|迎面|相对).*?(行|驶)|相遇",
    lambda m, g: g.add_candidate("trip", "join",  confidence=0.9, source="kw")
))
register_route("trip", (
    r"(同向|追及|追上|赶上)",
    lambda m, g: g.add_candidate("trip", "chase", confidence=0.9, source="kw")
))
register_route("trip", (
    r"(\d+(?:\.\d+)?)\s*(km/h|千?米/小时|m/s|米/秒)|速度",
    lambda m, g: g.add_candidate("trip", g.G.graph.get("mode") or None, confidence=0.7, source="unit")
))
register_route("trip", (
    r"(相距|距离).*(千?米|公里|km|米|m)",
    lambda m, g: g.add_candidate("trip", g.G.graph.get("mode") or None, confidence=0.5, source="dist")
))

# ====== 路由：非同时出发（时间差 Δt） ======
# 甲先出发 1 小时后，乙从对面出发 / …先出发…小时后…出发
register_route("trip", (
    r"(先|后).*?出发.*?(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s).*?(后)?",
    lambda m,g: g.add_candidate("trip", "join", confidence=0.95, source="delta_t")
))
# 相隔 1 小时出发 / 两人相隔…后出发
register_route("trip", (
    r"(相隔|间隔)\s*(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s).*?出发",
    lambda m,g: g.add_candidate("trip", "join", confidence=0.95, source="delta_t")
))
# …小时后出发（前一句已给出另一人出发）——泛化兜底
register_route("trip", (
    r"(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s)\s*后.*?出发",
    lambda m,g: g.add_candidate("trip", "join", confidence=0.9, source="delta_t")
))

# 目标：多久/多长时间
pat_target_time = re.compile(r"多(久|长时间)", re.I)
# 先出发 X 小时后（支持换行/逗号）
pat_dt1 = re.compile(r"先出发\s*(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s)\s*后", re.I)
# 相隔/间隔 X …出发
pat_dt2 = re.compile(r"(相隔|间隔)\s*(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s)\s*出发", re.I)


# ==== Phase-2：抽取（节点） ====
# 速度
register_rule("trip", (re.compile(r'(\d+(?:\.\d+)?)\s*(千?米|公里|km)\s*/\s*(小时|h)', re.I),
    lambda m,g: g.add_node(type="Speed", value=float(m.group(1)), unit="km/h")))
register_rule("trip", (re.compile(r'(\d+(?:\.\d+)?)\s*(米|m)\s*/\s*(秒|s)', re.I),
    lambda m,g: g.add_node(type="Speed", value=float(m.group(1)), unit="m/s")))
# 时间
register_rule("trip", (re.compile(r'(\d+(?:\.\d+)?)\s*(小时|h)', re.I),
    lambda m,g: g.add_node(type="Time", value=float(m.group(1)), unit="h")))
register_rule("trip", (re.compile(r'(\d+(?:\.\d+)?)\s*(分钟|min)', re.I),
    lambda m,g: g.add_node(type="Time", value=float(m.group(1)), unit="min")))
register_rule("trip", (re.compile(r'(\d+(?:\.\d+)?)\s*(秒|s)', re.I),
    lambda m,g: g.add_node(type="Time", value=float(m.group(1)), unit="s")))
# 距离 & 初始间距
register_rule("trip", (re.compile(r'(相距|距离)\s*(\d+(?:\.\d+)?)\s*(千?米|公里|km)', re.I),
    lambda m,g: g.add_node(type="Length", value=float(m.group(2)), unit="km")))
register_rule("trip", (re.compile(r'(相距|距离)\s*(\d+(?:\.\d+)?)\s*(米|m)', re.I),
    lambda m,g: g.add_node(type="Length", value=float(m.group(2)), unit="m")))
register_rule("trip", (re.compile(r'(领先|落后|相差|间隔)\s*(\d+(?:\.\d+)?)\s*(千?米|公里|km|米|m)', re.I),
    lambda m,g: g.add_node(type="Length", value=float(m.group(2)), unit=m.group(3), role="gap")))
# 出发时间差
register_rule("trip", (re.compile(r'(早|晚).*?(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s)', re.I|re.S),
    lambda m,g: g.add_node(type="Time", value=float(m.group(2)), unit=m.group(3), role="delta_t")))
# 目标量（问几小时/多少秒）
register_rule("trip", (re.compile(r'(几|多少)\s*(小时|h|分钟|min|秒|s)', re.I),
    lambda m,g: (g.add_node(type="Time", value=None, unit=m.group(2), role="target"),
                 g.G.graph.__setitem__("target", "Time"))))

# ====== 抽取：时间差 Δt ======
# 先/后……出发……X 小时/分钟/秒（跨行也能匹配）
register_rule("trip", (
    re.compile(r"(先|后).*?出发.*?(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s).*?(后)?", re.I|re.S),
    lambda m,g: g.add_node(type="Time", value=float(m.group(2)), unit=m.group(3), role="delta_t")
))
# 相隔/间隔 X 时间出发
register_rule("trip", (
    re.compile(r"(相隔|间隔)\s*(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s).*?出发", re.I|re.S),
    lambda m,g: g.add_node(type="Time", value=float(m.group(2)), unit=m.group(3), role="delta_t")
))
# X 小时后出发（泛化）
register_rule("trip", (
    re.compile(r"(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s)\s*后.*?出发", re.I|re.S),
    lambda m,g: g.add_node(type="Time", value=float(m.group(1)), unit=m.group(2), role="delta_t")
))

# ====== 抽取：目标量（多久/多长时间） ======
register_rule("trip", (
    re.compile(r"(多(久|长时间))", re.I),
    lambda m,g: (g.add_node(type="Time", value=None, unit=None, role="target"),
                 g.G.graph.__setitem__("target", "Time"))
))