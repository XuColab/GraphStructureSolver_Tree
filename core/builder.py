import networkx as nx, uuid, schema as S
import re

# === Mode alias & canonicalization (add this near the top of builder.py) ===
MODE_ALIAS = {
    ("tree", "loop_closed_distance"): "loop_closed",
    ("tree", "loop_closed_count"):    "loop_closed",
    # 如需更多别名，可继续添加：
    ("tree", "loop_closed_len"):      "loop_closed",
    # ("tree", "loop_closed_cnt") 等
}

def _canonical_mode(topic: str, mode: str) -> str:
    """将 (topic, mode) 归一到模板库用的规范名"""
    if not topic or not mode:
        return mode
    return MODE_ALIAS.get((topic, mode), mode)

class GraphBuilder:
    def __init__(self):
        self.G = nx.MultiDiGraph()
        self.last_map: dict[str, str] = {} # 记录最新节点 id

    # === 2025-10-27 新增：候选题型池 ===
    def add_candidate(self, topic, mode=None, confidence=1.0, source=None, notes=None):
        cand = {"topic": topic, "mode": mode, "conf": float(confidence),
                "source": source, "notes": notes}
        self.G.graph.setdefault("_candidates", []).append(cand)

    def get_candidates(self):
        return sorted(self.G.graph.get("_candidates", []),
                      key=lambda x: x["conf"], reverse=True)

    def clone_empty(self):
        """为某个候选 topic 重新抽取时，复制一个‘空图’（仅保留文本等图级元数据）"""
        nb = GraphBuilder()
        for k in ("raw_text", "target"):
            if k in self.G.graph:
                nb.G.graph[k] = self.G.graph[k]
        return nb

    # === 2025-10-27 新增结束 ===
    
    # 取最近节点
    def last_of(self, type_: str) -> str | None:
        """返回最近加入的同类型节点 id；若不存在返回 None"""
        return self.last_map.get(type_)

    # def _ensure_topic(self, topic):
    #     """若图里还没有 topic，就写入；已有则保持原值"""
    #     if "topic" not in self.G.graph:
    #         self.G.graph["topic"] = topic

    # def add_node(self, *, type, value=None, **attrs):
    #     """
    #     添加一个节点到图中，type 是节点类型，value 是可选的值。
    #     - 如果已有同类型节点，且 value=None 或 value 相同，则直接返回该节点 id。
    #     - 如果已有同类型节点且有值，而新节点无值，则复用已有节点。
    #     """
    #     # --- 新增：允许动态编号类型，如 Length1/2/3、Interval1/2/3 ---
    #     def _is_dyn_type(t: str) -> bool:
    #         return bool(re.fullmatch(r'(Length|Interval)\d+', t))

    #     # 若是动态编号类型，自动注册到 S.NODE_TYPES，避免断言失败
    #     if type not in S.NODE_TYPES and _is_dyn_type(type):
    #         S.NODE_TYPES.add(type)
            
    #     assert type in S.NODE_TYPES, f"未知节点类型: {type}"
        
    #     # 检查已有节点
    #     for nid, data in self.G.nodes(data=True):
    #         if data.get("type") != type:
    #             continue
    #         # 如果已有相同类型节点
    #         if value is None:
    #             return nid  # 无值节点直接复用
    #         if data.get("value") == value:
    #             return nid  # 相同值的节点直接复用
    #         # 特殊情况：已有节点无值，但新节点有值 → 更新值
    #         if data.get("value") is None:
    #             self.G.nodes[nid]["value"] = value
    #             return nid 

    #     # 否则创建新节点
    #     # assert type in S.NODE_TYPES
    #     nid = f"{type}_{uuid.uuid4().hex[:4]}"
    #     self.G.add_node(nid, type=type, value=value, **attrs)
    #     self.last_map[type] = nid
        
    #     return nid
    
    # def add_edge(self, uType, vType, *, type, op=None):
    #     """
    #     uType / vType 可以是“节点类型”或已知节点 id。
    #     - 如果是类型，就从 last_map 取最近节点。
    #     - 如果取不到，说明调用顺序不对，直接抛出易懂的异常。
    #     """
    #     # ---- 把类型转换成 id ----
    #     u = self.last_map.get(uType, uType)   # 若 uType 本身就是 id，不影响
    #     v = self.last_map.get(vType, vType)

    #     if u not in self.G.nodes or v not in self.G.nodes:
    #         raise ValueError(
    #             f"add_edge: 先 add_node，再连边；缺失节点 -> "
    #             f"{uType if u not in self.G.nodes else ''} "
    #             f"{vType if v not in self.G.nodes else ''}".strip()
    #         )

    #     self.G.add_edge(u, v, type=type, op=op)

    # # 设置图的模式和主题  topic: 题类，mode: 模式
    # def set_pattern(self, topic, mode, *, override=False):
    #     """写入 topic/mode；若 override=False 且已存在，则保持原值"""
    #     assert topic in S.PAT_TOPIC, "未知 topic"
    #     assert mode  in S.PAT_MODE[topic], "未知 mode"

    #     if override or ("topic" not in self.G.graph):
    #         self.G.graph.update(topic=topic, mode=mode)

    # def _resolve_ref(self, ref: str) -> str:
    #     """把“类型名”或“节点id”解析为实际节点id。
    #     支持 Length/Interval 这类基类名，自动回退到最近出现的同家族编号类型。"""
    #     # 若是现成的节点 id
    #     if ref in self.G.nodes: return ref
    #     # 先试 last_map 的直取
    #     nid = self.last_map.get(ref)
    #     if nid in self.G.nodes: return nid
    #     # 再做基类回退：Length -> 最近的 Length 或 Length\d+
    #     base_families = {"Length", "Interval", "Width", "Height"}
    #     if ref in base_families:
    #         # 从图里找该家族的最后一个（按加入顺序无法保证，用一次扫描兜底）
    #         cand = [nid for nid, d in self.G.nodes(data=True)
    #                 if d.get("type") == ref or str(d.get("type", "")).startswith(ref)]
    #         if cand:
    #             return cand[-1]  # 取最后一个
    #     raise ValueError(f"_resolve_ref: 无法解析引用 '{ref}'，请先 add_node 再连边。")

    def _resolve_ref(self, ref: str) -> str:
            if ref in self.G.nodes: return ref
            nid = self.last_map.get(ref)
            if nid and nid in self.G.nodes: return nid
            # 回退：Length -> Length1/Length2...
            for base in ["Length", "Interval", "Width", "Height"]:
                if ref == base:
                    # 找属于该族的最后一个
                    cands = [n for n, d in self.G.nodes(data=True) if str(d.get("type")).startswith(base)]
                    if cands: return cands[-1]
            raise ValueError(f"_resolve_ref: 无法解析引用 '{ref}'")
    
    # 创建动态编号时，同时更新“基类”的 last_map，便于 add_edge 用基类名引用
    def add_node(self, *, type, value=None, **attrs):
            # ... (前面的代码保持不变: 动态类型处理等) ...
            def _is_dyn_type(t: str) -> bool:
                return bool(re.fullmatch(r'(Length|Interval)\d+', t))

            if type not in S.NODE_TYPES and _is_dyn_type(type):
                S.NODE_TYPES.add(type)

            assert type in S.NODE_TYPES, f"未知节点类型: {type}"

            # 检查已有节点
            for nid, data in self.G.nodes(data=True):
                if data.get("type") != type: continue
                
                # 判断值是否匹配 (None 匹配 None, 具体值匹配具体值)
                if data.get("value") == value:
                    # 【修复核心 Bug】：找到已有节点时，更新/合并新的属性（如 role）
                    if attrs: self.G.nodes[nid].update(attrs)
                    return nid
                
                # 特殊情况：已有节点无值，但新节点有值 → 更新值和属性
                if data.get("value") is None and value is not None:
                    self.G.nodes[nid]["value"] = value
                    if attrs: self.G.nodes[nid].update(attrs)
                    return nid 

            # 否则创建新节点
            nid = f"{type}_{uuid.uuid4().hex[:4]}"
            self.G.add_node(nid, type=type, value=value, **attrs)
            self.last_map[type] = nid

            # # ... (后面的代码保持不变: 处理动态类型引用) ...
            # m = re.fullmatch(r'(Length|Interval)(\d+)', type)
            # if m:
            #     base = m.group(1)
            #     self.last_map[base] = nid

            # 更新基类指针
            m = re.fullmatch(r'(Length|Interval|Width|Height)(\d+)', type)
            if m:
                self.last_map[m.group(1)] = nid
            
            return nid

    # 修改 add_edge：用 _resolve_ref() 解析两端
    # def add_edge(self, uType, vType, *, type, op=None):
    #     u = self._resolve_ref(uType)
    #     v = self._resolve_ref(vType)
    #     if u not in self.G.nodes or v not in self.G.nodes:
    #         raise ValueError(
    #             f"add_edge: 先 add_node，再连边；缺失节点 -> "
    #             f"{uType if u not in self.G.nodes else ''} "
    #             f"{vType if v not in self.G.nodes else ''}".strip()
    #         )
    #     self.G.add_edge(u, v, type=type, op=op)

    def add_edge(self, uType, vType, *, type, op=None):
            u = self._resolve_ref(uType)
            v = self._resolve_ref(vType)
            self.G.add_edge(u, v, type=type, op=op)

    def set_pattern(self, topic, mode, *, override: bool = False,
                    canonicalize: bool = True, validate: bool = True):
        """
        设置题图的 (topic, mode)。

        - 保留你原来的行为：尊重 lock_mode，支持 override 覆盖。
        - 先做别名归一（canonicalize=True），再做枚举校验（validate=True）。
        - 记录 mode_raw 便于排查（保存调用时传入的“原始”mode）。
        """
        # 先做别名归一，再断言校验（避免在归一前被 assert 卡住）
        original_mode = mode
        if canonicalize:
            mode = _canonical_mode(topic, mode)

        # —— 校验 ——
        assert topic in S.PAT_TOPIC, f"未知 topic: {topic}"
        # assert mode  in S.PAT_MODE[topic], f"未知 mode: {mode}（原始: {original_mode}）" # 暂缓强校验，允许中间状态

        # —— 尊重 lock_mode —— 
        if self.G.graph.get("lock_mode") and not override:
            # 被规则锁定时不改
            return

        # —— 写入，并记录原始模式值 —— 
        self.G.graph.update(topic=topic, mode=mode, mode_raw=original_mode)

    # 检查是否有节点，type 和 value 都可以是 None
    def has_node(self, *, type=None, value=None):
        """
        检查图中是否存在某类节点。
        - type: 节点类型，如 "TreeCnt"。
        - value:
            - None  -> 只判断 type 是否存在。
            - True  -> 判断 type 是否存在且有非 None 的 value。
            - 其他值 -> 判断 type 是否存在且 value 等于该值。
        """        
        for _, data in self.G.nodes(data=True):
            if type is not None and data.get("type") != type: continue
            if value is not None:
                if value is True and data.get("value") is None: continue
                elif value is not True and data.get("value") != value: continue
            return True
        return False

    # def normalize_mode_by_knowns(self):
    #     """
    #     根据已知节点，把容易混淆的 mode 再校正一次。
    #     - 闭环：loop_closed  vs loop_closed_distance
    #     - 两端：both_ends_quantity vs both_ends_distance
    #     （若 lock_mode=True 则不改）
    #     """
    #     G = self.G
    #     topic = G.graph.get("topic")
    #     mode  = G.graph.get("mode")
    #     if not topic or topic != "tree":
    #         return

    #     if G.graph.get("lock_mode"):
    #         return

    #     def has(type_, need_value=False):
    #         return self.has_node(type=type_, value=need_value)

    #     # —— 闭环：根据已知/未知进行规整 —— 
    #     if mode in (None, "loop_closed", "loop_closed_distance"):
    #         if has("TreeCnt", True) and has("Interval", True) and not has("Length", True):
    #             # 已知 Z、I；未知 L：多为 “问周长多少米”
    #             self.set_pattern("tree", "loop_closed_distance")
    #         elif has("Length", True) and has("Interval", True) and not has("TreeCnt", True):
    #             # 已知 L、I；未知 Z：多为 “问有多少棵”
    #             self.set_pattern("tree", "loop_closed")

    #     # —— 两端模式：根据是否知道 TreeCnt 决定求什么 —— 
    #     if mode in (None, "both_ends_quantity", "both_ends_distance"):
    #         if has("TreeCnt", True):
    #             self.set_pattern("tree", "both_ends_distance")
    #         else:
    #             self.set_pattern("tree", "both_ends_quantity")
    
    # def normalize_mode_by_knowns(self):
    #     """
    #     根据已知节点，把容易混淆的 mode 再校正一次。
    #     - 闭环：loop_closed  vs loop_closed_distance
    #     - 两端：both_ends_quantity vs both_ends_distance
    #     （若 lock_mode=True 则不改）
    #     """
    #     G = self.G
    #     topic = G.graph.get("topic")
    #     mode  = G.graph.get("mode")
    #     if not topic or topic != "tree":
    #         return

    #     if G.graph.get("lock_mode"):
    #         return

    #     def has(type_, need_value=False):
    #         return self.has_node(type=type_, value=need_value)

    #     # —— 闭环：根据已知/未知进行规整 —— 
    #     if mode in (None, "loop_closed", "loop_closed_distance", "loop_closed_count"):
    #         if has("TreeCnt", True) and has("Interval", True) and not has("Length", True):
    #             # 已知 Z、I；未知 L：多为 “问周长多少米”
    #             self.set_pattern("tree", "loop_closed_distance")
    #         elif has("Length", True) and has("Interval", True) and not has("TreeCnt", True):
    #             # 已知 L、I；未知 Z：多为 “问有多少棵”
    #             self.set_pattern("tree", "loop_closed")

    #     # —— 两端模式：根据是否知道 TreeCnt 决定求什么 —— 
    #     if mode in (None, "both_ends_quantity", "both_ends_distance"):
    #         if has("TreeCnt", True):
    #             self.set_pattern("tree", "both_ends_distance")
    #         else:
    #             self.set_pattern("tree", "both_ends_quantity")

    #     # —— 兜底：统一把别名规范为模板库用的规范名（防止有人绕过 set_pattern 直接写 graph["mode"]）——
    #     topic = self.G.graph.get("topic")
    #     mode  = self.G.graph.get("mode")
    #     if topic and mode:
    #         self.G.graph["mode_raw"] = self.G.graph.get("mode_raw", mode)
    #         self.G.graph["mode"] = _canonical_mode(topic, mode)
    
    def _ensure_topic_if_tree(self):
        """见到典型节点就把 topic 兜底成 tree（不强制写 mode）。"""
        if self.G.graph.get("topic"): return
        for t in ("Length", "Interval", "TreeCnt", "SegmentCnt"):
            if self.has_node(type=t):  # 你已有的工具
                # 只写 topic，先不动 mode，避免断言
                self.G.graph["topic"] = "tree"
                break

    def _autowire_divides(self):
        """有 Length 和 Interval 就兜底补一条 divides（若不存在）。"""
        L = self.last_of("Length")
        I = self.last_of("Interval")
        if L and I and not self.G.has_edge(L, I):
            self.G.add_edge(L, I, type="divides", op=None)

    def normalize_mode_by_knowns(self):
        """
        根据已知量推断/细化模式。
        【关键修复】：只有当模式已经是 loop 类，或者模式为空但有强证据（如 target）时才推断。
        绝对不能把 "已知Z, I 求 L" 盲目推断为 Loop，因为 Linear 也是这个结构。
        """
        G = self.G
        if G.graph.get("lock_mode"): return

        self._ensure_topic_if_tree()
        topic = G.graph.get("topic")
        mode  = G.graph.get("mode")
        
        # ——（可保留你原有的判定分支，这里给最常用的两个）——
        topic = self.G.graph.get("topic")
        mode  = self.G.graph.get("mode")
        
        if topic == "tree":
            def has(type_, need_value=False):
                return self.has_node(type=type_, value=need_value)
            
            # # 闭环：已知 L、I 且 Z 未知 → 多为“问有多少棵”
            # if mode in (None, "loop_closed", "loop_closed_distance", "loop_closed_count"):
            #     if has("Length", True) and has("Interval", True) and not has("TreeCnt", True):
            #         self.set_pattern("tree", "loop_closed")
            #     elif has("TreeCnt", True) and has("Interval", True) and not has("Length", True):
            #         self.set_pattern("tree", "loop_closed_distance")  # 归一后仍是 loop_closed

            # # 直线一侧、两端都栽（或“从头到尾/从一头开始”常落此类）：
            # if mode in (None, "both_ends_quantity", "both_ends_distance"):
            #     # 只要有 L、I，就先归到 quantity（问棵树）；若反过来问长度，后续 unknown 会选 L
            #     if has("Length", True) and has("Interval", True):
            #         self.set_pattern("tree", "both_ends_quantity")

            # 1. 如果模式已经是 Loop 相关，进行细化
            if mode in ("loop_closed", "loop_closed_distance", "loop_closed_count"):
                # 已知 Z、I；未知 L -> 归一化为 loop_closed
                if has("TreeCnt", True) and has("Interval", True) and not has("Length", True):
                    self.set_pattern("tree", "loop_closed_distance") 
                # 已知 L、I；未知 Z -> 归一化为 loop_closed
                elif has("Length", True) and has("Interval", True) and not has("TreeCnt", True):
                    self.set_pattern("tree", "loop_closed")
            
            # 2. 如果模式未知，且有典型的“两端”特征（通常通过 Hook 里的正则已捕获，这里兜底）
            # 注意：千万不要在这里把 (Z, I) -> Loop，因为它更可能是 Linear
            if mode is None:
                if has("Length", True) and has("Interval", True):
                     # L, I 已知 -> 默认为两端植树（Linear），因为这是最基础模型
                     self.set_pattern("tree", "both_ends_quantity")

        # —— 归一化：统一做一次模式别名归一 + 兜底连边 —— 
        topic = self.G.graph.get("topic")
        mode  = self.G.graph.get("mode")
        if topic and mode:
            self.G.graph["mode"] = _canonical_mode(topic, mode)
        # self._autowire_divides()

    def finalize(self):
        """构图收尾：再保守归一一次 + 再兜底连边一次。"""
        topic = self.G.graph.get("topic")
        mode  = self.G.graph.get("mode")
        if topic and mode:
            self.G.graph["mode"] = _canonical_mode(topic, mode)
        self._autowire_divides()
        return self.G