import re, core.registry as R, core.builder as gb
"""
植树类题型（线性 + 矩形 + 向下取整 + 反推 + 改间隔 + 多段 + 同构“灯串/木板”）
"""
# —— 正则开关 —— 
FLAGS = re.S | re.I   # 跨行 & 忽略大小写
def r(regex, action): return (re.compile(regex, FLAGS), action)

# ---- 计数单位全覆盖 ----
COUNT_UNITS = r"(棵|面|盏|根|盆|旗|红旗|彩旗|灯笼|桶|垃圾桶|牌|指示牌|车|辆|名|人|个|台|支|盆花|路灯|电线杆)"
# ---- 触发“tree”主题的关键词（动词+名词）----
TREE_TRIGGERS = r"(种|栽|插|摆|挂|放|立|装|设|停靠|路灯|电线杆|彩旗|红旗|垃圾桶|指示牌|树|旗|花|盆花|灯笼)"
# ---- 圈/环/周长 ----
LOOP_TRIGGERS = r"(环形|圆形|环湖|环路|一周|周长|四周)"
# ---- 长宽矩形 ----
RECT_TRIGGERS = r"(长\s*\d+(\.\d+)?\s*米.*宽\s*\d+(\.\d+)?\s*米)"
# ---- “从头到尾/从第1到最后/连两端/两端都不/从一端开始” ----
PH_FROM_TO  = r"(从头到尾|从第[一1]到最后|连两端)"
PH_NONE_END = r"((?:两端|两头).*不(?:栽|种|插|摆)?)"
PH_BOTH_END = r"((?:两端|两头).*都(?:栽|种|插|摆))"
PH_ONE_START= r"(从(?:一|第[一1])端开始|从起点开始|从某一(盏|面|棵)开始)"

RULES = [
    r(r'长\s*(\d+)\s*米', lambda m,g: g.add_node(type="Length", value=int(m[1]))),
    r(r'宽\s*(\d+(\.\d+)?)\s*米',  lambda m,g: g.add_node(type="Width", value=float(m[1]))),    
    # r(r'(?:每隔|间隔|相隔)\s*(\d+)\s*米', lambda m,g: (g.add_node(type="Interval", value=int(m[1])))), # 改成（若已存在 Interval1/2 就跳过）
    r(r'(?:每隔|间隔|相隔)\s*(\d+)\s*米',
    lambda m,g: (
        None if any(d.get("type") in ("Interval1","Interval2") for _,d in g.G.nodes(data=True))
        else g.add_node(type="Interval", value=int(m[1]))
    )),
    
    # ----------- 求段 / 路长 ----------
    r(r'(?:多少|几)\s*段',  lambda m,g: g.add_node(type="SegmentCnt")),
    r(r'(?:多长|多少\s*米)', lambda m,g: g.add_node(type="Length")),  # 无 value 表示未知
    
    # ----------- 求树数 ----------
    r(r'共(?:有|植了)?\s*(\d+)\s*棵', lambda m,g: g.add_node(type="TreeCnt", value=int(m[1]))),  # 已知树数 求长度
    r(r'(?:多少|几)\s*棵',  lambda m,g: g.add_node(type="TreeCnt")),  # 树数未知，若已有数值型 TreeCnt，不会重复添加
    
    # 先匹配 两端.*植树，“两端不植树” 会被吃掉（.* 可以匹配 “不”），mode 被写成 both_ends，于是 op = PLUS1 → 树棵数 +1 。因此把none_end 放前面
    r(r'两端.*不植(?:树)?|不在两端', lambda m,g: g.set_pattern("tree", "none_end_quantity")),    
    r(r'.*一端(开始).*一端不种',    lambda m,g: g.set_pattern("tree", "one_end_quantity")), 
    # 已知长度求树数
    # r(r'两端.*植树', lambda m,g: g.set_pattern("tree", "both_ends_quantity")),
    

    # Q007 - 同一路两间隔比较（优先命中，阻止后续被升级为 multi_segment）
    r(r'(原来|之前).*每隔\s*(\d+)\s*米.*(现在|改为).*每隔\s*(\d+)\s*米',
    lambda m,g: (
        g.set_pattern("tree","both_ends_compare"),
        g.add_node(type="Interval1", value=int(m[2])),
        g.add_node(type="Interval2", value=int(m[4])),
        g.G.graph.__setitem__("lock_mode", True) # 锁定模式，防止后续被升级
    )),
    
    # 知树数求长度&知长度求树数，模式判断要放在TreeCnt 和 Interval 等关键数值节点提取规则之后
    r(r'两端.*植树', lambda m,g: (g.set_pattern("tree", "both_ends_distance") if g.has_node(type="TreeCnt", value=True) else g.set_pattern("tree", "both_ends_quantity"))),
    
    # Q006 - 操场四边种树
    r(r'(操场|四边).*角.*种(?:树)?', lambda m,g: g.set_pattern("tree", "rectangle_closed")),
    r(r'长\s*(\d+)\s*米[，、]?\s*宽\s*(\d+)\s*米', 
    lambda m,g: (g.add_node(type="Length", value=int(m[1])),
                g.add_node(type="Width", value=int(m[2])))),

    # 少了几棵 / 相差几棵 → 需要 Diff 作为未知量
    r(r'(少种了|少了|相差|差了|少种).*几棵', lambda m,g: g.add_node(type="Diff")),


    # Q008 - 多段连接种树
    r(r'(由|共)?两段.*组成', lambda m,g: g.set_pattern("tree", "multi_segment")),
    r(r'第一段\s*(\d+)\s*米.*每隔\s*(\d+)\s*米', 
    lambda m,g: (g.add_node(type="Length", value=int(m[1])),
                g.add_node(type="Interval", value=int(m[2])))),
    r(r'第二段\s*(\d+)\s*米.*每隔\s*(\d+)\s*米',
    lambda m,g: (g.add_node(type="Length", value=int(m[1])),
                g.add_node(type="Interval", value=int(m[2])))),
]

# 1) 长度同义：相距/距离/全长/周长
RULES += [
    r(r'(?:长|全长|长度|相距|相隔|距离)\s*(\d+(?:\.\d+)?)\s*米',
      lambda m,g: g.add_node(type="Length", value=float(m[1]) if '.' in m[1] else int(m[1]))),

    # 圆形/环形 + 周长（识别题型：闭环）
    r(r'(圆形|环形).*(周长)\s*(\d+(?:\.\d+)?)\s*米', 
      lambda m,g: (g.add_node(type="Length", value=float(m[3]) if '.' in m[3] else int(m[3])),
                   g.set_pattern("tree", "loop_closed"))),
]

# 2) 间隔同义：相邻…之间的距离/前后相邻两人间隔
RULES += [
    r(r'(?:每隔|间隔|相隔)\s*(\d+(?:\.\d+)?)\s*米',
      lambda m,g: g.add_node(type="Interval", value=float(m[1]) if '.' in m[1] else int(m[1]))),

    r(r'(?:相邻|相隔).{0,6}?(?:之间的?(?:距离|间距)?为?|为|是)\s*(\d+(?:\.\d+)?)\s*米',
      lambda m,g: g.add_node(type="Interval", value=float(m[1]) if '.' in m[1] else int(m[1]))),

    r(r'前后相邻(?:两人)?(?:之间)?(?:的)?(?:距离|间距|间隔)?(?:为|是)?\s*(\d+(?:\.\d+)?)\s*米',
      lambda m,g: g.add_node(type="Interval", value=float(m[1]) if '.' in m[1] else int(m[1]))),
]

# 3) 目标对象同义：广告牌/路灯/花盆/旗杆/盆栽… —— 询问“多少…？”
OBJECT_NOUNS = '(?:棵|盆|块|盏|根|杆|个|台|面|只)'
RULES += [
    r(r'多少\s*' + OBJECT_NOUNS, lambda m,g: g.add_node(type="TreeCnt")),  # 只增加未知“数量”节点
    r(r'一共(?:需要|安装|摆放|种|设置).*?几\s*' + OBJECT_NOUNS, lambda m,g: g.add_node(type="TreeCnt")),
]

# 4) 两端 + 不/端点管控（先 none_end，后 both_ends；已有逻辑保留，这里补充同义）
RULES += [
    r(r'(两端|两头).*(都)?不(?:植|种|设|摆)', lambda m,g: g.set_pattern("tree", "none_end_quantity")),
    r(r'(一端).*?(不种|不植)',               lambda m,g: g.set_pattern("tree", "one_end_quantity")),
    r(r'(两端|两头).*(都)?(?:植|种|设|摆)',  lambda m,g: g.set_pattern("tree", "both_ends_quantity")),
]

# 5) 两旁 / 两侧 —— 标记 two_sides 标志（在 hook 里乘2）
RULES += [
    r(r'(两旁|两侧|两边)', lambda m,g: g.G.graph.__setitem__("two_sides", True)),
]

# 6) 队列题：X 名…排成 K 列 —— 推导“每列人数”为 TreeCnt 值；接着走 both_ends_distance
def _people_per_column(m, g):
    total = int(m[1]); cols = int(m[2])
    if cols > 0 and total % cols == 0:
        per_col = total // cols
        g.add_node(type="TreeCnt", value=per_col)   # 每列“人数”→ 用 TreeCnt
        g.set_pattern("tree", "both_ends_distance")
RULES += [
    r(r'(\d+)\s*名.*?排成\s*(\d+)\s*列', _people_per_column),
    r(r'每列(队伍)?长(?:多少|多长)\s*米', lambda m,g: g.add_node(type="Length")),  # 目标未知：列长
]

# 7) 闭环题型（圆周摆放/种植）
RULES += [
    r(r'(沿|顺|围绕).*?(周长|周围).*?(?:每隔|间隔|相隔)\s*(\d+(?:\.\d+)?)\s*米',
      lambda m,g: (g.add_node(type="Interval", value=float(m[3]) if '.' in m[3] else int(m[3])),
                   g.set_pattern("tree","loop_closed"))),
]

# 8) 相邻共享（夹子/木桩/栏杆柱…）：N 段需要 N+1 个“夹子”
def _adjacent_share(m, g):
    N = int(m[1])
    g.add_node(type="SegmentCnt", value=N)           # 已知段数
    g.set_pattern("tree", "adjacent_share")
RULES += [
    r(r'(\d+)\s*(?:条|块|段).*?相邻.*?共.*?几\s*(?:个|只)?\s*(?:夹子|木桩|柱)', _adjacent_share),
]

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
    if g.G.graph.get("topic") != "tree":
        return

    G = g.G
    mode = G.graph.get("mode", "")

    # ① 若缺节点就补
    if g.last_of("SegmentCnt") is None:      # N
        g.add_node(type="SegmentCnt")
    if g.last_of("TreeCnt") is None:         # Z   ← 必须在加 edge 前保证存在
        g.add_node(type="TreeCnt")

    # ② 把 N = Length / Interval 的结果连到 SegmentCnt
    # 加入检查  是否已经有 Length / Interval 的关系
    has_div = any(d["type"] == "divides" and
                  g.G.nodes[u]["type"] == "Length" and
                  g.G.nodes[v]["type"] == "Interval"
                  for u, v, d in g.G.edges(data=True))
    if (not has_div and g.last_of("Length") and g.last_of("Interval")):
        g.add_edge("Length", "Interval", type="divides", op=None)
    
    _try_promote_to_multi_segment(g)
    
    # ③ N → Z tree_relation，用正确的 op
    # regex 先 不 画 tree_relation；统一放到 hook_tree 里，等 mode 已确定再连
    mode = g.G.graph.get("mode", "") # 可能刚被提升，重新取一次
    
    op_map = {
                "both_ends_quantity": "PLUS1",   # Z = N + 1
                "none_end_quantity" : "MINUS1",   # Z = N - 1
                "one_end_quantity"  : "EQUAL",   # Z = N
                "both_ends_distance": "MINUS1",   # Z = N - 1
                "rectangle_closed": "CUSTOM",     # 角上四次重复 → 无单一 Z-N 关系，需自定义公式
                "both_ends_compare": "DIFF",      # 比较两个 Z → 无段与树的单一关系
                "multi_segment": "MERGE",         # 多段连接去重 → 无 N→Z 边 需要合并 Z = Z1 + Z2 - 1
                "loop_closed": "CUSTOM"
            }
    
    if not any(d["type"] == "tree_relation" for _, _, d in G.edges(data=True)):
        op = op_map.get(mode)

        if op in {"PLUS1", "MINUS1", "EQUAL"}:
            seg = g.last_of("SegmentCnt")
            tree = g.last_of("TreeCnt")
            if seg and tree:
                g.add_edge(seg, tree, type="tree_relation", op=op)
        else:
            print(f"[hook] 跳过 tree_relation 连边：当前模式 {mode} → op = {op}")

    # 模式专属结构补全 按模式分发时加入
    if mode == "both_ends_compare":
        _patch_both_ends_compare(g)
    elif mode == "multi_segment":
        _patch_multi_segment(g)       # 你已有
    elif mode == "rectangle_closed":
        _patch_rectangle_closed(g)    # 你已有

    print("====last_map:", g.last_map)

    
R.register_rule("tree", ("__AUTO__", hook))