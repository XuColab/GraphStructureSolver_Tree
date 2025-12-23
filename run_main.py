# from pathlib import Path
# import pandas as pd
# import re, json
# from core import builder as bd, registry as R
# from core.matcher import match
# from core.solver  import solve_equation
# from core.explain_visualize import explain_equation, export_graphviz, export_mermaid, export_mermaid_cn

# def detect_topic(question:str)->str|None:
#     """通过正则首轮粗判题型-topic（谁先命中用谁）"""
#     for topic, rule_set in R.RULE_REGISTRY.items():
#         if any(rx.search(question) for rx, _ in rule_set if rx != "__AUTO__"):
#             return topic

#     return None

# _RX_T_LENGTH = re.compile(r'(?:周长|全长|长度|长多少|多长|一周有多少米)')
# _RX_T_TREE   = re.compile(r'(?:多少|几)(?:棵|面|盏|个|根|只|株|辆|位|人|块|次|盆|支|杆)')
# _RX_T_INT    = re.compile(r'(?:每隔多少|平均每隔多少|间隔多少|相距多少|相邻距离多少)')

# def detect_target(question: str) -> str | None:
#     q = question
#     if _RX_T_LENGTH.search(q): return "Length"
#     if _RX_T_TREE.search(q):   return "TreeCnt"
#     if _RX_T_INT.search(q):    return "Interval"
#     return None


# def solve(question:str):
#     topic = detect_topic(question)
    
#     if not topic:
#         return "未识别题型"

#     gb = bd.GraphBuilder()

#     gb.G.graph["target"] = detect_target(question)   # 【新增】目标量提示

#     # 1) regex 生成节点 / 边
#     for rx, fn in R.RULE_REGISTRY[topic]:
#         if rx == "__AUTO__":
#             continue
        
#         for m in rx.finditer(question):
#             fn(m, gb)

#     # ★ 在执行 __AUTO__ hook 之前规范化模式（靠已知值判断 distance/quantity 等）
#     if hasattr(gb, "normalize_mode_by_knowns"):
#         gb.normalize_mode_by_knowns()


#     # 2) hook 补漏
#     for rx, fn in R.RULE_REGISTRY[topic]:
#         if rx == "__AUTO__":
#             fn(gb)

#     print("构建的图：", gb.G.nodes(data=True), gb.G.edges(data=True))
#     print("图模式：", gb.G.graph.get("topic"), gb.G.graph.get("mode"))
    
#     # 3) 模板匹配 + 求解
#     tpl, mp = match(gb.G)
    
#     if not tpl:
#         return "无子图匹配"
    
#     return solve_equation(tpl, mp, gb.G)
    
# # 追加：一键解题 + 解释 + 可视化
# def solve_with_explain(question: str,
#                     export: str = "graphviz",
#                     out_prefix: str = "out/q"):
#     """
#     export: "graphviz" | "mermaid" | None
#     out_prefix: 导出文件前缀（graphviz: 生成 out/q.dot；mermaid: 生成 out/q.mmd）
#     返回: 可解释包 dict（包含 solved / formulas / instantiated / notes / mapping 等）
#     """

#     topic = detect_topic(question)
#     if not topic:
#         print("未识别题型")
#         return None
#     gb = bd.GraphBuilder()
    
#     # 1) 规则抽取
#     for rx, fn in R.RULE_REGISTRY[topic]:
#         if rx == "__AUTO__":
#             continue
#         for m in rx.finditer(question):
#             fn(m, gb)

#     # 先归一模式，再跑 __AUTO__ hooks
#     if hasattr(gb, "normalize_mode_by_knowns"):
#         gb.normalize_mode_by_knowns()            
            
#     # 2) hook 补漏/提模式
#     for rx, fn in R.RULE_REGISTRY[topic]:
#         if rx == "__AUTO__":
#             fn(gb)
#     print("构建的图：", gb.G.nodes(data=True), gb.G.edges(data=True))
#     print("子图匹配：", gb.G.graph.get("topic"), gb.G.graph.get("mode"))


#     # 3) 子图匹配
#     tpl, mapping = match(gb.G)
#     if not tpl:
#         print("无子图匹配")
#         return None
    
#     # 4) 解释包（含整数化结果）
#     pkg = explain_equation(tpl, mapping, gb.G)
    
#     # 5) 打印关键说明（替代散乱日志）
#     print("【模板】", pkg["template_id"], "【模式】", pkg["mode"])
#     print("【公式】", pkg["formulas"])
#     print("【代入】", pkg["instantiated"])
#     print("【解】  ", pkg["solved"])
#     if pkg["notes"]:
#         print("【说明】", " | ".join(pkg["notes"]))

#     # 6) 可视化导出（2选1，或关闭）
#     import os
#     os.makedirs(os.path.dirname(out_prefix), exist_ok=True)
    
#     # 把图对象放回去，便于外层需要时直接用
#     pkg["__G"] = gb.G
    
#     if export == "graphviz":
#         dot_path = f"{out_prefix}.dot"
#         export_graphviz(gb.G, mapping=pkg["mapping"], solved=pkg["solved"], filename=dot_path)
#         print("Graphviz DOT:", dot_path, "（在命令行运行：dot -Tpng", dot_path, "-o", out_prefix + ".png）")
#     elif export == "mermaid":
#         # mmd = export_mermaid(gb.G, mapping=pkg["mapping"], solved=pkg["solved"])
#         # mmd_path = f"{out_prefix}.mmd"
#         # with open(mmd_path, "w", encoding="utf-8") as f:
#         #     f.write(mmd)
#         # print("Mermaid 文件：", mmd_path, "（将文本粘到支持 Mermaid 的 Markdown/网页即可渲染）")
        
#         # 英文原版（保留内部 id）
#         mmd_en = export_mermaid(pkg["__G"], mapping=pkg["mapping"], solved=pkg["solved"])
#         with open(f"{out_prefix}_en.mmd","w",encoding="utf-8") as f:
#             f.write(mmd_en)

#         # 中文友好版
#         mmd_cn = export_mermaid_cn(pkg["__G"], mapping=pkg["mapping"], solved=pkg["solved"])
#         with open(f"{out_prefix}_cn.mmd","w",encoding="utf-8") as f:
#             f.write(mmd_cn)
            
#         print("Mermaid（英文）文件：", f"{out_prefix}_en.mmd")
#         print("Mermaid（中文）文件：", f"{out_prefix}_cn.mmd")

#     # 别在 return 后面再写任何东西
#     return pkg
    
# if __name__=="__main__":
#     # 从 Excel 文件中读取题目列表；使用相对路径或Path拼接
#     # dataset_path = Path(__file__).parent / "dataset" / "PlantingTree100.xlsx"
#     dataset_path = Path(__file__).parent / "dataset" / "Trip_test.xlsx"
    
#     # 读取第一个工作表sheet_name="Sheet1"，从第二行开始读取（header=1），读取前50行（nrows=50）
#     df = pd.read_excel(dataset_path, sheet_name = "Sheet1", nrows=50)

#     # 与 JSON 保持相同的数据结构（list[dict]）
#     question_col = "question"
#     questions = (
#         df.rename(columns={question_col: "question"})
#         .assign(question=lambda d: d["question"].astype(str).str.strip())
#         .to_dict(orient="records")
#     )

#     # 后续处理与 JSON 完全一致
#     for i, item in enumerate(questions, 1):
#         q = item["question"]
#         print(f"\nQ{i}: {q}")
#         print("----->", solve(q))
        
#         # print(f"数学题集中标记的题型: {item['type']}, 答案: {item.get('answer')}")
#         print(f"数据集中标记的答案: {item.get('answer')}")

# --- 2025-10-27版 ---
from pathlib import Path
import pandas as pd
import re, json
from core import builder as bd, registry as R
from core.matcher import match
from core.solver  import solve_equation
from core.explain_visualize import explain_equation

def preprocess(text: str) -> str:
    # 统一空白与常见中文标点
    t = (text or "")
    t = t.replace("\u3000", " ")          # 全角空格
    t = t.replace("\r", " ").replace("\n", " ") # 换行→空格
    t = t.replace("，", ",").replace("。", ".").replace("：", ":").replace("；", ";")
    t = " ".join(t.split()) # 压缩多空格
    return t

# 新增：统一评分函数
# def score_solution(route_conf: float, tpl: dict|None, mapping: dict|None, solved_ok: bool, G):
    # Coverage
    cov = 0.0
    if tpl and mapping:
        need = len(tpl.get("nodes", [])) or 1
        cov = min(1.0, len(mapping) / need)

    # 目标覆盖
    tgt_ok = 0.0
    tgt = G.graph.get("target")
    if tpl and tgt:
        tpl_types = [n.get("type") for n in tpl.get("nodes", [])]
        if tgt in tpl_types:
            tgt_ok = 1.0

    # SolveOK
    solv = 1.0 if solved_ok else 0.0

    # ====== Constraint：模板是否与图中“delta_t”一致 ======
    tpl_id = (tpl or {}).get("id", "")
    has_dt = any(attr.get("type")=="Time" and attr.get("role")=="delta_t"
                 for _, attr in G.nodes(data=True))
    cons = 0.5  # 中性起点
    if has_dt:
        if "DeltaT" in tpl_id:
            cons = 1.0
        elif "Simultaneous" in tpl_id:
            cons = 0.0
    else:
        if "DeltaT" in tpl_id:
            cons = 0.0
        elif "Simultaneous" in tpl_id:
            cons = 1.0

    # 权重（可微调）
    α, β, γ, δ, ζ = 0.2, 0.25, 0.2, 0.2, 0.05
    return α*route_conf + β*cov + γ*cons + δ*solv + ζ*tgt_ok

def score_solution(route_conf: float, tpl: dict | None, mapping: dict | None, solved_ok: bool, G):
    # Coverage
    cov = 0.0
    if tpl and mapping:
        need = len(tpl.get("nodes", [])) or 1
        cov = min(1.0, len(mapping) / need)

    # 目标覆盖
    tgt_ok = 0.0
    tgt = G.graph.get("target")
    if tpl and tgt:
        tpl_types = [n.get("type") for n in tpl.get("nodes", [])]
        if tgt in tpl_types:
            tgt_ok = 1.0

    # SolveOK
    solv = 1.0 if solved_ok else 0.0

    # === Constraint：只在 trip 题型上启用 DeltaT/Simultaneous 约束 ===
    cons = 0.5  # 中性起点（对非 trip 不加不减）
    topic = (tpl or {}).get("topic") or G.graph.get("topic")  # tpl 优先，其次取图上的 topic
    if topic == "trip":
        tpl_id = (tpl or {}).get("id", "")
        has_dt = any(
            attr.get("type") == "Time" and attr.get("role") == "delta_t"
            for _, attr in G.nodes(data=True)
        )
        if has_dt:
            cons = 1.0 if "DeltaT" in tpl_id else 0.0
        else:
            cons = 1.0 if "Simultaneous" in tpl_id else 0.0

    # 权重（可微调）
    α, β, γ, δ, ζ = 0.2, 0.25, 0.2, 0.2, 0.05
    return α * route_conf + β * cov + γ * cons + δ * solv + ζ * tgt_ok

def route_phase(text: str):
    """Phase-1：跨所有题型跑路由规则，返回候选列表"""
    gb = bd.GraphBuilder()
    gb.G.graph["raw_text"] = text

    hit_any = False
    for topic, rules in R.ROUTE_REGISTRY.items():
        for rx, fn in rules:
            for m in re.finditer(rx, text, flags=re.I|re.S) if isinstance(rx, str) else rx.finditer(text):
                fn(m, gb); hit_any = True

    cands = gb.get_candidates()
    # 兜底：若没任何命中，给 tree 一个很低置信度候选，避免“未识别题型”
    if not cands:
        gb.add_candidate("tree", None, confidence=0.01, source="fallback")
        cands = gb.get_candidates()
    return gb, cands

def _get_node_value(G, node_id):
    # 取节点数值（统一单位建议在 solver 内做归一，这里只拿原值即可）
    return G.nodes[node_id].get("value")

def canonicalize_trip_variables(tpl_id, mapping, G):
    """仅针对 Trip_Chase，保证 Vf>Vs；也保证 gap 为正"""
    if not mapping or not tpl_id:
        return mapping
    if "Trip_Chase" in tpl_id:
        # 拿到两个速度对应的节点 id
        vfid = mapping.get("Vf")
        vsid = mapping.get("Vs")
        if vfid and vsid:
            vf = _get_node_value(G, vfid)
            vs = _get_node_value(G, vsid)
            if vf is not None and vs is not None and vf < vs:
                # 交换
                mapping["Vf"], mapping["Vs"] = mapping["Vs"], mapping["Vf"]
        # gap 取正（如果你想更严格，也可以在抽取时强制 role="gap" 的 value>0）
        gid = mapping.get("Dgap")
        if gid:
            gapv = _get_node_value(G, gid)
            if gapv is not None and gapv < 0:
                G.nodes[gid]["value"] = abs(gapv)
    return mapping

def extract_and_solve(text: str, cand):
    """Phase-2：对单一候选进行抽取→=匹配→求解，返回(分数,结果包,图)"""
    g = bd.GraphBuilder()
    g.G.graph.update(raw_text=text)

    topic, mode, conf = cand["topic"], cand.get("mode"), cand.get("conf", 0.0)

    # 抽取规则（仅跑该 topic 的 Phase-2 规则）
    for rx, fn in R.RULE_REGISTRY.get(topic, []):
        if rx == "__AUTO__":  # 兼容旧规则写法：忽略 __AUTO__
            continue
        it = re.finditer(rx, text, flags=re.I|re.S) if isinstance(rx, str) else rx.finditer(text)
        for m in it:
            fn(m, g)

    # 设定题型与模式（若路由阶段没给出 mode，可允许后续规范函数修正）
    if mode:
        g.set_pattern(topic, mode, override=True)
    else:
        g.G.graph["topic"] = topic  # 先只立 topic
        if hasattr(g, "normalize_mode_by_knowns"):
            g.normalize_mode_by_knowns()  # 让 tree 的模式归一发挥作用
    
    print("DEBUG all nodes:", [(nid, d.get("type"), d.get("role"), d.get("value"), d.get("unit")) for nid, d in g.G.nodes(data=True)])
    
    # 子图匹配
    tpl, mapping = match(g.G)
    if not tpl:
        return 0.0, {"error": "no_match", "topic": topic, "mode": g.G.graph.get("mode")}, g.G

    # 规范化 Trip 变量（确保 Vf>Vs）
    mapping = canonicalize_trip_variables(tpl.get("id"), mapping, g.G)
    
    # 求解
    try:
        solved = solve_equation(tpl, mapping, g.G)
        ok = (solved is not None)
    except Exception:
        solved = None; ok = False

    sc = score_solution(conf, tpl, mapping, ok, g.G)
    
    # 调试信息
    print("DEBUG Time nodes:", [(nid, d) for nid, d in g.G.nodes(data=True) if d.get("type")=="Time"])

    return sc, {"template": tpl.get("id"), "mode": tpl.get("mode", g.G.graph.get("mode")), "solved": solved}, g.G

def solve(question: str):
    question = preprocess(question)
    
    # Phase-1：路由
    gb, candidates = route_phase(question)

    print("DEBUG Time nodes:", [(nid, d) for nid, d in gb.G.nodes(data=True) if d.get("type")=="Time"])
    
    # --- 去重：按 (topic, mode) 保留置信度最高的候选 ---
    uniq = {}
    for c in candidates:
        key = (c["topic"], c.get("mode"))
        if key not in uniq or c.get("conf", 0.0) > uniq[key].get("conf", 0.0):
            uniq[key] = c
        else:
            # 可选：合并来源，方便日志排查
            src_old = uniq[key].get("source")
            src_new = c.get("source")
            if src_new:
                merged = []
                if isinstance(src_old, list): merged += src_old
                elif src_old: merged.append(src_old)
                if isinstance(src_new, list): merged += src_new
                else: merged.append(src_new)
                uniq[key]["source"] = list(dict.fromkeys(merged))
    candidates = list(uniq.values())
    candidates.sort(key=lambda x: x.get("conf", 0.0), reverse=True)
    # --- 去重结束 ---

    # Phase-2：前 K 个候选逐一试解（K=3 可调）
    tried = []
    for cand in candidates[:3]:
        sc, res, g = extract_and_solve(question, cand)
        tried.append((sc, cand, res))

    if not tried:
        return "未识别题型"

    # 选最优 & 可选保留接近的次优
    tried.sort(key=lambda x: x[0], reverse=True)
    best_sc, best_cand, best_res = tried[0]
    return {"score": best_sc, "candidate": best_cand, "result": best_res}

if __name__=="__main__":
    dataset_path = Path(__file__).parent / "dataset" / "Trip_test.xlsx"
    df = pd.read_excel(dataset_path, sheet_name="Sheet1", nrows=50)
    questions = (df.rename(columns={"question": "question"})
                   .assign(question=lambda d: d["question"].astype(str).str.strip())
                   .to_dict(orient="records"))
    for i, item in enumerate(questions, 1):
        q = item["question"]
        print(f"\nQ{i}: {q}")
        out = solve(q)
        print("----->", out)
        print(f"数据集中标记的答案: {item.get('answer')}")