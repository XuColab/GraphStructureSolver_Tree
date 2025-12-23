def debug_subgraph_match(g, templates):
    """
    调试子图匹配问题
    参数：
        g: GraphBuilder 或其包含图的对象 (g.G)
        templates: 可用的子图模板列表，每个模板为 dict
                   必须包含 keys: 'id', 'nodes', 'edges'
    """
    G = g.G if hasattr(g, "G") else g  # 支持直接传入 g.G
    g_nodes = {data["type"] for _, data in G.nodes(data=True)}
    g_edges = {(data["type"], data.get("op")) for _, _, data in G.edges(data=True)}

    print("=== 调试子图匹配 ===")
    print("图节点类型：", g_nodes)
    print("图边类型：", g_edges)

    match_found = False

    for tmpl in templates:
        tmpl_id = tmpl.get("id", "unknown")
        tmpl_nodes = {n["type"] for n in tmpl.get("nodes", [])}
        tmpl_edges = {(e["type"], e.get("op")) for e in tmpl.get("edges", [])}

        missing_nodes = tmpl_nodes - g_nodes
        missing_edges = tmpl_edges - g_edges

        if not missing_nodes and not missing_edges:
            print(f"模板 [{tmpl_id}] 完全匹配")
            match_found = True
        else:
            print(f"模板 [{tmpl_id}] 不匹配")
            if missing_nodes:
                print("缺失节点类型：", missing_nodes)
            if missing_edges:
                print("缺失边类型：", missing_edges)

    if not match_found:
        print("没有模板与当前图完全匹配")
        
def auto_fix_graph(g, tmpl):
    """
    根据给定模板自动补齐缺失的节点和边。
    参数：
        g: GraphBuilder 或其包含图的对象 (g.G)
        tmpl: 目标子图模板 dict (包含 nodes 和 edges)
    返回：
        修复后的 g
    """
    G = g.G if hasattr(g, "G") else g  # 兼容 GraphBuilder 或直接传入 nx.Graph

    # 1. 补节点
    existing_node_types = {data["type"]: n for n, data in G.nodes(data=True)}
    for node in tmpl.get("nodes", []):
        n_type = node["type"]
        if n_type not in existing_node_types:
            new_id = node.get("id", f"{n_type}_{len(G.nodes)}")
            G.add_node(new_id, type=n_type, value=None)
            print(f"补充节点: {new_id} (type={n_type})")

    # 2. 补边
    existing_edges = {(data["type"], data.get("op")) for _, _, data in G.edges(data=True)}
    # 根据类型找到节点 ID
    def find_node_by_type(n_type):
        for nid, data in G.nodes(data=True):
            if data.get("type") == n_type:
                return nid
        return None

    for edge in tmpl.get("edges", []):
        e_type = edge["type"]
        e_op = edge.get("op")
        if (e_type, e_op) not in existing_edges:
            u = find_node_by_type(edge["u"]) or find_node_by_type(edge["u"].capitalize())
            v = find_node_by_type(edge["v"]) or find_node_by_type(edge["v"].capitalize())
            if u and v:
                G.add_edge(u, v, type=e_type, op=e_op)
                print(f"补充边: {u} - {v} (type={e_type}, op={e_op})")
            else:
                print(f"无法补充边 (缺少对应节点类型 {edge['u']} 或 {edge['v']})")

    print("修复完成！")
    return g   

def debug_and_fix(g, templates):
    print("第一步：初始匹配调试")
    debug_subgraph_match(g, templates)

    for tmpl in templates:
        print(f"\n第二步：尝试修复模板 [{tmpl.get('id')}]")
        auto_fix_graph(g, tmpl)

        print("第三步：修复后再次匹配验证")
        debug_subgraph_match(g, [tmpl])
        print("="*40)     