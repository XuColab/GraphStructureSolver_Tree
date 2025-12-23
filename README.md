###### Graph Solver · Tree Edition 🌳

<!-- 文件结构 -->
core/ 公共引擎 (与题型解耦)
rules/ 正则 + hook 仅 1 个文件
subgraphs/Tree_templates.json 三端点合一
tests/ 12 断言可扩充

> 后续若要扩题型，只需再加 `rules_xxx.py` + 对应 JSON 模板，无需动核心代码。

GraphStructureSolver_tree/
├─ core/
│  ├─ builder.py
│  ├─ matcher.py
│  ├─ solver.py
│  └─ registry.py
├─ rules/
│  └─ rules_tree.py
├─ subgraphs/
│  └─ Tree_templates.json
├─ tests/
│  └─ test_tree.py
├─ tree_demo.py
├─ README.md
└─ requirements.txt

<!-- 核心思路 -->
规则抽取 ➜ 把文字映射为 GraphBuilder 节点 / 边
Hook ➜ 补隐含量：段数 N、tree_relation(±1/0)
子图匹配 (VF2) ➜ 三端点模式一键匹配
SymPy 求解 ➜ 统一 formula + unknowns_set

##### “图模板解题”的独特卖点:
像画电路图一样解题：每个量都是一个节点，每个关系都有箭头和标注（divides, PLUS1…），逻辑结构一眼能懂。
模型化 + 可扩展：新题型只需加模板或小补丁，无需改旧题；模板是“规范”，不是黑箱规则。
步骤透明：从文本抽取 → 建图 → 匹配 → 代入 → 求解，步骤齐全、全可视。
鲁棒可诊断：子图匹配失败时，能立刻指出“缺哪个节点/边/类型不一致”，定位问题很快。
结果安全可解释：有“计数统一整数化”“四角去重”等规则注释，避免答案“12.0000…”的困惑。