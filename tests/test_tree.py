import sys, pathlib, pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from GraphStructureSolver_Tree.run_demo import solve

# def test_both_ends():
#     assert solve("小路长120米，两端都植树，间隔15米，共多少棵？")['Z']==9

# def test_none_end():
#     assert solve("小路长90米，两端不植，每隔15米种树，要几棵？")['Z']==5

# def test_one_end():
#     assert solve("长100米，只在一端植，间隔10米一棵，共多少段？")['N']==10

@pytest.mark.parametrize("q, ans", [
    ("一条小路长120米，路两端都植树，每隔15米种一棵，一共要种多少棵？", 9),
    ("一条小路长90米，两端不植树，每隔15米栽一棵，要栽多少棵？", 5),
    ("长 100 米的小路，只在一端植树，间隔 10 米一棵，一共多少段？", 10),
])
def test_tree(q, ans):
    res = solve(q)
    assert list(res.values())[0] == ans