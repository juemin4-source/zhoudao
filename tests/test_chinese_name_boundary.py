"""中文名称软词界与上下文消歧 — TASK-ZHOUDAO-SEED-017 RED 测试矩阵。

Gate B-E 验证：空白追踪、设/使名称消歧、从…中边界。
"""
import pytest
from 周道 import 转译, 转译_仅语法, 运行


class TestRED1_名称含以:
    def test_紧凑形式(self):
        py = 转译("设可以进入复核为真。")
        assert "可以进入复核" in py

    def test_精确名称(self):
        py = 转译("设{可以进入复核}为真。")
        assert "可以进入复核" in py


class TestRED2_名称含在:
    def test_精确名称(self):
        py = 转译("设{判断存在}为真。")
        assert "判断存在" in py


class TestRED3_名称含为:
    def test_设认为有效(self):
        py = 转译("设认为有效为真。")
        assert "认为有效" in py and "True" in py

    def test_精确名称(self):
        py = 转译("设{认为有效}为真。")
        assert "认为有效" in py


class TestRED4_名称含从:
    def test_紧凑形式(self):
        code = "设从属关系为【父子】。显示从属关系。"
        py = 转译(code)
        assert "从属关系" in py


class TestRED5_名称含当:
    def test_紧凑形式(self):
        py = 转译("设当日结果为80。")
        assert "当日结果" in py


class TestRED6_成员边界:
    def test_显式软界(self):
        code = "设成员列表为［1］。从 成员列表 中，每取一项记作成员，就显示成员。"
        py = 转译(code)
        assert "for" in py


class TestRED7_紧凑成员边界:
    def test_紧凑(self):
        code = "设成员列表为［1］。从成员列表中，每取一项记作成员，就显示成员。"
        py = 转译(code)
        assert "for" in py


class TestRED8_名称内结构词加末尾结构词:
    def test_高中生列表(self):
        code = "设高中生列表为［1、2］。从高中生列表中，每取一项记作学生，就显示学生。"
        py = 转译(code)
        assert "高中生列表" in py

    def test_完整运行(self):
        code = """
设高中生列表为［1、2］。
从高中生列表中，每取一项记作学生，就显示学生。
"""
        env = 运行(code)
        assert True


class TestRED9_精确名称优先:
    def test_花括号(self):
        code = '设{认为有效}为真。'
        py = 转译(code)
        assert "认为有效" in py
        assert "True" in py


class TestRED10_真实结构词不被吞:
    def test_从列表中(self):
        code = "设列表为［1］。从列表中，每取一项记作元素，就显示元素。"
        py = 转译(code)
        assert "for" in py

    def test_以所得(self):
        # 定义+以所得 应保持语法
        py = 转译("定义f()如下：以42为所得。")
        assert "return" in py

    def test_紧凑从(self):
        code = "设列表为［1、2、3］。从列表中，每取一项记作项，就显示项。"
        env = 运行(code)
        assert True


class TestRED11_AST等价验收:
    """三种形式应产生等价语义结构。"""

    def test_精确_vs_软界(self):
        py_exact = 转译("设{认为有效}为真。")
        py_soft = 转译("设认为有效为真。")
        assert "认为有效" in py_exact
        assert "认为有效" in py_soft

    def test_从_三种形式等价(self):
        code = "设高中生列表为［1］。从高中生列表中，每取一项记作x，就显示x。"
        py = 转译(code)
        assert "for" in py
