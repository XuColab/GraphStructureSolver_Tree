# explain_visualize.py
# -*- coding: utf-8 -*-
"""
Explain & visualize utilities for graph-template math solver.

This module exposes:
- explain_equation(tpl, mapping, G): produce an explanation bundle containing
  formulas, value substitution, instantiated equations and solved results.
- export_graphviz(G, mapping=None, solved=None, filename="graph.dot"): dump a DOT file.
- export_mermaid(G, mapping=None, solved=None): produce a mermaid flowchart string.

Assumptions:
- tpl: a template dict with keys: id, nodes, edges, formula, unknowns, mode (optional)
- mapping: dict of {template_node_id -> problem_graph_node_id}
- G: a networkx.DiGraph with node attributes: {"type": str, "value": (int/float/None)}
       and edge attributes: {"type": str, "op": Optional[str]}
"""

from sympy import symbols, Eq, sympify, solve, nsimplify
from copy import deepcopy
from html import escape

COUNT_TYPES = {"TreeCnt", "SegmentCnt", "Diff"}


def explain_equation(tpl: dict, mapping: dict, G) -> dict:
    """
    Build an explanation bundle:
    {
      "template_id": str,
      "mode": str | None,
      "nodes": [(node_id, {type, value, ...}), ...],
      "edges": [(u, v, {type, op, ...}), ...],
      "formulas": [str, ...],             # original formulas from template
      "given": {template_symbol: value},  # numeric values substituted
      "instantiated": [str, ...],         # equations after substitution
      "unknowns": [str, ...],
      "solved": {symbol_name: value},     # post-processed (intified for counts)
      "mapping": {tpl_id: prob_id},
      "notes": [str, ...]
    }
    """
    # ---- 0) normalize mapping direction if needed ----
    tpl_ids = {n["id"] for n in tpl["nodes"]}
    if not (set(mapping.keys()) & tpl_ids):
        # mapping is reversed -> flip to tpl_id -> prob_id
        mapping = {tpl_id: prob_id for prob_id, tpl_id in mapping.items()}

    # ---- 1) symbols / node type map ----
    symtab = {n["id"]: symbols(n["id"]) for n in tpl["nodes"]}
    node_type_map = {n["id"]: n["type"] for n in tpl["nodes"]}

    # ---- 2) collect known values (coerce 20.0 -> 20 when integral) ----
    def _coerce_num(val):
        if isinstance(val, float) and float(val).is_integer():
            return int(val)
        return val

    given = {}
    for tpl_id, prob_id in mapping.items():
        if prob_id in G.nodes and G.nodes[prob_id].get("value") is not None and tpl_id in symtab:
            given[symtab[tpl_id]] = _coerce_num(G.nodes[prob_id]["value"])

    # ---- 3) build equations ----
    eqs_raw = [Eq(*[sympify(side.strip(), locals=symtab) for side in f.split("=")]) for f in tpl["formula"]]
    eqs_sub = [e.subs(given) for e in eqs_raw]

    # ---- 4) solve unknowns ----
    unknown_syms = [symtab[uid] for uid in tpl["unknowns"]]
    solved_list = solve(eqs_sub, unknown_syms, dict=True)
    solved = solved_list[0] if solved_list else {}

    # ---- 5) post-process results (intify for count-like types) ----
    def _intify_if_count(tpl_sym_name: str, val):
        t = node_type_map.get(tpl_sym_name)
        if t in COUNT_TYPES:
            try:
                v_simpl = nsimplify(val, rational=True)
                if getattr(v_simpl, "is_integer", False):
                    return int(v_simpl)
                return int(round(float(v_simpl)))
            except Exception:
                try:
                    return int(round(float(val)))
                except Exception:
                    return val
        return val

    solved_int = {str(k): _intify_if_count(str(k), v) for k, v in solved.items()}

    # ---- 6) assemble package ----
    pkg = {
        "template_id": tpl.get("id"),
        "mode": G.graph.get("mode"),
        "nodes": [(nid, deepcopy(G.nodes[nid])) for nid in G.nodes()],
        "edges": [(u, v, deepcopy(d)) for u, v, d in G.edges(data=True)],
        "formulas": tpl["formula"],
        "given": {str(k): v for k, v in given.items()},
        "instantiated": [str(e) for e in eqs_sub],
        "unknowns": tpl["unknowns"],
        "solved": solved_int,
        "mapping": mapping,
        "notes": [],
    }

    # notes: tree_relation presence, and integerization notice
    if any(d.get("type") == "tree_relation" for _, _, d in G.edges(data=True)):
        for u, v, d in G.edges(data=True):
            if d.get("type") == "tree_relation":
                pkg["notes"].append(
                    f"树关系：{G.nodes[u]['type']} → {G.nodes[v]['type']}，op={d.get('op')}（如 Z=N±1）。"
                )
                break
    if any(node_type_map.get(u) in COUNT_TYPES for u in tpl["unknowns"]):
        pkg["notes"].append("结果为计数型（棵树/段数/差值），已做整数化处理。")

    return pkg


def export_graphviz(G, mapping=None, solved=None, filename: str = "graph.dot") -> str:
    """
    Dump a Graphviz DOT file describing the current problem graph.
    - Known nodes: light blue fill
    - Solved (mapped unknowns) nodes: light green fill
    - divides edge: solid gray
    - tree_relation edge: dashed orange with op label
    """
    solved_nodes = set()
    if mapping and solved:
        for tpl_id, _ in solved.items():
            pid = mapping.get(tpl_id)
            if pid:
                solved_nodes.add(pid)

    lines = [
        "digraph G {",
        'rankdir=LR;',
        'fontname="Arial";',
        'node [shape=box, fontname="Arial"];',
    ]

    def node_stmt(nid, data):
        t = data.get("type")
        val = data.get("value")
        label = f"{escape(t)}\\n{escape(nid)}"
        if val is not None:
            label += f"\\nvalue={escape(str(val))}"
        fill = "#FFFFFF"
        if val is not None:
            fill = "#E7F3FF"  # known
        if nid in solved_nodes:
            fill = "#E6FFEA"  # solved
        color = "#3366CC" if (mapping and nid in mapping.values()) else "#999999"
        return f'"{nid}" [label="{label}", style="rounded,filled", fillcolor="{fill}", color="{color}"];'

    for nid, data in G.nodes(data=True):
        lines.append(node_stmt(nid, data))

    for u, v, d in G.edges(data=True):
        et = d.get("type")
        color = "#666666"
        style = "solid"
        label = et
        if et == "tree_relation":
            color = "#FF8800"
            style = "dashed"
            label = f'{et}\\n{d.get("op")}'
        lines.append(f'"{u}" -> "{v}" [label="{label}", color="{color}", style="{style}"];')

    # legend
    lines += [
        'subgraph cluster_legend {label="Legend"; style=dashed; color="#BBBBBB";',
        '"K" [label="Known node", style="rounded,filled", fillcolor="#E7F3FF"];',
        '"S" [label="Solved node", style="rounded,filled", fillcolor="#E6FFEA"];',
        '"TR" [label="tree_relation: PLUS1/MINUS1/EQUAL", shape=plaintext];',
        '"DV" [label="divides: Length → Interval", shape=plaintext];',
        "}",
        "}",
    ]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filename  # run: dot -Tpng graph.dot -o graph.png


def export_mermaid(G, mapping=None, solved=None) -> str:
    """
    Produce a Mermaid flowchart string for lightweight embedding.
    """
    solved_nodes = set()
    if mapping and solved:
        for tpl_id, _ in solved.items():
            pid = mapping.get(tpl_id)
            if pid:
                solved_nodes.add(pid)

    def lbl(nid, d):
        t = d.get("type")
        val = d.get("value")
        s = f"{t}<br/>{nid}"
        if val is not None:
            s += f"<br/>value={val}"
        return s

    lines = [
        "flowchart LR",
        "classDef known fill:#E7F3FF,stroke:#3366CC,color:#000;",
        "classDef solved fill:#E6FFEA,stroke:#2f855a,color:#000;",
        "classDef unknown fill:#FFFFFF,stroke:#999,color:#000;",
    ]

    for nid, d in G.nodes(data=True):
        label = lbl(nid, d)
        if nid in solved_nodes:
            style = ":::solved"
        else:
            style = ":::known" if d.get("value") is not None else ":::unknown"
        lines.append(f'{nid}["{label}"]{style}')

    for u, v, d in G.edges(data=True):
        et = d.get("type")
        text = et if et != "tree_relation" else f'{et} {d.get("op")}'
        lines.append(f"{u} -->|{text}| {v}")

    return "\n".join(lines)

# 追加到 explain_visualize.py 末尾或任意位置
import re

def export_mermaid_cn(G, mapping=None, solved=None, *, show_ids=False) -> str:
    """
    中文友好版 Mermaid：
    - 节点标签：中文名称 + 数值 + 单位（隐藏内部 id）
    - 已知量：浅蓝；已解出：浅绿；未知：白
    - 边：divides 显示“÷”；tree_relation 显示 Z=N±1 或 “相等”
    - show_ids=True 可在标签下方追加内部id（调试用）
    """

    # 已解出的“题图节点 id”集合
    solved_nodes = set()
    solved_vals = {}
    if mapping and solved:
        for tpl_id, val in solved.items():
            pid = mapping.get(tpl_id)
            if pid:
                solved_nodes.add(pid)
                solved_vals[pid] = val

    # 显示名 & 单位（可按需再细化）
    def ordinal(name):
        # 把 Length1/Interval2 里的数字解析成“第一段/第二段”
        m = re.match(r"([A-Za-z]+)(\d+)$", name or "")
        if not m: return None
        idx = int(m.group(2))
        return ["零","一","二","三","四","五","六","七","八","九","十"][idx] if idx<11 else f"{idx}"

    def cn_name(ntype: str) -> str:
        # 基础中文名称
        base = {
            "Length": "长度",
            "Interval": "间隔",
            "TreeCnt": "树棵数",
            "SegmentCnt": "段数",
            "Diff": "少种棵数",
        }
        # 编号类型（Length1/2、Interval1/2）
        m = re.match(r"^(Length|Interval)(\d+)$", ntype)
        if m:
            kind, num = m.group(1), int(m.group(2))
            ord_cn = ["零","一","二","三","四","五","六","七","八","九","十"][num] if num < 11 else str(num)
            return f"第{ord_cn}段{'长度' if kind=='Length' else '间隔'}"
        return base.get(ntype, ntype)

    def unit(ntype: str) -> str:
        if ntype.startswith("Length") or ntype.startswith("Interval"):
            return "米"
        if ntype in ("TreeCnt","Diff"):
            return "棵"
        if ntype == "SegmentCnt":
            return "段"
        return ""

    # 生成节点标签
    def node_label(nid, data):
        ntype = data.get("type")
        val = data.get("value")
        name = cn_name(ntype)
        # 若该节点是已解出的目标，用解出来的值覆盖显示
        if nid in solved_nodes:
            val = solved_vals.get(nid, val)
        # 组装显示
        if val is None:
            label = f"{name}"
        else:
            u = unit(ntype)
            label = f"{name}\\n{val} {u}".strip()
        if show_ids:
            label += f"\\n{id}"
        return label

    # 边标签
    def edge_label(d):
        et = d.get("type")
        if et == "divides":
            return "÷"
        if et == "tree_relation":
            op = d.get("op")
            return {"PLUS1":"Z=N+1","MINUS1":"Z=N-1","EQUAL":"Z=N","DIFF":"差值"}\
                   .get(op, f"tree_relation {op}")
        return et

    # Mermaid
    lines = [
        "flowchart LR",
        "classDef known fill:#E7F3FF,stroke:#3366CC,color:#000;",
        "classDef solved fill:#E6FFEA,stroke:#2f855a,color:#000;",
        "classDef unknown fill:#FFFFFF,stroke:#999,color:#000;",
    ]

    for nid, d in G.nodes(data=True):
        ntype = d.get("type", "")
        label = node_label(nid, d)
        if nid in solved_nodes:
            klass = "solved"
        else:
            klass = "known" if d.get("value") is not None else "unknown"
        # 用节点类型+自增索引做“可读 id”，避免长 uuid
        readable_id = f"{ntype}_{str(nid)[-4:]}"
        lines.append(f'{readable_id}["{label}"]:::{klass}')
        d["_readable_id"] = readable_id  # 暂存映射

    # 查找可读 id
    def rid(x):
        return G.nodes[x].get("_readable_id", x)

    for u, v, d in G.edges(data=True):
        text = edge_label(d)
        lines.append(f"{rid(u)} -->|{text}| {rid(v)}")

    return "\n".join(lines)
