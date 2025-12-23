from sympy import symbols, Eq, sympify, solve, floor, N, nsimplify

def normalize_units(value, unit):
    if unit in ("km","公里","千米"):  return value * 1000, "m"
    if unit in ("m","米"):            return value, "m"
    if unit in ("km/h","公里/小时","千米/小时"): return value * (1000/3600), "m/s"
    if unit in ("m/s","米/秒"):       return value, "m/s"
    if unit in ("h","小时"):          return value * 3600, "s"
    if unit in ("min","分钟"):        return value * 60,   "s"
    if unit in ("s","秒"):            return value, "s"
    return value, unit

def solve_equation(tpl, mapping, G):
    """
    tpl      : 子图模板 dict（不含任何 'cast' 字段）
    mapping  : networkx 返回的模板节点 ➜ 题目节点 映射
    G        : 构建好的题目图
    """
    # ---------- 0. 映射方向标准化 ----------
    tpl_ids = {n["id"] for n in tpl["nodes"]}
    if not (set(mapping.keys()) & tpl_ids):
        mapping = {tpl_id: prob_id for prob_id, tpl_id in mapping.items()}

    # ---------- 1. 建符号表 ----------
    symtab = {n["id"]: symbols(n["id"]) for n in tpl["nodes"]}

    # 补一个：模板节点 id -> 节点类型（用于结果后处理判断是否为计数类）
    node_type_map = {n["id"]: n["type"] for n in tpl["nodes"]}

    # ---------- 2. 收集已知值（整值浮点 -> 整数；避免把 Float 传播到方程里） ----------
    def _coerce_num(val):
        # 20.0 -> 20；其他浮点保留
        if isinstance(val, float) and float(val).is_integer():
            return int(val)
        return val

    given = {
        symtab[tpl_id]: _coerce_num(G.nodes[prob_id]["value"])
        for tpl_id, prob_id in mapping.items()
        if G.nodes[prob_id].get("value") is not None and tpl_id in symtab
    }

    # ---------- 3. 转换公式为 sympy 方程 ----------
    eqs = [
        Eq(*[sympify(side.strip(), locals=symtab) for side in f.split("=")])
        for f in tpl["formula"]
    ]

    # ---------- 4. 解未知 ----------
    # unknown_syms = [symtab[uid] for uid in tpl["unknowns"]]
    # solved = solve([e.subs(given) for e in eqs], unknown_syms, dict=True)


    
    # === 新增：先把 givens 代入并打印便于调试 ===
    eqs_sub = [e.subs(given) for e in eqs]
    G.graph["__instantiated_eqs__"] = [str(e) for e in eqs_sub]
    
    print("【代入后方程】", " ; ".join(str(e) for e in eqs_sub))

    # unknown_syms = [symtab[uid] for uid in tpl["unknowns"]]
    # # 原先：solved = solve([e.subs(given) for e in eqs], unknown_syms, dict=True)
    # solved = solve(eqs_sub, unknown_syms, dict=True)    
    # === A. 自动识别未知量（忽略/越过模板里的 unknowns） ===
    unknown_ids = set()

    # 1) 题目图中“值为 None”的映射点，一律视为未知量
    for tpl_id, prob_id in mapping.items():
        if prob_id in G.nodes and G.nodes[prob_id].get("value") is None:
            unknown_ids.add(tpl_id)

    # 2) 若模板里也写了 unknowns，则只把“仍是未知”的那些纳入（已知的就忽略）
    for uid in tpl.get("unknowns", []):
        pid = mapping.get(uid)
        if pid and G.nodes.get(pid, {}).get("value") is None:
            unknown_ids.add(uid)

    unknown_syms = [symtab[u] for u in unknown_ids]

    # === B. 求解（若 unknown_syms 为空先尝试直接解自由符号） ===
    solved = []
    if unknown_syms:
        solved = solve(eqs_sub, unknown_syms, dict=True)

    # 兜底 1：若还没解出来，且是单方程，尝试对“仍在方程里的符号”逐个求
    if not solved and len(eqs_sub) == 1:
        # 优先对题目里确实未知的符号求解；若没有，再对所有自由符号尝试
        cand_syms = [symtab[u] for u in unknown_ids] or list(eqs_sub[0].free_symbols)
        for u in cand_syms:
            try:
                v = solve(eqs_sub[0], u)
                if v:
                    solved = [{u: v[0]}]
                    break
            except Exception:
                pass

    print(f"求解结果：{solved}")

    if not solved:
        return {}

    raw = solved[0]

    # ---------- 5. 结果后处理：对计数类（TreeCnt/SegmentCnt/Diff）做整数化 ----------
    # def _intify_if_count(tpl_id, val):
    #     t = node_type_map.get(tpl_id)
    #     if t in {"TreeCnt", "SegmentCnt", "Diff"}:
    #         try:
    #             # 先尽量化简为有理数/整数，再转 int；兜底用 round
    #             v_simpl = nsimplify(val, rational=True)
    #             if getattr(v_simpl, "is_integer", False):
    #                 return int(v_simpl)
    #             return int(round(float(v_simpl)))
    #         except Exception:
    #             try:
    #                 return int(round(float(val)))
    #             except Exception:
    #                 return val
    #     # 非计数类原样返回（可选：也可 nsimplify 一下）
    #     return val
    def _intify_if_count(tpl_id, val):
        """若模板变量映射到题面图的节点类型属于计数类（TreeCnt/SegmentCnt/Diff），则做整数化"""
        try:
            prob_id = mapping.get(tpl_id)
            ntype = G.nodes.get(prob_id, {}).get("type")
            if ntype in {"TreeCnt", "SegmentCnt", "Diff"}:
                try:
                    v_simpl = nsimplify(val)
                    return int(round(float(v_simpl)))
                except Exception:
                    try:
                        return int(round(float(val)))
                    except Exception:
                        return val
            return val
        except Exception:
            return val

    post = {}
    for sym_k, v in raw.items():
        tpl_id = str(sym_k)  # sympy.Symbol -> its name，如 'Z'
        post[tpl_id] = _intify_if_count(tpl_id, v)

    return post