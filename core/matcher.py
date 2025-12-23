# import networkx as nx, core.registry as R
# from networkx.algorithms.isomorphism import DiGraphMatcher
# """
# tpl_to_graph()把子图 JSON 转成实际 nx.MultiDiGraph() 供 VF2 同构匹配
# """
# def _tpl_to_graph(tpl):
#     G = nx.MultiDiGraph()
#     for n in tpl["nodes"]:
#         G.add_node(n["id"], **n)
#     for e in tpl["edges"]:
#         G.add_edge(e["u"], e["v"], **e)
#     G.graph.update(topic=tpl["topic"], mode=tpl["mode"])
#     return G

# def match(problemG):
#     topic = problemG.graph.get("topic")
#     mode  = problemG.graph.get("mode")

#     candidates = [tpl for tpl in R.SUBGRAPH_REGISTRY
#                   if tpl["topic"]==topic and tpl["mode"]==mode]

#     # nm = lambda a,b: a.get("type")==b.get("type") and a.get("op")==b.get("op")
#     nm = lambda a,b: a.get("type")==b.get("type") and a.get("op",None)==b.get("op",None)

#     # em = lambda a,b: (
#     #     a["type"] == b["type"] and
#     #     (b.get("op") is None or a.get("op")==b.get("op"))
#     #     and (b.get("optional") or True)   # b.optional==True → a 可以不存在
#     # )
#     em = nm
    
#     for tpl in candidates:
#         GM = DiGraphMatcher(problemG, _tpl_to_graph(tpl), nm, em)
#         if GM.subgraph_is_isomorphic():
#             mapping_raw = next(GM.subgraph_isomorphisms_iter())  # G_problem → G_tpl
#             mapping_inv = {tpl_id: prob_id for prob_id, tpl_id in mapping_raw.items()}
            
            
#             print(f"匹配到子图模板：{tpl['id']}，映射：{mapping_inv}")
            
#             return tpl, mapping_inv         # ←← 返回倒置后的映射
#     return None, None

# matcher.py
import copy
import networkx as nx, core.registry as R
from networkx.algorithms.isomorphism import DiGraphMatcher

import operator as _op

# 检查模板的 forbid_roles 是否在问题图里出现（出现则拒绝该模板）
def _violates_forbid_roles(problemG, tpl) -> bool:
    forb = tpl.get("forbid_roles") or []
    if not forb:
        return False
    for _, data in problemG.nodes(data=True):
        for f in forb:
            if data.get("type") == f.get("type") and data.get("role") == f.get("role"):
                return True
    return False

# 构造代入环境：把映射到的图节点数值带出来（你若有单位归一函数，可在这里调用）
def _build_env_from_mapping(problemG, tpl, mapping: dict) -> dict:
    env = {}
    for var, nid in mapping.items():
        if nid in problemG.nodes:
            env[var] = problemG.nodes[nid].get("value")
    return env

# 解析并判断一条简单守卫表达式（如 "Vf>Vs", "DT>0", "L>=0"）
_OPS = {">":_op.gt, ">=":_op.ge, "<":_op.lt, "<=":_op.le, "==":_op.eq, "!=":_op.ne}
def _eval_guard(expr: str, env: dict) -> bool:
    for sym in (">=", "<=", "==", "!=", ">", "<"):
        if sym in expr:
            left, right = expr.split(sym, 1)
            left = left.strip(); right = right.strip()
            if left not in env or env[left] is None:
                return False
            try:
                rv = float(env[right]) if right in env else float(right)
            except Exception:
                return False
            try:
                lv = float(env[left])
            except Exception:
                return False
            return _OPS[sym](lv, rv)
    return False

# --- helpers: 获取模板节点类型；对 TreeCnt 值做偏好打分 ---

def _tpl_node_type(tpl: dict, tpl_id: str) -> str | None:
    """从模板里取节点类型（通过模板节点的 id 匹配）。"""
    for n in tpl.get("nodes", []):
        if n.get("id") == tpl_id:
            return n.get("type")
    return None

def _pref_score_for_treecnt(problemG, prob_id: str) -> int:
    """
    偏好总数（>1），厌恶“每隔…1个”的 1。
    规则：
      - 如果图中存在  value>1 的 TreeCnt，而当前选择的是 value==1，则强惩罚（避免误选“每隔 1 个”）。
      - 如果当前选择的 TreeCnt 的 value>1，则小幅加分（偏好“共 N 个”这种）。
      - 否则不加不减。
    """
    node = problemG.nodes.get(prob_id, {})
    val = node.get("value", None)

    # 是否存在其它 "更像总数" 的 TreeCnt（>1）
    exist_gt1 = any(
        n.get("type") == "TreeCnt" and isinstance(n.get("value"), (int, float)) and n.get("value", 0) > 1
        for _, n in problemG.nodes(data=True)
    )

    if isinstance(val, (int, float)):
        if val == 1 and exist_gt1:
            return -2000   # 强惩罚“1 个”（通常来自“每隔…1个”）
        if val > 1:
            return +200    # 偏好“共 N 个”
    return 0

def _tpl_to_graph(tpl: dict) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    for n in tpl["nodes"]:
        G.add_node(n["id"], **n)  # id/type/...
    for e in tpl["edges"]:
        G.add_edge(e["u"], e["v"], **e)  # type/op/optional?
    G.graph.update(topic=tpl.get("topic"), mode=tpl.get("mode"))
    return G

def _tpl_variants_with_optional(tpl: dict):
    """生成模板变体：原模板 + 去掉所有 optional 边 的版本。
       如需更细粒度（任意子集），可扩展为幂集，但二合一通常足够。"""
    yield tpl
    opt = [e for e in tpl.get("edges", []) if e.get("optional")]
    if opt:
        t2 = copy.deepcopy(tpl)
        t2["edges"] = [e for e in t2["edges"] if not e.get("optional")]
        yield t2

# 新增一个打分函数
def _score_match(problemG, tpl, mapping) -> int:
    """
    评分规则：
      +1000 : 模板的 unknown 对应的问题图节点类型 == 目标量 target（gb.G.graph["target"]）
       + 50 : unknown 映射到的节点当前“无值”（确实是未知）
       -200 : unknown 映射到的节点已“有值”（说明可能选错模板）
       + 10 : 非 unknown 的节点在问题图里“有值”（上下文越完整越好）
    新增偏好：
       +200 : 当模板节点是 TreeCnt 且映射到的值 > 1（更像“总数”）
      -2000 : 当模板节点是 TreeCnt 且映射到的值 == 1，且图中存在另一个 TreeCnt>1（避免把“每隔…1个”当总数）
    """

    s = 0
    target = problemG.graph.get("target")
    unk = set(tpl.get("unknowns", []))

    # 目标量强优先
    if target:
        for u in unk:
            pid = mapping.get(u)
            if pid and problemG.nodes[pid].get("type") == target:
                s += 1000
                break

    # 未知量是否真的未知
    for u in unk:
        pid = mapping.get(u)
        val = problemG.nodes.get(pid, {}).get("value") if pid in problemG.nodes else None
        s += 50 if val is None else -200

    # 已知量覆盖度
    for n in tpl.get("nodes", []):
        if n.get("id") in unk:
            continue
        pid = mapping.get(n.get("id"))
        if pid and problemG.nodes.get(pid, {}).get("value") is not None:
            s += 10

    # —— 新增：对 TreeCnt 的“1 vs >1”偏好打分（放在最后，作为微调/否决项）——
    for tpl_id, prob_id in mapping.items():
        ttype = _tpl_node_type(tpl, tpl_id)
        if ttype == "TreeCnt":
            s += _pref_score_for_treecnt(problemG, prob_id)

    return s

def match(problemG: nx.MultiDiGraph):
    topic = problemG.graph.get("topic")
    mode  = problemG.graph.get("mode")

    candidates = [tpl for tpl in R.SUBGRAPH_REGISTRY
                  if tpl.get("topic") == topic and tpl.get("mode") == mode]

    # 节点只比较 type（节点没有 op）
    # nm = lambda a, b: a.get("type") == b.get("type")
    def nm(a, b):
        # type 必须相同；若模板节点声明了 role，则也必须匹配
        if a.get("type") != b.get("type"):
            return False
        brole = b.get("role", None)
        if brole is not None and a.get("role", None) != brole:
            return False
        return True

    # 边匹配：type 必须相等；若模板边明确给了 op，则必须相等；否则忽略 op
    def em(a, b):
        if a.get("type") != b.get("type"):
            return False
        bop = b.get("op", None)
        if bop is not None and a.get("op", None) != bop:
            return False
        return True
    
    # hits = []
    # for tpl in candidates:
    #     for tvar in _tpl_variants_with_optional(tpl):
    #         GM = DiGraphMatcher(problemG, _tpl_to_graph(tvar), node_match=nm, edge_match=em)
    #         if GM.subgraph_is_isomorphic():
    #             mapping_raw = next(GM.subgraph_isomorphisms_iter())
    #             mapping_inv = {tpl_id: prob_id for prob_id, tpl_id in mapping_raw.items()}
    #             hits.append((tvar, mapping_inv))

    hits = []
    for tpl in candidates:
        for tvar in _tpl_variants_with_optional(tpl):
            # 先看 forbid_roles（有就直接跳过）
            if _violates_forbid_roles(problemG, tvar):
                continue

            GM = DiGraphMatcher(problemG, _tpl_to_graph(tvar), node_match=nm, edge_match=em)
            if not GM.subgraph_is_isomorphic():
                continue

            # 遍历所有映射；每个映射都做一次 guards 校验，通过的才收集
            for mapping_raw in GM.subgraph_isomorphisms_iter():
                mapping_inv = {tpl_id: prob_id for prob_id, tpl_id in mapping_raw.items()}
                guards = tvar.get("guards") or []
                if guards:
                    env = _build_env_from_mapping(problemG, tvar, mapping_inv)
                    ok = True
                    for gexpr in guards:
                        if not _eval_guard(gexpr, env):
                            ok = False
                            break
                    if not ok:
                        continue  # 换下一种映射
                # 通过了（或没有 guards）→ 计入候选
                hits.append((tvar, mapping_inv))


    if not hits:
        return None, None

    best = max(hits, key=lambda hm: _score_match(problemG, hm[0], hm[1]))
    print(f"匹配到子图模板：{best[0]['id']}，映射：{best[1]}（已按 target 优选）")
    return best
    