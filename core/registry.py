"""
一次 I/O ，把规则 & 模板 注册 / 读盘 到全局变量，常驻内存。
负责一次性读盘→常驻内存：1) 收集所有 regex 规则；2) 把 subgraphs/*.json 读成 dict 列表，供 matcher.py 搜索。

2025-10-27新增：先路由收集候选 → 再逐候选抽取/匹配/求解 → 按统一评分选最优，天然支持扩题 & 混合题
"""
import pathlib, json, pkgutil, importlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUBGRAPH_DIR = ROOT / "subgraphs"

# ---------- 规则 ----------
RULE_REGISTRY = {} # 全局 dict {"tree":[(regex,action)…]}，在 rules 文件里调用 register_rule(rule) 即可加入
def register_rule(topic: str, rule):
    """
    在各 rules_*.py 中调用： register_rule(topic, (regex, action_fn))
    """
    RULE_REGISTRY.setdefault(topic, []).append(rule)

# ---------- 新增路由（Phase-1）:在现有内容基础上，新增路由规则池和 register_route ---------

ROUTE_REGISTRY = {}  # Phase-1：题型路由，只收集候选，不直接写 topic/mode
def register_route(topic: str, rule):
    """
    在 rules_*.py 中调用：register_route(topic, (regex, action))
    action(m, g) 里只调用 g.add_candidate(...)，不要写 g.set_pattern(...)
    """
    ROUTE_REGISTRY.setdefault(topic, []).append(rule)

# 动态 import rules/*.py，文件名格式必须 `rules_<topic>.py`
for mod in pkgutil.iter_modules([str(ROOT / "rules")]):
    if not mod.name.startswith("rules_"):
        continue
    importlib.import_module(f"rules.{mod.name}")

# ---------- 子图模板 ----------
# load templates，循环 subgraphs/*.json 读成 dict，后续 matcher.py 直接遍历此列表做同构匹配
SUBGRAPH_REGISTRY = []
# for fp in pathlib.Path("subgraphs").glob("*.json"):
for fp in SUBGRAPH_DIR.glob("*.json"):
    data = json.load(fp.open(encoding="utf-8"))
    SUBGRAPH_REGISTRY.extend(data if isinstance(data,list) else [data])

print("子图模板数:", len(SUBGRAPH_REGISTRY))
print("已加载题型:", list(RULE_REGISTRY.keys()))
print([tpl["mode"] for tpl in SUBGRAPH_REGISTRY]) # 验证模板加载


print("DEBUG trip templates:", [t["id"] for t in SUBGRAPH_REGISTRY if t.get("topic")=="trip"])