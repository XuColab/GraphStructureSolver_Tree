import re, json
from core import builder as bd, registry as R
from core.matcher import match
from core.solver  import solve_equation
from core.explain_visualize import explain_equation, export_graphviz, export_mermaid, export_mermaid_cn

def detect_topic(question:str)->str|None:
    """通过正则首轮粗判题型-topic（谁先命中用谁）"""
    for topic, rule_set in R.RULE_REGISTRY.items():
        if any(rx.search(question) for rx, _ in rule_set if rx != "__AUTO__"):
            return topic

    return None

def solve(question:str):
    topic = detect_topic(question)
    
    if not topic:
        return "未识别题型"

    gb = bd.GraphBuilder()

    # 1) regex 生成节点 / 边
    for rx, fn in R.RULE_REGISTRY[topic]:
        if rx == "__AUTO__":
            continue
        
        for m in rx.finditer(question):
            fn(m, gb)

    # 2) hook 补漏
    for rx, fn in R.RULE_REGISTRY[topic]:
        if rx == "__AUTO__":
            fn(gb)

    print("构建的图：", gb.G.nodes(data=True), gb.G.edges(data=True))
    print("图模式：", gb.G.graph.get("topic"), gb.G.graph.get("mode"))
    
    # 3) 模板匹配 + 求解
    tpl, mp = match(gb.G)
    
    if not tpl:
        return "无子图匹配"
    
    return solve_equation(tpl, mp, gb.G)
    
# 追加：一键解题 + 解释 + 可视化
def solve_with_explain(question: str,
                    export: str = "graphviz",
                    out_prefix: str = "out/q"):
    """
    export: "graphviz" | "mermaid" | None
    out_prefix: 导出文件前缀（graphviz: 生成 out/q.dot；mermaid: 生成 out/q.mmd）
    返回: 可解释包 dict（包含 solved / formulas / instantiated / notes / mapping 等）
    """

    topic = detect_topic(question)
    if not topic:
        print("未识别题型")
        return None
    gb = bd.GraphBuilder()
    
    # 1) 规则抽取
    for rx, fn in R.RULE_REGISTRY[topic]:
        if rx == "__AUTO__":
            continue
        for m in rx.finditer(question):
            fn(m, gb)
            
    # 2) hook 补漏/提模式
    for rx, fn in R.RULE_REGISTRY[topic]:
        if rx == "__AUTO__":
            fn(gb)
    print("构建的图：", gb.G.nodes(data=True), gb.G.edges(data=True))
    print("子图匹配：", gb.G.graph.get("topic"), gb.G.graph.get("mode"))
    
    # 3) 子图匹配
    tpl, mapping = match(gb.G)
    if not tpl:
        print("无子图匹配")
        return None
    
    # 4) 解释包（含整数化结果）
    pkg = explain_equation(tpl, mapping, gb.G)
    
    # 5) 打印关键说明（替代散乱日志）
    print("【模板】", pkg["template_id"], "【模式】", pkg["mode"])
    print("【公式】", pkg["formulas"])
    print("【代入】", pkg["instantiated"])
    print("【解】  ", pkg["solved"])
    if pkg["notes"]:
        print("【说明】", " | ".join(pkg["notes"]))

    # 6) 可视化导出（2选1，或关闭）
    import os
    os.makedirs(os.path.dirname(out_prefix), exist_ok=True)
    
    # 把图对象放回去，便于外层需要时直接用
    pkg["__G"] = gb.G
    
    if export == "graphviz":
        dot_path = f"{out_prefix}.dot"
        export_graphviz(gb.G, mapping=pkg["mapping"], solved=pkg["solved"], filename=dot_path)
        print("Graphviz DOT:", dot_path, "（在命令行运行：dot -Tpng", dot_path, "-o", out_prefix + ".png）")
    elif export == "mermaid":
        # mmd = export_mermaid(gb.G, mapping=pkg["mapping"], solved=pkg["solved"])
        # mmd_path = f"{out_prefix}.mmd"
        # with open(mmd_path, "w", encoding="utf-8") as f:
        #     f.write(mmd)
        # print("Mermaid 文件：", mmd_path, "（将文本粘到支持 Mermaid 的 Markdown/网页即可渲染）")
        # 英文原版（保留内部 id）
        mmd_en = export_mermaid(pkg["__G"], mapping=pkg["mapping"], solved=pkg["solved"])
        with open(f"{out_prefix}_en.mmd","w",encoding="utf-8") as f:
            f.write(mmd_en)

        # 中文友好版
        mmd_cn = export_mermaid_cn(pkg["__G"], mapping=pkg["mapping"], solved=pkg["solved"])
        with open(f"{out_prefix}_cn.mmd","w",encoding="utf-8") as f:
            f.write(mmd_cn)
            
        print("Mermaid（英文）文件：", f"{out_prefix}_en.mmd")
        print("Mermaid（中文）文件：", f"{out_prefix}_cn.mmd")

    # 别在 return 后面再写任何东西
    return pkg
    
if __name__=="__main__":
    # 从 JSON 文件中读取题目列表

    # with open("D:/DiagramOrGraphSolver/GraphStructureSolver_Tree/dataset/tree_basic.json", "r", encoding="utf-8") as f:
    #     questions = json.load(f)    
    
    # 换成相对路径或用 Path 拼接，避免不同机器运行失败
    from pathlib import Path
    dataset_path = Path(__file__).parent / "dataset" / "tree_basic.json" # PlantingTree1k
    with open(dataset_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    for i, item in enumerate(questions, 1):
        q = item["question"]
        print(f"\nQ{i}: {q}")
        print("----->", solve(q))
        
        # print(f"数学题集中标记的题型: {item['type']}, 答案: {item.get('answer')}")
        print(f"数据集中标记的答案: {item.get('answer')}")
        
        # 每题一个文件，避免覆盖
        out_prefix = f"LogicGraph_output/q{i}"
        solve_with_explain(q, export="mermaid", out_prefix=out_prefix)

        # pkg = solve_with_explain(q, export=None, out_prefix=out_prefix)  # 先只算、拿到 pkg
        # if pkg is None:
        #     continue

        # # 用“中文友好版 Mermaid”导出
        # import os
        # os.makedirs(os.path.dirname(out_prefix), exist_ok=True)

        # mmd = export_mermaid_cn(pkg["__G"], mapping=pkg["mapping"], solved=pkg["solved"])

        # mmd_path = f"{out_prefix}.mmd"
        # with open(mmd_path, "w", encoding="utf-8") as f:
        #     f.write(mmd)
        # print("Mermaid（中文）文件：", mmd_path)