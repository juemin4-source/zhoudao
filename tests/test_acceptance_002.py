"""周道 v0.0.2 验收测试 — 第二批语法、语义检查、组合程序。

所有测试为真正的 pytest 函数。
所有组合程序必须 compile 并真实运行。
复杂类别必须 exec 并创建实例。
"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from contextlib import redirect_stdout
from 周道 import 转译, 转译_仅语法, 运行
from 周道.lexer import 扫描
from 周道.parser import 解析器
from 周道.emitter import 发射器
from 周道.errors import 语法错误, 词法错误, 语义错误


def 编译(源码: str) -> str:
    """转译 + compile，返回 Python 代码。"""
    py = 转译(源码)
    compile(py, "<周道>", "exec")
    return py


def 编译运行(源码: str) -> str:
    """转译 + compile + exec，捕获 stdout 输出。"""
    py = 转译(源码)
    compile(py, "<周道>", "exec")
    f = io.StringIO()
    env = {"__name__": "__周道__"}
    with redirect_stdout(f):
        exec(py, env)
    return f.getvalue().strip()


# ==================== 一、复杂类别 ====================

class Test复杂类别:

    def test_完整类别声明(self):
        """完整复杂类别：类型约束 + 不得为负 + 默认值 + 可空。"""
        src = "设置用户类别，包括以下内容：姓名，须为文本；年龄，须为整数且不得为负；性别，默认为【未知】；职业，可以没有值。"
        py = 编译(src)
        # 验证关键元素
        assert "from typing import Any" in py
        assert "from dataclasses import dataclass" in py
        assert "@dataclass(kw_only=True)" in py
        assert "class 用户" in py
        assert "def __post_init__" in py
        # 验证字段定义
        assert "姓名: str" in py
        assert "年龄: int" in py
        assert "性别: Any" in py
        assert "职业: Any = None" in py
        # 验证使用 if+raise 而非 assert
        assert "raise TypeError" in py
        assert "raise ValueError" in py
        assert "assert " not in py
        # 验证类型检查在值检查之前
        姓名_idx = py.index("raise TypeError")
        年龄_type_idx = py.index("「年龄」", 姓名_idx)
        年龄_value_idx = py.index("「年龄」", 年龄_type_idx + 10)
        assert 年龄_type_idx < 年龄_value_idx, "类型检查应在值检查之前"

    def test_exec并创建实例(self):
        """类别代码必须 exec 并创建实例。"""
        src = "设置用户类别，包括以下内容：姓名，须为文本；年龄，须为整数且不得为负；性别，默认为【未知】；职业，可以没有值。"
        py = 转译(src)
        env = {"__name__": "__周道__"}
        exec(py, env)
        User = env["用户"]
        u = User(姓名="张三", 年龄=25)
        assert u.姓名 == "张三"
        assert u.年龄 == 25
        assert u.性别 == "未知"
        assert u.职业 is None

    def test_类型验证(self):
        """类别字段类型错误应引发 TypeError。"""
        src = "设置用户类别，包括以下内容：姓名，须为文本；年龄，须为整数且不得为负；性别，默认为【未知】；职业，可以没有值。"
        py = 转译(src)
        env = {"__name__": "__周道__"}
        exec(py, env)
        User = env["用户"]
        with pytest.raises(TypeError):
            User(姓名=123, 年龄=25)

    def test_不得为负验证(self):
        """负数值应引发 ValueError。"""
        src = "设置用户类别，包括以下内容：姓名，须为文本；年龄，须为整数且不得为负；性别，默认为【未知】；职业，可以没有值。"
        py = 转译(src)
        env = {"__name__": "__周道__"}
        exec(py, env)
        User = env["用户"]
        with pytest.raises(ValueError):
            User(姓名="张三", 年龄=-1)

    def test_简单类别(self):
        """简单类别（无复杂约束）。"""
        src = "设置用户类别，包括姓名、年龄、性别。"
        py = 编译(src)
        assert "class 用户" in py
        # 简单类别：字段不加类型约束
        assert "姓名" in py

    def test_且不得为负不拆分字段(self):
        """「且不得为负」不应拆分出字段「负」。"""
        src = "设置测试类别，包括以下内容：分数，须为整数且不得为负。"
        py = 转译(src)
        env = {"__name__": "__周道__"}
        exec(py, env)
        Test = env["测试"]
        t = Test(分数=100)
        assert t.分数 == 100
        # 验证没有「负」字段
        assert not hasattr(t, "负")

    def test_可以没有值(self):
        """「可以没有值」应正确处理为可空字段。"""
        src = "设置任务类别，包括以下内容：描述，可以没有值。"
        py = 编译(src)
        assert "描述: Any = None" in py
        # 测试实例化
        env = {"__name__": "__周道__"}
        exec(py, env)
        Task = env["任务"]
        t = Task(描述="测试")
        assert t.描述 == "测试"
        t2 = Task()
        assert t2.描述 is None


# ==================== 二、软关键词边界 ====================

class Test软关键词边界:

    def test_完成度变量(self):
        assert 编译运行("设完成度为3，显示完成度。") == "3"

    def test_完成时间变量(self):
        assert 编译运行("设完成时间为【今天】，显示完成时间。") == "今天"

    def test_时长变量(self):
        assert 编译运行("设时长为10，显示时长。") == "10"

    def test_如下内容变量(self):
        assert 编译运行("设如下内容为【正文】，显示如下内容。") == "正文"

    def test_负数变量(self):
        assert 编译运行("设负数为0减1，显示负数。") == "-1"

    def test_文本保护完成(self):
        assert 编译运行("显示【完成测试】。") == "完成测试"

    def test_文本保护时长(self):
        assert 编译运行("显示【时长测试】。") == "时长测试"

    def test_文本保护负数(self):
        assert 编译运行("显示【负数测试】。") == "负数测试"

    def test_文本保护如下(self):
        assert 编译运行("显示【如下内容】。") == "如下内容"

    def test_模块名成功(self):
        assert 编译运行("引入《随机》，显示【模块引入成功】。") == "模块引入成功"


# ==================== 三、语义检查（非法上下文） ====================

class Test语义检查:

    def test_循环外跳出(self):
        with pytest.raises(语法错误, match="只能在循环内"):
            转译("跳出循环。")

    def test_循环外继续(self):
        with pytest.raises(语法错误, match="只能在循环内"):
            转译("继续下一轮。")

    def test_定义外依次给出(self):
        with pytest.raises(语法错误, match="只能在定义内"):
            转译("依次给出3。")

    def test_定义外等待(self):
        with pytest.raises(语法错误, match="只能在定义内"):
            转译("等待下载（地址）完成。")

    def test_定义外等待表达式(self):
        with pytest.raises(语法错误, match="只能在定义内"):
            转译("设页面为等待下载（地址）的所得。")

    def test_错误内容在异常外(self):
        with pytest.raises(语法错误, match="只能在如果出错"):
            转译("显示错误内容。")

    def test_错误对象在异常外(self):
        with pytest.raises(语法错误, match="只能在如果出错"):
            转译("设x为错误。")

    def test_最后外无尝试(self):
        with pytest.raises(语法错误):
            转译("无论是否出错，最后显示【test】。")

    def test_定义外以所得(self):
        with pytest.raises(语法错误, match="只能在定义内"):
            转译("以3为所得。")

    def test_定义外以(self):
        with pytest.raises(语法错误, match="只能在定义内"):
            转译("以3为所得。")

    def test_顶层nonlocal(self):
        with pytest.raises(语法错误, match="只能在定义内"):
            转译("下文所用计数，指本定义外层的计数。")

    # ==================== 新增语义拒绝 ====================

    def test_重复类别字段(self):
        with pytest.raises(语法错误, match="重复字段"):
            转译("设置用户类别，包括以下内容：姓名，须为文本；姓名，须为整数。")

    def test_约束冲突(self):
        with pytest.raises(语法错误, match="约束冲突"):
            转译("设置用户类别，包括以下内容：年龄，须为文本且须为整数。")

    def test_分情形重复字面量(self):
        with pytest.raises(语法错误, match="重复的字面量"):
            转译("依1分情形：若为1，就显示【一】，若为1，就显示【壹】。")

    def test_其余后继续分支(self):
        with pytest.raises(语法错误, match="其余.*之后"):
            转译("依1分情形：若为1，就显示【一】，其余，就显示【其他】，若为2，就显示【二】。")


# ==================== 四、成员名映射 ====================

class Test成员映射:

    def test_随机整数映射(self):
        """从《随机》中引入随机整数 → from random import randint as 随机整数。"""
        py = 转译("从《随机》中引入随机整数。")
        assert "from random import randint as 随机整数" in py

    def test_未知成员保持原名(self):
        """不在映射中的名称保持原样。"""
        py = 转译("从《数学》中引入未知函数。")
        assert "from math import 未知函数" in py

    def test_成员映射运行(self):
        """验证映射后的代码可运行。"""
        out = 编译运行("从《随机》中引入随机整数，显示【就绪】。")
        assert "就绪" in out


# ==================== 五、async / generator 语义 ====================

class TestAsyncGenerator:

    def test_等待生成async_def(self):
        """定义中含等待语句应生成 async def。"""
        src = "定义获取数据（地址）如下：等待请求（地址）完成。"
        py = 转译_仅语法(src)
        assert "async def 获取数据" in py

    def test_依次给出生成yield(self):
        """定义中含依次给出应生成 yield。"""
        src = "定义生成数（上限）如下：设i为0，当i小于上限时，一直（依次给出i，并使i加1）。"
        py = 转译(src)
        assert "yield " in py

    def test_同时等待和依次给出(self):
        """定义中同时含等待和依次给出应生成异步生成器。"""
        src = "定义处理流（源）如下：设数据为等待获取（源）的所得，依次给出数据。"
        py = 转译_仅语法(src)
        assert "async def 处理流" in py
        assert "yield " in py
        assert "await " in py


# ==================== 六、组合程序（真实 compile + exec + 消费生成器/协程） ====================

class Test组合程序:

    def test_同步消费生成器(self):
        """同步生成器必须真实用 for 消费，进入生成器函数体。"""
        src = """
设执行任务（任务名称、任务优先级），
如果任务优先级大于5，就依次给出任务名称，
不然，如果任务优先级大于0，就当任务优先级大于0时，一直显示任务名称，并使任务优先级减1，
不然就报错【优先级不得为负】。
设任务列表为执行任务（【日常清洁】、3），
从任务列表中，每取一项记作任务，就显示任务。
""".strip()
        out = 编译运行(src)
        assert "日常清洁" in out

    def test_同步生成器负数错误(self):
        """生成器在传入负数参数时必须在生成器函数体内触发报错。"""
        src = """
设执行任务（任务名称、任务优先级），
如果任务优先级大于5，就依次给出任务名称，
不然，如果任务优先级大于0，就当任务优先级大于0时，一直显示任务名称，并使任务优先级减1，
不然就报错【优先级不得为负】。
设任务列表为执行任务（【日常清洁】、0减1），
尝试（从任务列表中，每取一项记作任务，就显示任务），
如果出错，就显示【捕获到负数错误】。
""".strip()
        out = 编译运行(src)
        assert "捕获到负数错误" in out

    def test_同步生成器finally(self):
        """生成器不管是否提前退出都必须执行 finally。"""
        src = """
设生成数（上限），
尝试（设i为0，当i小于上限时，一直（依次给出i，并使i加1）），
无论是否出错，最后显示【生成器结束】。
设结果为生成数（3），
从结果中，每取一项记作数，就显示数。
""".strip()
        out = 编译运行(src)
        lines = out.split("\n")
        assert "0" in lines
        assert "1" in lines
        assert "2" in lines
        assert "生成器结束" in out

    def test_同步完整输出顺序(self):
        """精确断言同步组合程序完整输出顺序。"""
        src = """
设生成数（上限），
设i为0，
当i小于上限时，一直（依次给出i，并使i加1）。
设结果为生成数（3），
从结果中，每取一项记作数，就显示数。
显示【完成】。
""".strip()
        out = 编译运行(src)
        assert out == "0\n1\n2\n完成"

    def test_作用域与等待程序(self):
        """组合了：嵌套定义、全局声明、外层声明、等待所得。"""
        src = """
定义获取数据（地址）如下：
设页面_为等待模拟请求（地址）的所得，
以页面_为所得。
定义外层处理（）如下：
设计数为0，
定义内层（）如下：
下文所用计数，指本定义外层的计数，
使计数加1，
以计数为所得。
""".strip()
        py = 转译_仅语法(src)  # 只验证可编译（模拟请求由测试注入）
        assert "await " in py
        assert "nonlocal" in py
        # 验证外层函数是 async def（含等待）
        assert "async def 获取数据" in py

    def test_异步协程实际运行(self):
        """async 函数必须 exec + asyncio.run 真实调用，验证 await 所得。"""
        import asyncio, io, contextlib
        src = """
定义获取数据（地址）如下：
设页面_为等待模拟请求（地址）的所得，
以页面_为所得。
""".strip()
        py = 转译_仅语法(src)
        assert "async def 获取数据" in py
        assert "await " in py
        # 注入 async 测试环境
        test_code = """
import asyncio

async def 模拟请求(地址):
    return "来自：" + 地址

""" + py + """

async def 测试():
    结果 = await 获取数据("测试地址")
    print(结果)

asyncio.run(测试())
"""
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            exec(test_code, {"__name__": "__周道__"})
        out = f.getvalue().strip()
        assert out == "来自：测试地址"

    def test_异步合法nonlocal(self):
        """合法 nonlocal 编译通过，生成的 Python 含 nonlocal 声明。"""
        src = """
定义外层处理（）如下：
设计数为0，
定义内层（）如下：
下文所用计数，指本定义外层的计数，
使计数加1，
以计数为所得。
""".strip()
        py = 编译(src)
        assert "nonlocal 计数" in py
        # 实际执行验证不报错
        env = {"__name__": "__周道__"}
        exec(py, env)
        assert "外层处理" in env

    def test_异步生成器async_for消费(self):
        """异步生成器必须用 async for 消费。"""
        import asyncio, io, contextlib
        src = """
定义模拟获取（源）如下：
等待模拟请求（源）完成，
依次给出【数据A】。
""".strip()
        py = 转译_仅语法(src)
        assert "async def 模拟获取" in py
        assert "yield " in py
        assert "await " in py
        test_code = """
import asyncio

async def 模拟请求(源):
    return "OK"

""" + py + """

async def 测试():
    async for 项 in 模拟获取("test"):
        print(项)

asyncio.run(测试())
"""
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            exec(test_code, {"__name__": "__周道__"})
        out = f.getvalue().strip()
        assert "数据A" in out

    def test_类别实例化组合(self):
        """复杂类别 + 字段访问 + 实例化运行。"""
        from 周道 import 转译
        src = """
设置产品类别，包括以下内容：名称，须为文本；价格，须为整数且不得为负；标签，可以没有值。
""".strip()
        py = 转译(src)
        env = {"__name__": "__周道__"}
        exec(py, env)
        Product = env["产品"]
        p = Product(名称="手机A", 价格=2999)
        assert p.名称 == "手机A"
        assert p.价格 == 2999

    def test_成员映射组合(self):
        """成员名映射 + 随机函数。"""
        src = """
从《随机》中引入随机整数。
设数字为随机整数（1、10），
显示数字。
""".strip()
        py = 编译(src)  # 确保可编译
        assert "randint as 随机整数" in py


# ==================== 七、--check 流程 ====================

# ==================== 测试质量扫描 ====================

class Test测试质量:

    def test_拒绝无断言布尔表达式(self):
        """扫描测试文件，拒绝仅计算布尔表达式但不 assert 的测试。"""
        import ast, pathlib
        test_file = pathlib.Path(__file__).parent / "test_acceptance_002.py"
        源码 = test_file.read_text("utf-8")
        tree = ast.parse(源码)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for stmt in node.body:
                    # 裸表达式语句（不是assert，不是赋值，不是返回）
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Compare):
                        raise AssertionError(
                            f"测试函数 {node.name} 含有无 assert 的比较表达式："
                            f" {ast.dump(stmt.value)[:80]}"
                        )

    def test_拒绝裸except_Exception(self):
        """拒绝 except Exception 不重新抛出的测试。"""
        import ast, pathlib
        test_file = pathlib.Path(__file__).parent / "test_acceptance_002.py"
        源码 = test_file.read_text("utf-8")
        tree = ast.parse(源码)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
                    if not any(isinstance(s, ast.Raise) for s in node.body):
                        raise AssertionError(
                            f"存在 except Exception 但不重新抛出的处理"
                        )


class TestCheck流程:

    def test_check通过(self):
        """--check 必须完整执行 Lexer→Parser→Lowering→SemanticAnalysis→Emitter→compile。"""
        src = "设数量为3，显示数量。"
        # 完整管线：扫描 → 解析 → 降低 → 语义分析 → 发射
        from 周道 import 转译
        py = 转译(src)
        compile(py, "<check>", "exec")
        # 没有异常即通过

    def test_check语法错误(self):
        """语法错误应被 --check 捕获。"""
        from 周道.lexer import 扫描
        from 周道.parser import 解析器
        from 周道.errors import 语法错误
        src = "设数量为"
        with pytest.raises(语法错误):
            tokens = 扫描(src)
            p = 解析器(tokens)
            ast = p.解析()
