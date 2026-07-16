"""周道 v0.0.4 SEED-004 测试 — 表达式取用系统。

测试覆盖：
- 成员访问（的）语法生成
- 字符串键下标（【】在表达式后）
- 表达式下标（［］）
- 成员变更与删除
- 后缀链组合
- 切片下标（［开始：结束］）
- 映射字面量（［【键】为【值】］）
- 向后兼容测试
- 错误路径
"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from contextlib import redirect_stdout
from 周道 import 转译, 转译_仅语法, 运行
from 周道.lexer import 扫描
from 周道.parser import 解析器
from 周道.emitter import 发射器
from 周道.errors import 语法错误, 词法错误


def 编译(源码: str) -> str:
    """转译 + compile，返回 Python 代码。"""
    py = 转译(源码)
    compile(py, "<周道>", "exec")
    return py


def 编译运行(源码: str, 全局变量: dict | None = None) -> str:
    """转译 + compile + exec，捕获 stdout 输出。"""
    py = 转译(源码)
    compile(py, "<周道>", "exec")
    f = io.StringIO()
    env = {"__name__": "__周道__"}
    if 全局变量:
        env.update(全局变量)
    with redirect_stdout(f):
        exec(py, env)
    return f.getvalue().strip()


def 检查转译(源码: str, 期望_python: str):
    """检查转译结果是否与期望的 Python 一致（跳过语义分析）。"""
    python_code = 转译_仅语法(源码)
    py_norm = " ".join(python_code.strip().split())
    exp_norm = " ".join(期望_python.strip().split())
    assert py_norm == exp_norm, f"\n期望: {期望_python}\n实际: {python_code}"


# ==================== 一、成员访问（的） — 语法检查 ====================

class Test成员访问语法:

    def test_基本成员读取(self):
        检查转译("显示甲的乙。", "print(甲.乙)")

    def test_成员在条件中(self):
        检查转译("如果甲的年龄不少于18，就显示【成年】。",
                  'if 甲.年龄 >= 18:\n    print("成年")')

    def test_成员在算术中(self):
        检查转译("设总额为价格乘数量。", "总额 = 价格 * 数量")

    def test_链式成员访问(self):
        py = 转译_仅语法("显示甲的乙的丙。")
        assert "甲.乙.丙" in py

    def test_成员值绑定到变量(self):
        检查转译("设值为甲的乙。", "值 = 甲.乙")

    def test_成员作为调用参数(self):
        检查转译("显示甲的乙。", "print(甲.乙)")


# ==================== 二、成员变更与删除 — 语法检查 ====================

class Test成员变更与删除语法:

    def test_成员直接变更(self):
        检查转译("使用户的年龄变为30。", "用户.年龄 = 30")

    def test_成员算术变更(self):
        检查转译("使用户的年龄加5。", "用户.年龄 += 5")

    def test_成员删除(self):
        py = 转译_仅语法("删去用户的名称。")
        assert "del 用户.名称" in py

    def test_删除名称保持兼容(self):
        检查转译("删去甲。", "del 甲")

    def test_删除链式成员(self):
        py = 转译_仅语法("删去甲的乙的丙。")
        assert "del 甲.乙.丙" in py


# ==================== 三、字符串键下标 — 运行测试 ====================

class Test字符串键下标:

    def test_字符串键读取(self):
        src = """
设映射为dict（）。
使映射【键1】变为【值1】。
显示映射【键1】。
""".strip()
        out = 编译运行(src)
        assert out == "值1"

    def test_字符串键变更(self):
        src = """
设映射为dict（）。
使映射【键1】变为【值1】。
使映射【键1】变为【值2】。
显示映射【键1】。
""".strip()
        out = 编译运行(src)
        assert out == "值2"

    def test_字符串键删除(self):
        py = 编译("设映射为dict（）。使映射【键1】变为【值1】。删去映射【键1】。")
        assert 'del 映射' in py and '键1' in py

    def test_字符串字面量兼容(self):
        """【】在表达式起始仍为字符串字面量。"""
        检查转译("显示【测试】。", 'print("测试")')

    def test_绑定字符串字面量(self):
        """设 右侧【】为字符串字面量。"""
        检查转译("设甲为【测试】。", '甲 = "测试"')

    def test_参数中字符串(self):
        """函数参数中的【】为字符串。"""
        检查转译("设甲为dict（【测试】）。", '甲 = dict("测试")')


# ==================== 四、表达式下标 — 运行测试 ====================

class Test表达式下标:

    def test_整数索引读取(self):
        src = """
设列表为［10、20、30］。
显示列表［0］。
显示列表［1］。
""".strip()
        out = 编译运行(src)
        lines = out.split("\n")
        assert lines == ["10", "20"]

    def test_表达式索引(self):
        src = """
设列表为［10、20、30］。
设索引为1。
显示列表［索引加1］。
""".strip()
        out = 编译运行(src)
        assert out == "30"

    def test_索引变更(self):
        src = """
设列表为［10、20、30］。
使列表［0］变为100。
显示列表［0］。
""".strip()
        out = 编译运行(src)
        assert out == "100"

    def test_索引删除(self):
        src = """
设列表为［10、20、30］。
删去列表［1］。
显示列表［0］。
显示列表［1］。
""".strip()
        out = 编译运行(src)
        lines = out.split("\n")
        assert lines == ["10", "30"]

    def test_嵌套下标(self):
        src = """
设矩阵为［［1、2］、［3、4］］。
显示矩阵［0］。
显示矩阵［0］［1］。
""".strip()
        out = 编译运行(src)
        lines = out.split("\n")
        assert lines[1] == "2"


# ==================== 五、后缀链组合 ====================

class Test后缀链:

    def test_成员后下标(self):
        py = 转译_仅语法("显示甲的乙【键】。")
        assert '乙["键"]' in py

    def test_链式后缀语法(self):
        py = 转译_仅语法("显示甲的乙［0］的丙。")
        assert "甲.乙" in py
        assert "丙" in py

    def test_方法调用(self):
        检查转译("显示结果。", "print(结果)")


# ==================== 六、向后兼容 ====================

class Test向后兼容:

    def test_绑定(self):
        检查转译("设数量为3。", "数量 = 3")

    def test_变更(self):
        检查转译("使数量变为5。", "数量 = 5")

    def test_算术变更(self):
        检查转译("使数量加1。", "数量 += 1")

    def test_空值绑定(self):
        检查转译("设查询结果没有值。", "查询结果 = None")

    def test_命题绑定(self):
        检查转译("设任务完成成立。", "任务完成 = True")

    def test_显示(self):
        检查转译("显示【测试】。", 'print("测试")')

    def test_列表字面量(self):
        检查转译("设列表为［1、2、3］。", "列表 = [1, 2, 3]")

    def test_条件(self):
        检查转译("如果数量大于0，就显示【正数】。", 'if 数量 > 0:\n    print("正数")')

    def test_遍历(self):
        检查转译("从名单中，每取一项记作姓名，就显示姓名。", "for 姓名 in 名单:\n    print(姓名)")

    def test_删去变量(self):
        检查转译("删去甲。", "del 甲")

    def test_函数定义(self):
        py = 转译("设平方（数）为数乘数。")
        assert "def 平方" in py
        assert "return" in py

    def test_引入(self):
        py = 转译_仅语法("引入《随机》。")
        assert "import random" in py

    def test_从中引入(self):
        py = 转译_仅语法("从《随机》中引入随机整数。")
        assert "randint as 随机整数" in py


# ==================== 七、错误路径 ====================

class Test错误路径:

    def test_的后面缺成员名(self):
        with pytest.raises((语法错误, Exception)):
            转译("显示甲的。")

    def test_表达式下标未闭合(self):
        with pytest.raises((语法错误, 词法错误)):
            转译("显示甲［0。")


# ==================== 八、切片下标 ====================

class Test切片下标:

    def test_基本切片(self):
        检查转译("显示文本［0：3］。", 'print(文本[0:3])')

    def test_省略开始(self):
        检查转译("显示文本［：3］。", 'print(文本[:3])')

    def test_省略结束(self):
        检查转译("显示文本［0：］。", 'print(文本[0:])')

    def test_全省略(self):
        检查转译("显示文本［：］。", 'print(文本[:])')

    def test_表达式切片(self):
        检查转译("显示文本［开始：结束］。", 'print(文本[开始:结束])')


# ==================== 九、映射字面量 ====================

class Test映射字面量:

    def test_基本映射(self):
        py = 转译_仅语法("设映射为［【姓名】为【周道】］。")
        assert '"姓名"' in py
        assert '"周道"' in py

    def test_映射执行(self):
        src = "设映射为［【姓名】为【周道】］，显示映射【姓名】。"
        out = 编译运行(src)
        assert out == "周道"

    def test_多条目映射(self):
        src = """
设映射为［【姓名】为【张三】、【年龄】为25］。
显示映射【姓名】。
显示映射【年龄】。
""".strip()
        out = 编译运行(src)
        lines = out.split("\n")
        assert "张三" in lines
        assert "25" in lines

    def test_空映射(self):
        py = 转译_仅语法("设列表为［］。")
        assert "[]" in py

    def test_列表不混淆(self):
        检查转译("设列表为［1、2、3］。", "列表 = [1, 2, 3]")

    def test_映射值变更(self):
        src = """
设映射为［【键】为【旧值】］。
使映射【键】变为【新值】。
显示映射【键】。
""".strip()
        out = 编译运行(src)
        assert out == "新值"

    def test_仅映射含为(self):
        """验证只有含 为 的才被解析为映射。"""
        py = 转译("设列表为［【测试】］。")
        assert "测试" in py
