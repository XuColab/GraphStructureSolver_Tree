核心思路回顾（与现有植树题对齐）
节点（node）：携带数值与单位的实体，如 Length/Speed/Time 等
边（edge）：可选（行程题里我们用极简边，主要靠公式表达关系）
模板（subgraph template）：
    列出需要的节点类型
    用 formula 写“物理约束”（实质是方程/方程组）
    用 unknowns 指定要解的量
求解：solver.solve_equation(tpl, mapping, G) 用 SymPy 把 formula → 方程，代入节点数值 → 解出 unknowns

> 行程题里，“物理约束”全部写在模板的 formula 数组即可，比植树题的 tree_relation 边更简洁

4 条物理约束 = 模板里的公式
单主体位移约束
    中文：距离 = 速度 × 时间（可带起始间距正负项）
    公式：Distance == SpeedA*TimeA (+/- StartDistanceGap)
    使用：一人（或一车）相对某参考点运动，或同向追及里给领先距离

同时性/记时对齐
    中文：两人的有效行驶时间的关系（可能有先后出发时间差）
    公式：TimeA == TimeB (+/- StartGapTime)
    使用：非同时出发；或“早出发/晚出发 △t”

相向相遇
    中文：总路程 = 两人各自位移之和（同一段共同时间）
    公式：Distance_total == SpeedA*Time + SpeedB*Time
    使用：相向而行/迎面而行，相遇时刻

同向追及
    中文：追及所需克服的“相对位移” = 相对速度 × 追及时间
    公式：Distance_gap == (Speed_fast - Speed_slow) * Time_catch
    使用：同向快追慢，给领先距离或落后距离