> 在 **不修改模板结构** 的前提下，**自动识别哪些变量需要向下取整**（如 `N = Y / X`，且类型是 `Length ÷ Interval`），并在求解结果中进行 `floor` 处理。

------

已根据原始函数**补全并内嵌了自动 `floor` 判断与处理逻辑**，保持所有原接口不变，只增强了求解环节：

------

###### 改写后的 `solve_equation_with_cast`

```python
from sympy import symbols, Eq, sympify, solve, floor, N

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

    # ---------- 2. 收集已知值 ----------
    given = {
        symtab[tpl_id]: G.nodes[prob_id]["value"]
        for tpl_id, prob_id in mapping.items()
        if G.nodes[prob_id].get("value") is not None
    }

    # ---------- 3. 转换公式为 sympy 方程 ----------
    eqs = [
        Eq(*[sympify(side.strip(), locals=symtab) for side in f.split("=")])
        for f in tpl["formula"]
    ]

    # ---------- 4. 构造类型查表 ----------
    type_table = {n["id"]: n["type"] for n in tpl["nodes"]}

    # ---------- 5. 分析公式，推理需要 floor 的变量 ----------
    cast_dict = {}
    for formula_str in tpl.get("formula", []):
        try:
            eq = sympify(formula_str, evaluate=False)
            if not isinstance(eq, Eq):
                continue
            lhs = str(eq.lhs)
            rhs = eq.rhs

            # 检查是否除法结构
            if rhs.func.__name__ == "Mul":
                for term in rhs.args:
                    if term.func.__name__ == "Pow" and term.args[1] == -1:
                        numerator = rhs.args[0]
                        denominator = term.args[0]
                        t1 = type_table.get(str(numerator))
                        t2 = type_table.get(str(denominator))
                        if {t1, t2} == {"Length", "Interval"}:
                            cast_dict[lhs] = "floor"
            elif rhs.func.__name__ == "Div" or rhs.func.__name__ == "Rational":
                a, b = map(str, rhs.args)
                t1 = type_table.get(a)
                t2 = type_table.get(b)
                if {t1, t2} == {"Length", "Interval"}:
                    cast_dict[lhs] = "floor"
        except:
            continue  # 安全跳过

    # ---------- 6. 解未知 ----------
    unknown_syms = [symtab[uid] for uid in tpl["unknowns"]]
    solved = solve([e.subs(given) for e in eqs], unknown_syms, dict=True)

    print(f"求解结果（未处理）：{solved}")

    # ---------- 7. 后处理：floor 处理 ----------
    if solved:
        result = solved[0]
        post_result = {}
        for k, v in result.items():
            if str(k) in cast_dict and cast_dict[str(k)] == "floor":
                post_result[str(k)] = floor(v)
            else:
                post_result[str(k)] = v
        return post_result
    else:
        return {}
```

------

###### 说明

| 部分          | 功能                                              |
| ------------- | ------------------------------------------------- |
| `type_table`  | 从 `tpl["nodes"]` 中提取变量类型                  |
| `cast_dict`   | 自动识别除法结构中满足 `Length ÷ Interval` 的情况 |
| `solve()`     | 原始 `sympy` 求解逻辑，无变动                     |
| `post_result` | 在求解后判断变量是否需要 `floor`，再处理输出      |

------

**使用示例不**

你依旧可以在主逻辑中调用：

```python
solve_equation(tpl, mapping, G)
```

无需在 `tpl` 中显式写明 `cast`。

------

**下一步可选增强**

若你希望未来支持更多规则（例如 `Total ÷ Average → floor`），我们可以将 `cast_dict` 生成逻辑抽出成：

```python
extract_cast_from_formula(tpl["formula"], type_table)
```

甚至用规则表驱动，如：

```python
CAST_RULES = [
    {"input": ("Length", "Interval"), "op": "div", "cast": "floor"},
    {"input": ("Total", "Average"), "op": "div", "cast": "floor"},
    ...
]
```



------

###### ✅ 第一部分：抽出 `extract_cast_from_formula` 函数

目的：从公式（`tpl["formula"]`）和节点类型表（`type_table`）中提取出需要进行 `cast`（如 `floor`）的变量，例如：

- `N = Y / X`
- 若 `Y: Length`，`X: Interval`
- 则自动得出：`cast_dict = {"N": "floor"}`

------

通用规则表驱动设计：引入一个规则表 `CAST_RULES`，可随时扩展.

```python
CAST_RULES = [
    {
        "op": "div",
        "input": ("Length", "Interval"),
        "cast": "floor"
    },
    {
        "op": "div",
        "input": ("Total", "Average"),
        "cast": "floor"
    },
    # 你可以继续添加更多规则...
]
```

------

函数定义：`extract_cast_from_formula`

```python
from sympy import Eq, sympify

def extract_cast_from_formula(formula_list, type_table, cast_rules):
    cast_dict = {}

    for formula_str in formula_list:
        try:
            eq = sympify(formula_str, evaluate=False)
            if not isinstance(eq, Eq):
                continue

            lhs = str(eq.lhs)
            rhs = eq.rhs

            # 检查是否除法结构：形如 A = B / C 或 A = B * C**-1
            if rhs.func.__name__ == "Mul":
                for term in rhs.args:
                    if term.func.__name__ == "Pow" and term.args[1] == -1:
                        numerator = str(rhs.args[0])
                        denominator = str(term.args[0])
                        type_pair = {type_table.get(numerator), type_table.get(denominator)}
                        # 规则匹配
                        for rule in cast_rules:
                            if rule["op"] == "div" and set(rule["input"]) == type_pair:
                                cast_dict[lhs] = rule["cast"]

            elif rhs.func.__name__ in {"Div", "Rational"} or "/" in formula_str:
                args = list(map(str, rhs.args))
                if len(args) == 2:
                    a, b = args
                    type_pair = {type_table.get(a), type_table.get(b)}
                    for rule in cast_rules:
                        if rule["op"] == "div" and set(rule["input"]) == type_pair:
                            cast_dict[lhs] = rule["cast"]

        except Exception:
            continue  # 忽略语法错误或不匹配

    return cast_dict
```

------

###### 第二部分：在主函数中调用

在原来的 `solve_equation` 中添加如下调用即可：

```python
# 新增：规则表
CAST_RULES = [
    {"op": "div", "input": ("Length", "Interval"), "cast": "floor"},
    {"op": "div", "input": ("Total", "Average"), "cast": "floor"},
    # 可扩展更多
]

# 新增：变量类型表
type_table = {n["id"]: n["type"] for n in tpl["nodes"]}

# 新增：提取 cast_dict
cast_dict = extract_cast_from_formula(tpl["formula"], type_table, CAST_RULES)
```

------

最终效果示例

输入：

```json
{
  "nodes": [
    {"id": "Y", "type": "Length"},
    {"id": "X", "type": "Interval"},
    {"id": "N", "type": "SegmentCnt"}
  ],
  "formula": ["N = Y / X"],
  "unknowns": ["N"]
}
```

自动推理：

```python
type_table = {"Y": "Length", "X": "Interval", "N": "SegmentCnt"}
CAST_RULES = [
    {"op": "div", "input": ("Length", "Interval"), "cast": "floor"}
]
```

输出：

```python
cast_dict = {"N": "floor"}
```

------

###### 总结：优势

| 特性                        | 好处                                           |
| --------------------------- | ---------------------------------------------- |
| `extract_cast_from_formula` | 模块化、便于调试                               |
| `CAST_RULES`                | 配置式可扩展（只改规则，不动代码）             |
| 结果自动应用到 `solve` 后   | 不改模板结构，保持纯净                         |
| 易于维护和测试              | 支持快速增加规则（如 Average ÷ Ratio → float） |

------

是否进一步生成一个 YAML 规则文件（可读入 CAST_RULES）？或者把整个模块整理成一个可导入的 Python 文件结构？