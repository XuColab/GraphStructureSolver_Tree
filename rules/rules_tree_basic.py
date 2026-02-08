# -*- coding: utf-8 -*-
import re, core.registry as R, core.builder as gb
from core.registry import register_route, register_rule

FLAGS = re.S | re.I   # 跨行 + 忽略大小写

def r(regex, action): return (re.compile(regex, FLAGS), action)

# ----------------- 通用工具 -----------------
def _to_number(s: str):
    """把捕获到的数字串安全转为 int/float。"""
    if s is None: return None
    s = s.strip().replace('．', '.').replace('，', '').replace(',', '')
    # return float(s) if '.' in s else int(s)
    try:
        v = float(s)
        return int(v) if abs(v - int(v)) < 1e-9 else v
    except: return None    

def _cap_number(patterns, text):
    """
    依次用一组regex去匹配text，找到第一个包含 (?P<num>...) 的命名分组。
    返回 number 或 None。
    """
    for pat in patterns:
        m = pat.search(text)
        if m and 'num' in m.groupdict():
            return _to_number(m.group('num'))
    return None

# ------------- Interval（间隔/相距）抽取：多写法 -------------
INTERVAL_PATTERNS = [
    # 经典 “每隔 10 米 / 间隔 10 米 / 相隔 10 米”
    re.compile(r'(?:每隔|间隔|相隔)\s*(?P<num>\d+(?:\.\d+)?)\s*米', FLAGS),

    # “相邻两棵/每两棵/两…之间 的 (距离|间隔|相距) 20 米”
    re.compile(r'(?:相邻|每两(?:个|棵|面|盏|根)|两(?:个|棵|面|盏|根)[^，。；]*?之间)[^，。；]*?(?:距离|间隔|相距)[是为]?\s*(?P<num>\d+(?:\.\d+)?)\s*米', FLAGS),

    # “每相距 20 米 / 每…相距…米”
    re.compile(r'每[^，。；]*?(?:相距|相隔|间距)[是为]?\s*(?P<num>\d+(?:\.\d+)?)\s*米', FLAGS),
]

INTERVAL_RULE = r(r'.+', lambda m,g: (
    (lambda v: g.add_node(type="Interval", value=v))(_cap_number(INTERVAL_PATTERNS, m.string))
    if (not g.has_node(type="Interval") and _cap_number(INTERVAL_PATTERNS, m.string) is not None)
    else None
))

# ================= 正则匹配规则库 =================
# ------------- 数值节点（长度、宽度、树数） -------------
# LENGTH_RULES = [
#     r(r'长\s*(\d+(?:\.\d+)?)\s*米', lambda m,g: g.add_node(type="Length", value=_to_number(m.group(1)))),
#     r(r'宽\s*(\d+(?:\.\d+)?)\s*米', lambda m,g: g.add_node(type="Width",  value=_to_number(m.group(1)))),
#     r(r'周长[是为]?\s*(\d+(?:\.\d+)?)\s*米', lambda m,g: g.add_node(type="Length", value=_to_number(m.group(1)))),  # 可选
# ]
# 1. Length 扩充：走了 X 米 / 从起点到终点 X 米
LENGTH_RULES = [
    r(r'长\s*(\d+(?:\.\d+)?)\s*(?:米|m)', lambda m,g: g.add_node(type="Length", value=_num(m.group(1)))),
    r(r'宽\s*(\d+(?:\.\d+)?)\s*(?:米|m)', lambda m,g: g.add_node(type="Width",  value=_num(m.group(1)))),
    r(r'周长[是为]?\s*(\d+(?:\.\d+)?)\s*(?:米|m)', lambda m,g: g.add_node(type="Length", value=_num(m.group(1)))),
    # “走了 X 米”
    r(r'走了\s*(\d+(?:\.\d+)?)\s*(?:米|m)', lambda m,g: g.add_node(type="Length", value=_num(m.group(1)))),
    # “这段路/这条路...总长/全长”
    r(r'(?:这条|这段|该|总)?(?:路|小道|跑道|城楼|绳子|队伍)(?:全长|总长|长)\s*(\d+(?:\.\d+)?)\s*(?:米|m)', 
      lambda m,g: g.add_node(type="Length", value=_num(m.group(1)))),
    # 距离 X 米
    r(r'(?:相距|距离)\s*(\d+(?:\.\d+)?)\s*(?:米|m)', lambda m,g: g.add_node(type="Length", value=_num(m.group(1)))),
]

# 2. Interval 扩充
INTERVAL_RULES = [
    r(r'(?:每隔|间隔|相隔|间距)\s*(\d+(?:\.\d+)?)\s*(?:米|m)', 
      lambda m,g: g.add_node(type="Interval", value=_num(m.group(1)))),
    r(r'(?:相邻|每两).*?(?:距离|间隔|相距)[是为]?\s*(\d+(?:\.\d+)?)\s*(?:米|m)',
      lambda m,g: g.add_node(type="Interval", value=_num(m.group(1)))),
]

# TREECNT_RULES = [
#     r(r'共(?:有|植了|栽了)?\s*(\d+)\s*棵', lambda m,g: g.add_node(type="TreeCnt", value=int(m.group(1)))),
#     r(r'(?:多少|几)\s*棵',              lambda m,g: g.add_node(type="TreeCnt")),  # 未知树数
# ]

# 3. TreeCnt 扩充
TREECNT_RULES = [
    r(r'(?:共|一共|总共|需要|安装|插|栽|种).*?\s*(\d+)\s*(?:棵|面|盏|根|盆|个|辆|只)',
      lambda m,g: g.add_node(type="TreeCnt", value=_num(m.group(1)))),
    r(r'(?:多少|几)\s*(?:棵|面|盏|根|盆|个|辆|只)',
      lambda m,g: g.add_node(type="TreeCnt")),
    # 人数相等 N 列 -> 拆分
    r(r'(\d+)\s*.*?(?:同学|人).*?(\d+)列.*?相等',
      lambda m,g: g.add_node(type="TreeCnt", value=_num(m.group(1)) // int(m.group(2)))),
]

# 4. 模式识别规则
MODE_RULES = [
    # 比较/更换间隔 (Lock)
    r(r'(原来|之前).*每隔\s*(\d+).*?(现在|改为).*每隔\s*(\d+)',
      lambda m,g: (
          g.set_pattern("tree", "both_ends_compare"),
          g.add_node(type="Interval1", value=_num(m.group(2))),
          g.add_node(type="Interval2", value=_num(m.group(4))),
          g.G.graph.__setitem__("lock_mode", True)
      )),
    
    # 闭环：明确的环形/四周/一圈
    r(r'(环形|圆形|一圈|四周|周围|围成)', lambda m,g: g.set_pattern("tree", "loop_closed")),
    
    # 两端都种（含“从起点到终点”）
    r(r'(从头到尾|从头至尾|从起点到终点|两端都|两头都|连两端|一侧栽|一边种)', 
      lambda m,g: g.set_pattern("tree", "both_ends_quantity")),
    
    # 一端不种 / 一端开始 (通常 N=Z)
    r(r'(从某一|从第1|从第一|一端开始|一头开始)', 
      lambda m,g: g.set_pattern("tree", "one_end_quantity")),
    
    # 两端都不 (含“不打结”)
    r(r'(两端|两头).*?(不栽|不种|不插|不摆|不打结|不挂)', 
      lambda m,g: g.set_pattern("tree", "none_end_quantity")),

    # 多段/车队
    r(r'(车|彩车).*?每.*长\s*(\d+).*?相隔\s*(\d+).*?共\s*(\d+)\s*辆',
      lambda m,g: (
          g.add_node(type="Length1", value=_num(m.group(2))),
          g.add_node(type="Interval1", value=_num(m.group(3))),
          g.add_node(type="TreeCnt", value=_num(m.group(4))),
          g.add_node(type="Length2", value=None),
          g.set_pattern("tree", "multi_segment")
      ))
]

RULES = LENGTH_RULES + INTERVAL_RULES + TREECNT_RULES + MODE_RULES
for rule in RULES: R.register_rule("tree", rule)

# ------------- 模式判定（注意顺序） -------------
TOPIC_MODE_RULES = [
    # Q007：同一路两种间隔比较（优先命中并“锁模式”）
    r(r'(原来|之前).*每隔\s*(\d+)\s*米.*(现在|改为).*每隔\s*(\d+)\s*米',
      lambda m,g: (
        g.set_pattern("tree", "both_ends_compare"),
        g.add_node(type="Interval1", value=int(m.group(2))),
        g.add_node(type="Interval2", value=int(m.group(4))),
        g.G.graph.__setitem__("lock_mode", True)
    )),

    # 闭环（loop）：出现 “四周/一圈/环形/周边/周围”等提示
    # 若已知 （TreeCnt 有值 + Interval 有值） → 多为问“周长多少米” → 设 loop_closed_distance
    # 否则设 loop_closed（多为已知L, I，求Z）
    r(r'(四周|一圈|环形|围成一圈|围成一周|沿着.*周边|沿.*周围|正方形.*周长|周长.*求)',
      lambda m,g: (
        g.set_pattern("tree", "loop_closed_distance")
        if (g.has_node(type="TreeCnt", value=True) and g.has_node(type="Interval", value=True))
        else g.set_pattern("tree", "loop_closed")
    )),

    # 操场/四边 + 角都种（矩形闭合）
    r(r'(操场|四边).*角.*种(?:树)?', lambda m,g: g.set_pattern("tree", "rectangle_closed")),

    # 多段
    r(r'(由|共)?两段.*组成', lambda m,g: g.set_pattern("tree", "multi_segment")),

    # 经典“两端植树”：按是否已知 TreeCnt 判别是求长度还是求树数
    r(r'两端.*植树',
      lambda m,g: (g.set_pattern("tree", "both_ends_distance")
                   if g.has_node(type="TreeCnt", value=True)
                   else g.set_pattern("tree", "both_ends_quantity"))),

    # 一端开始，另一端不种
    r(r'.*一端(开始).*一端不种', lambda m,g: g.set_pattern("tree", "one_end_quantity")),

    # 两端都不种
    r(r'两端.*不植(?:树)?|不在两端', lambda m,g: g.set_pattern("tree", "none_end_quantity")),
]

# ------------- 多段文本里的数值抽取（可选留用） -------------
MULTI_SEG_RULES = [
    r(r'第一段\s*(\d+)\s*米.*每隔\s*(\d+)\s*米',
      lambda m,g: (g.add_node(type="Length", value=int(m.group(1))),
                   g.add_node(type="Interval", value=int(m.group(2))))),
    r(r'第二段\s*(\d+)\s*米.*每隔\s*(\d+)\s*米',
      lambda m,g: (g.add_node(type="Length", value=int(m.group(1))),
                   g.add_node(type="Interval", value=int(m.group(2))))),
    # 少/相差 → 用 Diff 作为未知量
    r(r'(少种了|少了|相差|差了|少种).*几棵', lambda m,g: g.add_node(type="Diff")),
]

# ------------- 汇总（顺序很重要：先节点，后模式） -------------
RULES = []
RULES += LENGTH_RULES
RULES += TREECNT_RULES
RULES += [INTERVAL_RULE]
RULES += TOPIC_MODE_RULES
RULES += MULTI_SEG_RULES


def _num(s):
    try:
        v = float(s)
        return int(v) if abs(v - int(v)) < 1e-12 else v
    except Exception:
        return None

# 定义一组强烈的“植树”关键词，用于在 Trip 路由中进行排除/降权
TREE_STRONG_KEYWORDS = re.compile(r"(栽|种|植|每隔|间隔|树苗|杨树|柳树)", re.I)

# ==== Phase-1：路由 (修改版) ====

# 1. 相遇/相向 (Join)
register_route("trip", (
    r"(相向|迎面|相对).*?(行|驶|走|跑)|相遇",
    lambda m, g: (
        # 【增强排除】：如果包含植树关键词，大概率是“环形植树反向走”的题，不应单纯视为 Trip
        None if TREE_STRONG_KEYWORDS.search(g.G.graph.get("raw_text", ""))
        else g.add_candidate("trip", "join", confidence=0.9, source="kw")
    )
))

# 2. 追及 (Chase)
register_route("trip", (
    r"(同向|追及|追上|赶上)",
    lambda m, g: (
        None if TREE_STRONG_KEYWORDS.search(g.G.graph.get("raw_text", ""))
        else g.add_candidate("trip", "chase", confidence=0.9, source="kw")
    )
))

# 3. 速度单位 (这是硬指标，通常不会误判，保持信心)
register_route("trip", (
    r"(\d+(?:\.\d+)?)\s*(km/h|千?米/小时|m/s|米/秒)|速度",
    lambda m, g: g.add_candidate("trip", g.G.graph.get("mode") or None, confidence=0.7, source="unit")
))

# 4. 距离 (Dist) - 这是一个弱特征，很容易撞车，需要降权或排除
register_route("trip", (
    r"(相距|距离).*(千?米|公里|km|米|m)",
    lambda m, g: (
        # 如果有“每隔”等词，这通常是植树的“间隔”或“全长”，而不是行程的“两地距离”
        None if TREE_STRONG_KEYWORDS.search(g.G.graph.get("raw_text", ""))
        else g.add_candidate("trip", g.G.graph.get("mode") or None, confidence=0.5, source="dist")
    )
))

# 5. 时间差 (DeltaT)
register_route("trip", (
    r"(先|后).*?出发.*?(\d+(?:\.\d+)?)\s*(小时|h|分钟|min|秒|s).*?(后)?",
    lambda m,g: g.add_candidate("trip", "join", confidence=0.95, source="delta_t")
))


# ---------- Length / 周长 ----------
# R.register_rule("tree", (re.compile(
#     r'(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)的[^，。；]*?(?:环形|圆形)?[^，。；]*?(?:跑道|湖|水池|花园|道路|公路|操场|广场|花坛|围栏|栅栏)',
#     FLAGS),
#     lambda m, g: g.add_node(type="Length", value=_num(m.group(1)))
# ))
# 修改为（新增：小道|步道|人行道|甬道|校道 等等）：
R.register_rule("tree", (re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)的[^，。；]*?(?:环形|圆形)?[^，。；]*?'
    r'(?:跑道|湖|水池|花园|道路|公路|操场|广场|花坛|围栏|栅栏|小道|步道|人行道|甬道|校道)',
    FLAGS),
    lambda m, g: g.add_node(type="Length", value=_num(m.group(1)))
))
R.register_rule("tree", (re.compile(
    r'(?:周长|全长|长度)[是为]?\s*(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)', FLAGS),
    lambda m, g: g.add_node(type="Length", value=_num(m.group(1)))
))
# “两…之间相隔/相距/距离 X 米” → 更像总长（直线）
R.register_rule("tree", (re.compile(
    r'(?:两|俩|首尾|两端|两头|甲乙|东西|东|西|南|北|前后)[^，。；]{0,8}?(?:之间|相隔|相距|距离)[是为]?\s*(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)',
    FLAGS),
    lambda m, g: g.add_node(type="Length", value=_num(m.group(1)))
))
# 反向/相向而行，相遇 -> 周长 = 两人路程和
R.register_rule("tree", (re.compile(
    r'(?:甲|A)[^，。；]*?走了\s*(\d+(?:\.\d+)?)\s*(?:米|m)'
    r'[^。；]*?(?:乙|B)[^，。；]*?走了\s*(\d+(?:\.\d+)?)\s*(?:米|m)'
    r'[^。；]*?(?:相遇|相向而行|反向而行)', FLAGS),
    lambda m, g: (
        # 若已有 Length 节点，强制更新其值；否则新建
        (g.G.nodes[g.last_of("Length")]["value"].__setitem__(slice(None), None),)  # 无操作占位
        if False else None,  # 仅为占位，下面真的更新
        (g.G.nodes.__setitem__(g.last_of("Length"), g.G.nodes[g.last_of("Length")])
         if g.last_of("Length") else None),
        (g.G.nodes[g.last_of("Length")].__setitem__("value",
            _num(m.group(1)) + _num(m.group(2)))) if g.last_of("Length")
        else g.add_node(type="Length", value=_num(m.group(1)) + _num(m.group(2))),
        g.set_pattern("tree", "loop_closed")  # 统一走闭环模板
    )
))
# === 补充“长度/周长”抽取的名词覆盖 ===
R.register_rule("tree", (
    re.compile(
        r'(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)的[^，。；]*?(?:环形|圆形)?[^，。；]*?'
        r'(?:跑道|湖|水池|花园|道路|公路|操场|广场|花坛|围栏|栅栏|小道|步道|人行道|甬道|校道)',
        re.I
    ),
    lambda m, g: (
        # 若已有 Length 则保留较“长”的那个；没有则新建（你也可以改为直接覆盖）
        (lambda val: (
            g.G.nodes[g.last_of("Length")].update({"value": val})
            if g.last_of("Length") else g.add_node(type="Length", value=val)
        ))(_num(m.group(1)))
    )
))
# # 闭环相向/反向相遇：周长 = 两人走的距离和
# R.register_rule("tree", (
#     re.compile(
#         r'(?:甲|A)[^。；\n]*?走了\s*(\d+(?:\.\d+)?)\s*(?:米|m)[^。；\n]*?'
#         r'(?:乙|B)[^。；\n]*?走了\s*(\d+(?:\.\d+)?)\s*(?:米|m)[^。；\n]*?(?:相遇|反向而行|相向而行)', re.I),
#     lambda m, g: (
#         g.add_node(type="Length", value=(float(m.group(1))+float(m.group(2)))),
#         g.set_pattern("tree", "loop_closed")
#     )
# ))

# === A. 大类：闭环（周围/一圈/环形/圆形/周长/沿…一周）→ loop_closed ===
R.register_rule("tree", (
    re.compile(r'(周围|四周|一圈|沿[^。；]*?一周|环形|圆形|周长)', re.I),
    lambda m, g: g.set_pattern("tree", "loop_closed")
))
# 矩形围一圈（四角、四周）→ 周长 = 2*(长+宽)
R.register_rule("tree", (
    re.compile(r'(?:四个角|四角|四周|一圈)[^。；\n]*?(?:摆|栽|插)', re.I),
    lambda m, g: (
        (lambda L, W: (
            g.add_node(type="Length", value=2*(L+W)),
            g.set_pattern("tree", "loop_closed")
        ))(
            g.G.nodes.get(g.last_of("Length"),{}).get("value",0) or 0,
            g.G.nodes.get(g.last_of("Width"),{}).get("value",0)  or 0
        ) if g.last_of("Length") and g.last_of("Width") else None
    )
))

# === B. 大类：直线一侧、“从头到尾/从一头开始/两端都栽/一侧栽树” → both_ends_quantity ===
# # 两端都不… → MINUS1（放在“都栽”之前，确保优先）
# R.register_rule("tree", (
#     re.compile(r'(两端|两头).*?(都不栽|都不种|都不安装|都不放置|都不打结|都不挂)', re.I),
#     lambda m, g: g.G.graph.__setitem__("end_op", "MINUS1")
# ))
# # 两端都… → PLUS1
# R.register_rule("tree", (
#     re.compile(r'(两端|两头).*(都栽|都种|都安装|都放置|都打结|都挂)', re.I),
#     lambda m, g: g.G.graph.__setitem__("end_op", "PLUS1")
# ))

R.register_rule("tree", (
    re.compile(r'(从头至尾|从头到尾|从一头开始|两端都栽|两头都栽|路的一侧|道路一侧|一侧栽|在.*一边.*栽)', re.I),
    lambda m, g: g.set_pattern("tree", "both_ends_quantity")
))

# === C. 兜底：只要出现“栽/种/插 + 树/旗/垃圾桶/路灯”等对象，就把 topic 立起来 ===
R.register_rule("tree", (
    re.compile(r'(栽|种|插)[^。；]*?(树|柳树|杨树|旗|红旗|垃圾桶|路灯)', re.I),
    lambda m, g: (g.G.graph.get("topic") or g.G.graph.__setitem__("topic","tree"))
))
# === 只要出现“相隔/每隔/间隔/相距/距离 X 米”，就抽 Interval=X
# 同时若此前误把同一个数值抽成了 Length，则把该 Length 的 value 清空（避免 Length=8 的误判）
R.register_rule("tree", (
    re.compile(r'(?:每隔|相隔|间隔|相距|距离)\s*(\d+(?:\.\d+)?)\s*(?:米|m)', re.I),
    lambda m, g: (
        # 1) 抽取间隔
        g.add_node(type="Interval", value=_num(m.group(1))),
        # 2) 若存在最近的 Length 且其值恰好等于该间隔，视作误判 -> 清空
        (g.G.nodes[g.last_of("Length")].__setitem__("value", None)
            if g.last_of("Length") and g.G.nodes[g.last_of("Length")].get("value") == _num(m.group(1))
            else None)
    )
))
# === “共/一共/总共 … 栽/种/插 … X 棵（树/柳树/杨树/树苗）” -> TreeCnt = X
R.register_rule("tree", (
    re.compile(
        r'(?:共|一共|总共)?[^。；\n]*?(?:栽|种|插)[^。；\n]*?(\d+)\s*棵'
        r'[^。；\n]*?(?:树|柳树|杨树|树苗)?',  # 名词可省略
        re.I
    ),
    lambda m, g: (
        # 若已有 TreeCnt 且为 None/未赋值，则覆盖；若不存在则新建
        (g.G.nodes[g.last_of("TreeCnt")].__setitem__("value", _num(m.group(1)))
            if g.last_of("TreeCnt") and g.G.nodes[g.last_of("TreeCnt")].get("value") in (None, )
            else g.add_node(type="TreeCnt", value=_num(m.group(1))))
    )
))

# ---------- TreeCnt / 多少棵（更广量词与动词） ----------
_OBJ = r'(?:棵|面|盏|个|根|只|株|辆|位|人|块|次|盆|支|杆)'
R.register_rule("tree", (re.compile(
    r'(?:连两端|连两头)?(?:共(?:有|计|用|装|插|放|栽)|一共|合计|共有|准备|需要|用了|共放|共插|共装|共立|共栽|共摆)[^0-9]{0,4}(\d+)\s*' + _OBJ,
    FLAGS),
    lambda m, g: g.add_node(type="TreeCnt", value=int(m.group(1)))
))
R.register_rule("tree", (re.compile(
    r'(?:栽|插|放|挂|立|装|摆|安装|准备|需要)[^0-9]{0,3}(\d+)\s*' + _OBJ,
    FLAGS),
    lambda m, g: g.add_node(type="TreeCnt", value=int(m.group(1)))
))
# 问句型未知树数
R.register_rule("tree", (re.compile(
    r'(?:多少|几)\s*' + _OBJ, FLAGS),
    lambda m, g: g.add_node(type="TreeCnt")
))
# # 人/同学/小朋友数量（避免“每隔…1个”误匹配）
# R.register_rule("tree", (
#     re.compile(r'(\d+)\s*(?:位|个)\s*(?:小朋友|同学|人)\b(?![^。；\n]*?每隔)', re.I),
#     lambda m, g: (
#         g.add_node(type="TreeCnt", value=int(m.group(1)))
#         if not g.last_of("TreeCnt")
#         else g.G.nodes[g.last_of("TreeCnt")].__setitem__("value", int(m.group(1)))
#     )
# ))
# 人数相等的N列 → 把 TreeCnt 均分到单列
R.register_rule("tree", (
    re.compile(r'(\d+)\s*(?:位|个)\s*(?:小朋友|同学|人)[^。；\n]*?(?:两|三|四|五|六|七|八|九|十|(\d+))列[^。；\n]*?(?:人数相等|相等)', re.I),
    lambda m, g: (
        (lambda total, cols:
            g.add_node(type="TreeCnt", value= total // cols)
            if not g.last_of("TreeCnt")
            else g.G.nodes[g.last_of("TreeCnt")].__setitem__("value", total // cols)
        )(int(re.search(r'\d+', m.group(0)).group()),  # 总人数
          ({"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}.get(m.group(1), int(m.group(2) or 1))))
    )
))

# ---------- Interval / 间隔 ----------
# 典型“每隔/间隔/相隔 X 米”
R.register_rule("tree", (re.compile(
    r'(?:每隔|间隔|相隔)\s*(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)', FLAGS),
    lambda m, g: g.add_node(type="Interval", value=_num(m.group(1)))
))
# “每…相距/间距…米”
R.register_rule("tree", (re.compile(
    r'每[^，。；]*?(?:相距|相隔|间距)[是为]?\s*(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)', FLAGS),
    lambda m, g: g.add_node(type="Interval", value=_num(m.group(1)))
))
# “相邻/每两…之间…距离/间隔/相距 X 米”（相邻点间隔）
R.register_rule("tree", (re.compile(
    r'(?:相邻|每两(?:个|棵|面|盏|根)|两(?:个|棵|面|盏|根)[^，。；]*?之间)[^，。；]*?(?:距离|间隔|相距)[是为]?\s*(\d+(?:\.\d+)?)\s*(?:米|m|千米|km)',
    FLAGS),
    lambda m, g: g.add_node(type="Interval", value=_num(m.group(1)))
))

# ---------- 类植树题场景 ----------
_num = lambda s: float(s) if '.' in s else int(s)

# === A. 通用“数量”抽取：小朋友/同学/车辆/灯/旗/垃圾桶…… -> TreeCnt ===
R.register_rule("tree", (
    re.compile(
        r'(?:共|一共|总共)?[^。；\n]*?(?:有|栽|种|插|站|排|安装|放置|设置|排列)'
        r'[^。；\n]*?(\d+)\s*(?:棵|位|个|辆|盏|面)'
        r'(?:[^。；\n]*?(?:树|柳树|杨树|树苗|小朋友|同学|车|车辆|灯|路灯|垃圾桶|红旗|旗))?',
        re.I),
    lambda m, g: (
        g.add_node(type="TreeCnt", value=_num(m.group(1)))
        if not g.last_of("TreeCnt")
        else g.G.nodes[g.last_of("TreeCnt")].__setitem__("value", _num(m.group(1)))
    )
))

# === B. 直线一侧/队伍/排队 -> both_ends_quantity（让 hook 自动挂 PLUS1） ===
R.register_rule("tree", (
    re.compile(
        r'(站成一列|排成一排|队伍|车队|从头至尾|从头到尾|从一头开始|路的一侧|道路一侧|一侧栽|在.*一边.*栽)',
        re.I),
    lambda m, g: g.set_pattern("tree", "both_ends_quantity")
))

# === C. “平均每隔多少米 / 每隔几米” -> 创建未知 Interval 节点 ===
R.register_rule("tree", (
    re.compile(r'(平均)?每隔\s*(?:多少|几)\s*(?:米|m)?', re.I),
    lambda m, g: (
        g.add_node(type="Interval", value=None)
        if not g.last_of("Interval") else None
    )
))

# === D. 两侧对比：原打算…Z1棵…每隔I1米；实际…Z2棵；问新间距 I2 ===
# 公式：L 固定 -> (Z1-1)*I1 = (Z2-1)*I2
R.register_rule("tree", (
    re.compile(
        r'(?:两侧|两边)[^。；\n]*?(?:原打算|原计划)[^。；\n]*?(\d+)\s*棵'
        r'[^。；\n]*?每隔\s*(\d+(?:\.\d+)?)\s*(?:米|m)'
        r'[^。；\n]*?(?:实际|后来|现在)[^。；\n]*?(\d+)\s*棵',
        re.I),
    lambda m, g: (
        g.add_node(type="TreeCnt", value=_num(m.group(1))),  # Z1
        g.add_node(type="Interval", value=_num(m.group(2))), # I1
        g.add_node(type="TreeCnt", value=_num(m.group(3))),  # Z2
        g.add_node(type="Interval", value=None),             # I2 (未知)
        g.set_pattern("tree", "both_ends_compare")
    )
))

# === E. 多段车队：每辆车长 a、前后相隔 b、共 Z 辆 -> 设 multi_segment，创建 L1/I1/Z，L2未知 ===
R.register_rule("tree", (
    re.compile(
        r'(?:车|车辆|彩车|卡车|汽车)[^。；\n]*?(?:每辆|每台|每车)[^。；\n]*?长\s*'
        r'(\d+(?:\.\d+)?)\s*(?:米|m)[^。；\n]*?(?:相隔|间隔|间距)\s*'
        r'(\d+(?:\.\d+)?)\s*(?:米|m)[^。；\n]*?(?:共|一共|总共)\s*'
        r'(\d+)\s*(?:辆)',
        re.I),
    lambda m, g: (
        g.add_node(type="Length1", value=_num(m.group(1))),   # 车长
        g.add_node(type="Interval1", value=_num(m.group(2))), # 车距
        g.add_node(type="TreeCnt", value=_num(m.group(3))),   # 车辆数
        g.add_node(type="Length2", value=None),               # 队伍总长
        g.set_pattern("tree", "multi_segment")
    )
))
# # 直线强提示 → 归类 linear
# R.register_rule("tree", (
#     re.compile(r'(从第[一1].*到最后[一1].*距离|路的一侧|沿.*一侧|连两端)', re.I),
#     lambda m, g: g.set_pattern("tree", "linear")
# ))


for rule in RULES: R.register_rule("tree", rule)


def _try_promote_to_multi_segment(g):
    G = g.G
    if G.graph.get("lock_mode"):   # 有锁直接不升级
        return
    mode = G.graph.get("mode","")
    if mode == "both_ends_compare":  # compare 不参与升级
        return

    # 仅当真的是“原生多段”才升级：至少 2 个原生 Length 或 2 个原生 Interval
    n_len = sum(1 for _,d in G.nodes(data=True) if d.get("type") == "Length")
    n_int = sum(1 for _,d in G.nodes(data=True) if d.get("type") == "Interval")
    if (n_len >= 2 or n_int >= 2) and mode in {"both_ends_quantity","both_ends_distance","one_end_quantity"}:
        G.graph["mode"] = "multi_segment"
        # 清理误连的 tree_relation
        to_remove = [(u,v) for u,v,d in G.edges(data=True) if d.get("type")=="tree_relation"]
        for u,v in to_remove: G.remove_edge(u,v)
        print("[hook] 检测到多段，覆盖模式为 multi_segment，并移除误连 tree_relation")

def _patch_rectangle_closed(g):
    """矩形围场：Length/Width → Length1/Length2；补 L2–Interval 的 divides（模板已不要求 N1/N2）。"""
    G = g.G
    # 1) 重命名
    lengths = [nid for nid, d in G.nodes(data=True) if d["type"] == "Length"]
    widths  = [nid for nid, d in G.nodes(data=True) if d["type"] == "Width"]

    # 取一个 Length 作为 Length1
    if lengths:
        G.nodes[lengths[0]]["type"] = "Length1"
        # 若还有多余的 Length，用于 Length2（防止没有 Width 的文本）
        if len(lengths) >= 2 and not any(d["type"] == "Length2" for _, d in G.nodes(data=True)):
            G.nodes[lengths[1]]["type"] = "Length2"
            print("[hook] rectangle_closed: Length → Length1, Length2 赋值")
    # 否则用 Width 作为 Length2
    if not any(d["type"] == "Length2" for _, d in G.nodes(data=True)) and widths:
        w = widths[0]
        G.nodes[w]["type"] = "Length2"
        print(f"[hook] rectangle_closed: Width → Length2 ({w})")

    # 2) 补 L2 – Interval divides
    l2 = next((nid for nid, d in G.nodes(data=True) if d["type"] == "Length2"), None)
    I  = next((nid for nid, d in G.nodes(data=True) if d["type"] == "Interval"), None)
    if l2 and I:
        has_div = any(
            d.get("type") == "divides" and ((u == l2 and v == I) or (u == I and v == l2))
            for u, v, d in G.edges(data=True)
        )
        if not has_div:
            g.add_edge(l2, I, type="divides", op=None)
            print("[hook] rectangle_closed: 添加 Length2 - Interval divides")


def _patch_multi_segment(g):
    """多段连接：Length/Interval 标号成 1/2；补成对 divides：L1–I1、L2–I2。"""
    G = g.G
    # 1) 标号
    lens = [nid for nid, d in G.nodes(data=True) if d["type"] == "Length"]
    ints = [nid for nid, d in G.nodes(data=True) if d["type"] == "Interval"]

    for i, nid in enumerate(lens[:2]):
        G.nodes[nid]["type"] = f"Length{i+1}"
    for i, nid in enumerate(ints[:2]):
        G.nodes[nid]["type"] = f"Interval{i+1}"
    print("[hook] multi_segment: Length/Interval 分段重命名完成")

    # 2) 成对 divides
    def last_of(t):
        return next((nid for nid, d in G.nodes(data=True) if d["type"] == t), None)

    for k in (1, 2):
        Lk = last_of(f"Length{k}")
        Ik = last_of(f"Interval{k}")
        if Lk and Ik:
            has_div = any(
                d.get("type") == "divides" and ((u == Lk and v == Ik) or (u == Ik and v == Lk))
                for u, v, d in G.edges(data=True)
            )
            if not has_div:
                g.add_edge(Lk, Ik, type="divides", op=None)
                print(f"[hook] multi_segment: 添加 divides (Length{k}, Interval{k})")

def _patch_both_ends_compare(g):
    G = g.G

    # A) 清理裸 Interval（避免被其它模板误匹配）
    rm = [nid for nid,d in G.nodes(data=True) if d.get("type") == "Interval"]
    for nid in rm:
        G.remove_node(nid)

    # B) 对 Interval1/2 去重（同 value 合并）
    def _dedup(tname):
        seen = {}
        to_remove = []
        for nid,d in list(G.nodes(data=True)):
            if d.get("type") != tname: continue
            k = (tname, d.get("value"))
            if k in seen:
                keep = seen[k]
                # 合并边
                for u,v,data in list(G.edges(nid, data=True)):
                    other = v if u == nid else u
                    if not G.has_edge(keep, other):
                        G.add_edge(keep, other, **{k:v for k,v in data.items()})
                    G.remove_edge(u,v)
                to_remove.append(nid)
            else:
                seen[k] = nid
        for nid in to_remove:
            G.remove_node(nid)

    _dedup("Interval1")
    _dedup("Interval2")

    # C) 确保 Y–X1 / Y–X2 divides 都在
    Y  = g.last_of("Length")
    X1 = g.last_of("Interval1")
    X2 = g.last_of("Interval2")

    def ensure_div(u, v):
        if not u or not v: return
        has = any(d.get("type")=="divides" and ((a==u and b==v) or (a==v and b==u))
                  for a,b,d in G.edges(data=True))
        if not has:
            g.add_edge(u, v, type="divides", op=None)

    ensure_div(Y, X1)
    ensure_div(Y, X2)
    print("[hook] both_ends_compare: 去重并补齐 Y–X1 / Y–X2 divides")


# hook：补 N 节点、关系边
def hook(g: gb.GraphBuilder):
    # 1. 只有 topic 为 tree 时才执行    
    if g.G.graph.get("topic") != "tree":
        return

    G = g.G
    mode = G.graph.get("mode", "")

    # # ① 若缺节点就补
    # if g.last_of("SegmentCnt") is None:      # N
    #     g.add_node(type="SegmentCnt")
    # if g.last_of("TreeCnt") is None:         # Z   ← 必须在加 edge 前保证存在
    #     g.add_node(type="TreeCnt")

    # # ② 把 N = Length / Interval 的结果连到 SegmentCnt
    # # 加入检查  是否已经有 Length / Interval 的关系
    # has_div = any(d["type"] == "divides" and
    #               g.G.nodes[u]["type"] == "Length" and
    #               g.G.nodes[v]["type"] == "Interval"
    #               for u, v, d in g.G.edges(data=True))
    # if (not has_div and g.last_of("Length") and g.last_of("Interval")):
    #     g.add_edge("Length", "Interval", type="divides", op=None)
    
    # 2. 补全核心节点 (N 和 Z)
    # 很多题目正则只抽到了 Length/Interval/TreeCnt，缺 SegmentCnt(N)
    # 必须在此处显式补充，否则模板无法匹配 N 节点
    if not g.has_node(type="SegmentCnt"):
        g.add_node(type="SegmentCnt")
    
    # 确保 TreeCnt 存在 (通常已有，但为了安全起见)
    if not g.has_node(type="TreeCnt"):
        g.add_node(type="TreeCnt")

    # 3. 自动连接 Length --(divides)--> Interval (如果尚未连接)
    # 只有当 L 和 I 都存在时才连
    L = g.last_of("Length")
    I = g.last_of("Interval")
    if L and I:
        has_div = any(
            d.get("type") == "divides" and 
            ((u == L and v == I) or (u == I and v == L))
            for u, v, d in G.edges(data=True)
        )
        if not has_div:
            g.add_edge(L, I, type="divides", op=None)

    # 4. 尝试升级为“多段”模式 (检测是否有多组 L/I)    
    _try_promote_to_multi_segment(g)
    
    # ③ N → Z tree_relation，用正确的 op
    # regex 先 不 画 tree_relation；统一放到 hook_tree 里，等 mode 已确定再连
    
    # 重新获取可能被升级过的 mode    
    mode = g.G.graph.get("mode", "") # 可能刚被提升，重新取一次
    
    # op_map = {
    #             "both_ends_quantity": "PLUS1",   # Z = N + 1
    #             "none_end_quantity" : "MINUS1",   # Z = N - 1
    #             "one_end_quantity"  : "EQUAL",   # Z = N
    #             "both_ends_distance": "MINUS1",   # Z = N - 1
    #             "rectangle_closed": "CUSTOM",     # 角上四次重复 → 无单一 Z-N 关系，需自定义公式
    #             "both_ends_compare": "DIFF",      # 比较两个 Z → 无段与树的单一关系
    #             "multi_segment": "MERGE",         # 多段连接去重 → 无 N→Z 边 需要合并 Z = Z1 + Z2 - 1
    #             "loop_closed": "CUSTOM",   

    #             # 新增（大多不需要自动连边 → CUSTOM）
    #             "one_end_distance": "CUSTOM",
    #             "none_end_distance": "CUSTOM",


    #             "rectangle_nocorner": "CUSTOM",
    #             "rectangle_diffI_closed": "CUSTOM",
    #             "rectangle_diffI_nocorner": "CUSTOM",


    #             "both_ends_two_sides": "CUSTOM",

    #             "multi_segment_dedup": "CUSTOM",  # 由模板公式解决 -1

    #             # 下面这两类需要自动连 N→Z
    #             "one_end_from_segments": "EQUAL",
    #             "none_end_from_segments": "MINUS1"
    #         }
    
    # 5. 建立 SegmentCnt(N) -> TreeCnt(Z) 的树形关系边 (tree_relation)
    # 不同的植树模式对应不同的 N/Z 关系 (加1、减1、相等)
    op_map = {
        # —— 经典三类 ——
        "both_ends_quantity": "PLUS1",    # Z = N + 1
        "none_end_quantity" : "MINUS1",   # Z = N - 1
        "one_end_quantity"  : "EQUAL",    # Z = N
        "both_ends_distance": "MINUS1",   # Z = N - 1  （已知Z求L，不需要自动连也可；保留兼容）
        "linear"            : "PLUS1",     # 统一直线模式的默认：Z = N + 1
        
        # —— 闭环 / 多边 / 比较：一般不自动连 N→Z —— 
        "rectangle_closed": "CUSTOM",           # 角重复、模板内有公式
        "both_ends_compare": "DIFF",            # 比较两种间隔 → 非单一 N→Z
        "multi_segment": "MERGE",               # 多段合并（模板内处理 -1）
        "loop_closed": "CUSTOM",                # 闭环：已知 L,I 求 Z（公式里给出）
        "loop_closed_distance": "CUSTOM",       # 闭环：已知 Z,I 求 L（新增）

        # —— 其他矩形变体：都在模板里给公式 —— 
        "rectangle_nocorner": "CUSTOM",
        "rectangle_diffI_closed": "CUSTOM",
        "rectangle_diffI_nocorner": "CUSTOM",

        # —— 两边/两段之类扩展：一般也不需要自动连 —— 
        "both_ends_two_sides": "CUSTOM",
        "multi_segment_dedup": "CUSTOM",

        # —— 只有“由段数反推树数”的两种，需要自动连 —— 
        "one_end_from_segments": "EQUAL",
        "none_end_from_segments": "MINUS1",

        # —— 如果你有这两类“求长度”的模式，也应 CUSTOM —— 
        "one_end_distance": "CUSTOM",
        "none_end_distance": "CUSTOM",
    }

    # 仅当图中还没有 tree_relation 边时才添加 (防止重复 Hook 导致多条边)
    has_tree_rel = any(d.get("type") == "tree_relation" for u, v, d in G.edges(data=True))

    # if not any(d["type"] == "tree_relation" for _, _, d in G.edges(data=True)):
    #     op = op_map.get(mode)

    #     if op in {"PLUS1", "MINUS1", "EQUAL"}:
    #         seg = g.last_of("SegmentCnt")
    #         tree = g.last_of("TreeCnt")
    #         if seg and tree:
    #             g.add_edge(seg, tree, type="tree_relation", op=op)
    #     else:
    #         print(f"[hook] 跳过 tree_relation 连边：当前模式 {mode} → op = {op}")

    if not has_tree_rel:
            op = op_map.get(mode)
            # 只有明确的 +1/-1/Equal 关系才连边，CUSTOM/MERGE 等交给模板公式处理
            if op in {"PLUS1", "MINUS1", "EQUAL"}:
                seg = g.last_of("SegmentCnt")
                tree = g.last_of("TreeCnt")
                if seg and tree:
                    g.add_edge(seg, tree, type="tree_relation", op=op)
                    # print(f"[Hook] Added tree_relation: {mode} -> op={op}")

    # 6. 特定模式的额外补全
    if mode == "both_ends_compare":
        _patch_both_ends_compare(g)
    elif mode == "multi_segment":
        _patch_multi_segment(g)
    elif mode == "rectangle_closed":
        _patch_rectangle_closed(g)

    # print("====last_map:", g.last_map)

# 注册 Hook (注意是元组形式)    
R.register_rule("tree", ("__AUTO__", hook))