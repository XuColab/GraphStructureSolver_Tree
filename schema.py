# schema.py 统一枚举表，定义了图结构求解器中使用的节点类型、边类型和操作符

# 节点类型
NODE_TYPES = {
    # 植树
    "Length", "Interval", "SegmentCnt", "TreeCnt", 
    "Width", "Height", # 矩形长宽
    # "CountDiff", # 两种方案树数之差
    "Diff", # 两端数之差

    # 新增：多段直线
    "Length1", "Interval1", "Length2",
    
    # 行程
    "Speed", "Time",
    
    # 工程
    "Rate", "Work",
    
    # 运算中间节点
    "Op"
}

# 边类型
EDGE_TYPES = {
    "divides", "adds", "subs", "multiplies",
    "tree_relation",     # 植树
    "work_relation"      # 工程
}

OP_ENUM = {"ADD","SUB","PLUS1","MINUS1","EQUAL", "FLOOR_DIV", "X4_CORNERS"}

PAT_TOPIC = {"tree","trip","work"}
PAT_MODE  = {
    "tree": {"none_end_quantity", "one_end_quantity", "both_ends_quantity", "both_ends_distance", "rectangle_closed", "linear", "both_ends_compare", "multi_segment", "loop_closed", "adjacent_share", "two_sides_wrap", "one_end_distance", "none_end_distance", "rectangle_nocorner","rectangle_diffI_closed", "rectangle_diffI_nocorner", "both_ends_two_sides", "one_end_from_segments", "none_end_from_segments", "multi_segment_dedup", "loop_closed_distance"},
    "trip": {"join","chase","round"},
    "work": {"coop","solo","split"}
}