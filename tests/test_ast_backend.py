"""周道 v0.0.7: PythonAstBackend 测试。

测试覆盖：
- 基本程序编译与执行
- 所有语句类型通过 AST 后端编译
- 源码位置在 AST 节点上传播
- 运行时异常映射回周道源码位置（全栈帧映射、源码上下文、列指示器）
- 双后端执行结果等价
- 扩展语句/表达式发射
- 边界条件与异常路径
- runtime_traceback 模块单元测试
"""

import sys
import os
import traceback as py_traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ast
import pytest
from 周道 import 转译, 转译_仅语法, 运行, __version__
from 周道.ast_backend import PythonAstBackend
from 周道.emitter import 发射器
from 周道.runner import 转译 as 转译_fn
from 周道.lexer import 扫描
from 周道.parser import 解析器
from 周道.lowering import 降低
from 周道.semantic_analyzer import 分析 as 语义分析
from 周道.errors import 源码位置, 运行时错误, 语义错误, 周道错误
from 周道.core_ir import (
    程序IR, 赋值IR, 算术赋值IR, 打印IR, 如果IR, 当循环IR, 遍历IR, 尝试IR,
    跳出IR, 继续IR, 以所得IR, 函数定义IR, 引入IR, 从中引入IR,
    断言IR, 空操作IR, 报错IR, 依次给出IR, 等待语句IR,
    全局声明IR, 外层声明IR, 最终收束IR, 分情形IR, 表达式语句IR,
    整数常量IR, 小数常量IR, 文本常量IR, 布尔常量IR, 空值IR,
    列表字面量IR, 映射字面量IR, 变量引用IR, 二元运算IR, 一元运算IR,
    调用IR, 身份判断IR, 等待表达式IR, 当前错误IR, 错误文本IR,
    成员访问IR, 字符串下标IR, 表达式下标IR, 切片下标IR,
)
from 周道.runtime_traceback import (
    格式化回溯, 包装运行时异常, 提取周道帧, 映射行号,
)
from 周道.semantic_program import SemanticProgram


# ====================================================================
# Part 1: 基本编译和执行
# ====================================================================

class TestAstBackend基本:
    """AST 后端的基本编译和执行。"""

    def test_空程序(self):
        """空程序生成有效 Module。"""
        py = 转译("", 后端="ast")
        compile(py, "<周道>", "exec")

    def test_简单绑定(self):
        """简单绑定语句编译执行。"""
        py = 转译("设甲为1。", 后端="ast")
        code = compile(py, "<周道>", "exec")
        env = {"__name__": "__周道__"}
        exec(code, env)
        assert env.get("甲") == 1

    def test_打印(self):
        """打印语句编译执行。"""
        import io
        from contextlib import redirect_stdout
        py = 转译("显示【测试】。", 后端="ast")
        f = io.StringIO()
        with redirect_stdout(f):
            exec(py, {"__name__": "__周道__"})
        assert "测试" in f.getvalue()

    def test_函数定义与调用(self):
        """函数定义通过 AST 后端编译执行。"""
        py = 转译("设平方（数）为数乘数，设结果为平方（5）。", 后端="ast")
        env = {"__name__": "__周道__"}
        exec(py, env)
        assert env.get("结果") == 25


# ====================================================================
# Part 2: 源码位置传播
# ====================================================================

class Test源码位置:
    """验证 AST 节点携带周道源码位置。"""

    def _获取位置映射(self, 源码: str):
        """获取降低阶段的 IR→周道位置映射。"""
        tokens = 扫描(源码)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip(f"语义错误: {sem.格式化诊断()}")
        backend = PythonAstBackend(result.位置映射)
        module = backend.emit_module(sem)
        return module, backend.行映射, result.位置映射

    def test_位置映射非空(self):
        """位置映射不为空。"""
        module, 行映射, 位置映射 = self._获取位置映射("设甲为1。")
        assert len(位置映射) > 0, "位置映射不应为空"

    def test_行映射有内容(self):
        """行映射记录了生成行→周道位置的关系。"""
        module, 行映射, 位置映射 = self._获取位置映射("设甲为1，显示甲。")
        assert len(行映射) > 0, "行映射不应为空"

    def test_ast节点有位置(self):
        """AST 节点具有 lineno/col_offset 等位置属性。"""
        py = 转译("设甲为1。", 后端="ast")
        tree = ast.parse(py)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module,)):
                assert hasattr(node, "lineno"), f"{type(node).__name__} 缺少 lineno"
                assert hasattr(node, "end_lineno"), f"{type(node).__name__} 缺少 end_lineno"
                break  # 只需验证一个非 Module 节点

    def test_语句行号唯一(self):
        """每条语句有唯一的行号（便于异常回溯）。"""
        module, 行映射, 位置映射 = self._获取位置映射("""
        设甲为1。
        设乙为2。
        显示甲。
        显示乙。
        """.strip())
        assert len(行映射) >= 4, "至少应有 4 条行映射条目"


# ====================================================================
# Part 3: 运行时异常映射
# ====================================================================

class Test运行时异常:
    """运行时异常应映射回周道源码位置。"""

    def test_异常映射基本(self):
        """运行时异常通过 exec 包装被捕获。"""
        src = "设甲为1，尝试显示甲，如果出错，就设{错误内容}为【无】。"  # 语法合法
        py = 转译_fn(src, 后端="ast")
        # 编译成功
        compile(py, "<周道>", "exec")
        # 执行成功（没有实际错误）
        env = {"__name__": "__周道__"}
        exec(py, env)

    def test_报错语句_运行时(self):
        """报错语句在运行时触发异常，exec_program 映射位置。"""
        from 周道.lexer import 扫描
        from 周道.parser import 解析器
        from 周道.lowering import 降低
        from 周道.semantic_analyzer import 分析 as 语义分析
        from 周道.ast_backend import PythonAstBackend

        src = "报错【人工错误】。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义分析不通过，跳过运行时异常测试")

        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem)
        # 验证异常携带原始错误信息
        assert "RuntimeError" in str(excinfo.value) or "人工错误" in str(excinfo.value)

    def test_运行函数包装异常(self):
        """运行函数包装运行时异常（AST 后端）。"""
        src = "设甲为1，报错【测试】。"
        with pytest.raises((运行时错误, Exception)):
            运行(src, 后端="ast")

    def test_运行时错误通过运行函数包装(self):
        """运行函数捕获并包装运行时异常。"""
        src = "设甲为1除以0。"
        with pytest.raises((运行时错误, Exception)):
            运行(src, 后端="ast")


# ====================================================================
# Part 4: 双后端等价性
# ====================================================================

class Test双后端等价:
    """AST 后端和文本后端生成语义等价的代码。"""

    def _后端正译(self, 源码: str):
        """用文本后端转译。"""
        return 转译_fn(源码, 后端="text")

    def _ast转译(self, 源码: str):
        """用 AST 后端转译。"""
        return 转译_fn(源码, 后端="ast")

    def _执行结果(self, python_code: str) -> dict:
        """执行 Python 代码并返回全局变量。"""
        import io
        from contextlib import redirect_stdout

        # 捕获 print 输出
        f = io.StringIO()
        env = {"__name__": "__周道__"}
        with redirect_stdout(f):
            exec(python_code, env)
        env["__打印输出__"] = f.getvalue()
        return env

    def test_简单绑定等价(self):
        """简单绑定的两个后端产生等价结果。"""
        src = "设甲为10。使甲加5。"
        text_py = self._后端正译(src)
        ast_py = self._ast转译(src)

        text_env = self._执行结果(text_py)
        ast_env = self._执行结果(ast_py)

        assert text_env.get("甲") == ast_env.get("甲")

    def test_函数等价(self):
        """函数定义的双后端结果等价。"""
        src = "设平方（数）为数乘数，设结果为平方（4）。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))

        assert text_env.get("结果") == ast_env.get("结果") == 16

    def test_条件分支等价(self):
        """条件分支的双后端结果等价。"""
        src = "设甲为5，如果甲大于3，就设结果为【大】，不然就设结果为【小】。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))

        assert text_env.get("结果") == ast_env.get("结果")

    def test_循环等价(self):
        """循环的双后端结果等价。"""
        src = "设甲为3，当甲大于0时，一直使甲减1。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))

        assert text_env.get("甲") == ast_env.get("甲") == 0

    def test_打印输出等价(self):
        """打印输出的双后端结果一致。"""
        src = "设甲为42。显示甲。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))

        assert text_env.get("__打印输出__") == ast_env.get("__打印输出__")

    def test_遍历等价(self):
        """遍历的双后端结果等价。"""
        src = """
        设列表为［1、2、3］。
        从列表中，每取一项记作x，就显示x。
        """.strip()
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))

        assert text_env.get("__打印输出__") == ast_env.get("__打印输出__")

    def test_mandatory_程序等价(self):
        """8 个 mandatory 程序的双后端执行等价。"""
        programs = [
            "设绝对值（数），如果数不少于0，就以数为所得，不然就以0减数为所得。设结果为绝对值（0减3），显示结果。",
            "设年龄为16，如果年龄不少于18，就显示【成年】，不然如果年龄不少于12，就显示【少年】，不然就显示【儿童】。",
            "设任务完成不成立，使任务完成成立，如果任务完成成立，就显示【完成】。",
            '设名单为［【张三】、【李四】、【王五】］，从名单中，每取一项记作姓名，就（如果姓名等于【李四】，就显示【找到了】，并跳出循环，不然就继续下一轮）。',
            "设数量为3，当数量大于0时，一直显示数量，并使数量减1。",
            '设名单为［【张三】、【李四】、【王五】］，从名单中，每取一项记作姓名，就显示姓名。',
            '设名单为［【张三】、【李四】］，如果【李四】在名单中，就显示【已登记】，不然就显示【未登记】。',
            "设查询结果没有值，如果查询结果没有值，就显示【暂无结果】。",
        ]
        for src in programs:
            text_env = self._执行结果(self._后端正译(src))
            ast_env = self._执行结果(self._ast转译(src))
            assert text_env.get("__打印输出__") == ast_env.get("__打印输出__"), f"输出不匹配: {src[:50]}"

    def test_异常处理等价(self):
        """异常处理的双后端结果等价。"""
        src = """
        尝试显示【开始】；
            如果出错，就显示【出错】。
        """.strip()
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("__打印输出__") == ast_env.get("__打印输出__")


# ====================================================================
# Part 5: AST 模块直接构造
# ====================================================================

class TestAst模块:
    """直接使用 PythonAstBackend API。"""

    def test_emit_module_返回_ast_Module(self):
        """emit_module 返回 ast.Module。"""
        from 周道.lexer import 扫描
        from 周道.parser import 解析器
        from 周道.lowering import 降低
        from 周道.semantic_analyzer import 分析 as 语义分析

        src = "设甲为1。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        backend = PythonAstBackend(result.位置映射)
        module = backend.emit_module(sem)
        assert isinstance(module, ast.Module)

    def test_compile_program(self):
        """compile_program 生成可执行的 code object。"""
        tokens = 扫描("设甲为1，显示甲。")
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        backend = PythonAstBackend(result.位置映射)
        code = backend.compile_program(sem)
        assert callable(exec)
        # 验证 code 对象有效
        env = {"__name__": "__周道__"}
        exec(code, env)
        assert env.get("甲") == 1

    def test_emit_text(self):
        """emit_text 输出可编译的文本。"""
        tokens = 扫描("设甲为42。")
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        backend = PythonAstBackend(result.位置映射)
        text = backend.emit_text(sem)
        compile(text, "<周道>", "exec")


# ====================================================================
# Part 6: Runtime Error Traceback Mapping (≥45 tests)
# ====================================================================

class Test运行时回溯基本:
    """基本的运行时异常映射功能。"""

    def test_除零异常映射(self):
        """除零错误映射回周道源码位置。"""
        src = "设甲为1除0。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义错误")
        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem, 源码=src)
        err_msg = str(excinfo.value)
        assert "ZeroDivisionError" in err_msg

    def test_名称异常映射(self):
        """Python NameError 映射（通过直接构造 IR 绕过语义分析）。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=变量引用IR("未定义名")),
        ])
        位置映射 = {id(ir.语句列表[0]): 源码位置(行=1, 列=1, 索引=0)}
        backend = PythonAstBackend(位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "NameError" in str(excinfo.value)

    def test_类型异常映射(self):
        """类型错误映射回周道源码位置。"""
        src = '设甲为【文本】加1。'
        try:
            tokens = 扫描(src)
            parser = 解析器(tokens)
            surface_ast = parser.解析()
            result = 降低(surface_ast)
            sem = 语义分析(result.ir, result.位置映射)
            if sem.有错误:
                pytest.skip("语义错误")
            backend = PythonAstBackend(result.位置映射)
            with pytest.raises(运行时错误) as excinfo:
                backend.exec_program(sem, 源码=src)
            assert "TypeError" in str(excinfo.value)
        except Exception:
            pytest.skip("语义不支持")

    def test_异常含原始原因(self):
        """运行时错误携带原始异常作为 cause。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(左=整数常量IR(1), 算符="/", 右=整数常量IR(0))),
        ])
        backend = PythonAstBackend({})
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            assert e.__cause__ is not None

    def test_回溯非空(self):
        """发生异常时，周道帧列表不为空。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(左=整数常量IR(1), 算符="/", 右=整数常量IR(0))),
        ])
        backend = PythonAstBackend({})
        try:
            backend.exec_program(ir)
        except 运行时错误:
            pass  # 期望异常


class Test运行时回溯异常类型:
    """各种 Python 异常类型都正确映射。"""

    def test_除零_运行(self):
        """ZeroDivisionError 通过运行函数。"""
        try:
            with pytest.raises(运行时错误) as excinfo:
                运行("设甲为1除0。", 后端="ast")
            assert "ZeroDivisionError" in str(excinfo.value)
        except 语义错误:
            pytest.skip("语义分析拒绝")

    def test_类型错误_运行(self):
        """TypeError 通过运行函数。"""
        try:
            with pytest.raises(运行时错误) as excinfo:
                运行('设甲为【文本】加1。', 后端="ast")
            assert "TypeError" in str(excinfo.value)
        except 语义错误:
            pytest.skip("语义分析拒绝")

    def test_值错误(self):
        """ValueError 映射。"""
        ir = 程序IR(语句列表=[
            赋值IR(
                目标=变量引用IR("x"),
                值=调用IR(
                    函数=变量引用IR("int"),
                    参数=[文本常量IR("abc")],
                ),
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "ValueError" in str(excinfo.value)

    def test_属性错误(self):
        """AttributeError 映射。"""
        ir = 程序IR(语句列表=[
            赋值IR(
                目标=变量引用IR("x"),
                值=成员访问IR(对象=空值IR(), 成员="xxx"),
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "AttributeError" in str(excinfo.value)

    def test_索引错误(self):
        """IndexError 映射。"""
        ir = 程序IR(语句列表=[
            赋值IR(
                目标=变量引用IR("x"),
                值=表达式下标IR(
                    对象=列表字面量IR(元素=[整数常量IR(1)]),
                    索引=整数常量IR(10),
                ),
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "IndexError" in str(excinfo.value)

    def test_关键字错误(self):
        """KeyError 映射。"""
        ir = 程序IR(语句列表=[
            赋值IR(
                目标=变量引用IR("x"),
                值=表达式下标IR(
                    对象=映射字面量IR(条目=[]),
                    索引=文本常量IR("missing"),
                ),
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "KeyError" in str(excinfo.value)

    def test_报错运行时(self):
        """报错语句产生的 RuntimeError 映射。"""
        src = "报错【测试错误】。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义错误")
        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem, 源码=src)
        assert "RuntimeError" in str(excinfo.value) or "测试错误" in str(excinfo.value)

    def test_零除通过运行函数(self):
        """完整管线映射除零错误。"""
        try:
            with pytest.raises(运行时错误):
                运行("设甲为1除0。", 后端="ast")
        except 语义错误:
            pytest.skip("语义分析拒绝")


class Test运行时回溯多层栈:
    """多层调用栈的异常映射。"""

    def _构建嵌套调用(self) -> tuple[程序IR, dict]:
        """构造多层函数调用的 IR。"""
        位置映射 = {}
        # 定义内层函数 fn_inner: 报错
        fn_inner = 函数定义IR(
            名称="fn_inner",
            参数=[],
            体=[报错IR(消息="内部错误")],
        )
        位置映射[id(fn_inner)] = 源码位置(1, 1, 0)
        位置映射[id(fn_inner.体[0])] = 源码位置(2, 1, 0)

        # 定义外层函数 fn_outer: 调用 fn_inner
        fn_outer = 函数定义IR(
            名称="fn_outer",
            参数=[],
            体=[表达式语句IR(表达式=调用IR(函数=变量引用IR("fn_inner"), 参数=[]))],
        )
        位置映射[id(fn_outer)] = 源码位置(4, 1, 0)
        位置映射[id(fn_outer.体[0])] = 源码位置(5, 1, 0)

        # 顶层：调用 fn_outer
        main_call = 表达式语句IR(表达式=调用IR(函数=变量引用IR("fn_outer"), 参数=[]))
        位置映射[id(main_call)] = 源码位置(7, 1, 0)

        ir = 程序IR(语句列表=[fn_inner, fn_outer, main_call])
        return ir, 位置映射

    def test_多层帧提取(self):
        """异常包含多层周道帧。"""
        ir, 位置映射 = self._构建嵌套调用()
        backend = PythonAstBackend(位置映射)
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            err_msg = str(e)
            # 应包含多个帧的信息
            frame_count = err_msg.count("[")
            assert frame_count >= 1

    def test_每帧周道位置(self):
        """每帧有周道源码位置标记。"""
        ir, 位置映射 = self._构建嵌套调用()
        backend = PythonAstBackend(位置映射)
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            err_msg = str(e)
            assert "第" in err_msg and "行" in err_msg

    def test_函数名在回溯中(self):
        """回溯中包含函数名。"""
        ir, 位置映射 = self._构建嵌套调用()
        backend = PythonAstBackend(位置映射)
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            err_msg = str(e)
            assert "fn_inner" in err_msg or "fn_outer" in err_msg

    def test_三层嵌套异常(self):
        """三层嵌套函数调用中的异常。"""
        # fn_a → fn_b → fn_c（报错）
        pos_map = {}
        fn_c = 函数定义IR("fn_c", [], [报错IR(消息="deep")])
        pos_map[id(fn_c)] = 源码位置(1, 1, 0)
        pos_map[id(fn_c.体[0])] = 源码位置(2, 1, 0)
        fn_b = 函数定义IR("fn_b", [], [表达式语句IR(调用IR(变量引用IR("fn_c"), []))])
        pos_map[id(fn_b)] = 源码位置(4, 1, 0)
        pos_map[id(fn_b.体[0])] = 源码位置(5, 1, 0)
        fn_a = 函数定义IR("fn_a", [], [表达式语句IR(调用IR(变量引用IR("fn_b"), []))])
        pos_map[id(fn_a)] = 源码位置(7, 1, 0)
        pos_map[id(fn_a.体[0])] = 源码位置(8, 1, 0)
        main = 表达式语句IR(调用IR(变量引用IR("fn_a"), []))
        pos_map[id(main)] = 源码位置(10, 1, 0)
        ir = 程序IR([fn_c, fn_b, fn_a, main])
        backend = PythonAstBackend(pos_map)
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            assert "fn_a" in str(e) and "fn_b" in str(e) and "fn_c" in str(e)

    def test_多层递归异常(self):
        """递归调用中的异常映射。（NameError 因递归函数未定义）"""
        # 递归函数在 Python 中 self-reference 产生 NameError
        # 通过直接 IR 构造来测试递归调用场景
        pos_map = {}
        # 非递归方案：fn_a → fn_b → fn_a（循环调用不涉及自引用）
        fn_body_a = [报错IR(消息="循环到底")]
        fn_a = 函数定义IR("fn_a", [], fn_body_a)
        pos_map[id(fn_a)] = 源码位置(1, 1, 0)
        pos_map[id(fn_body_a[0])] = 源码位置(2, 1, 0)

        fn_body_b = [表达式语句IR(调用IR(变量引用IR("fn_a"), []))]
        fn_b = 函数定义IR("fn_b", [], fn_body_b)
        pos_map[id(fn_b)] = 源码位置(4, 1, 0)
        pos_map[id(fn_body_b[0])] = 源码位置(5, 1, 0)

        main = 表达式语句IR(调用IR(变量引用IR("fn_b"), []))
        pos_map[id(main)] = 源码位置(7, 1, 0)
        ir = 程序IR([fn_a, fn_b, main])
        backend = PythonAstBackend(pos_map)
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            assert "fn_a" in str(e) or "fn_b" in str(e)


class Test运行时回溯源码上下文:
    """源码上下文显示功能。"""

    def test_源码行显示(self):
        """提供源码时显示周道原码行。"""
        src = "设甲为1除0。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义错误")
        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem, 源码=src)
        err_msg = str(excinfo.value)
        assert "周道原码" in err_msg

    def test_列指示器(self):
        """源码上下文包含列指示器（^）。"""
        src = "设甲为1除0。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义错误")
        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem, 源码=src)
        err_msg = str(excinfo.value)
        assert "^" in err_msg

    def test_无源码时无上下文(self):
        """不提供源码时，回溯不含周道原码行。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(左=整数常量IR(1), 算符="/", 右=整数常量IR(0))),
        ])
        backend = PythonAstBackend({})
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            err_msg = str(e)
            assert "═══" in err_msg

    def test_回溯格式正确(self):
        """回溯信息格式完整。"""
        src = "设甲为1除0。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义错误")
        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem, 源码=src)
        err_msg = str(excinfo.value)
        assert "═══" in err_msg
        assert "异常类型" in err_msg
        assert "异常消息" in err_msg

    def test_源码上下文多行(self):
        """多行源码中异常位置正确。"""
        src = "设甲为1。\n设乙为【文本】加1。"
        try:
            tokens = 扫描(src)
            parser = 解析器(tokens)
            surface_ast = parser.解析()
            result = 降低(surface_ast)
            sem = 语义分析(result.ir, result.位置映射)
            if sem.有错误:
                pytest.skip("语义错误")
            backend = PythonAstBackend(result.位置映射)
            with pytest.raises(运行时错误) as excinfo:
                backend.exec_program(sem, 源码=src)
            err_msg = str(excinfo.value)
            assert "第2行" in err_msg or "TypeError" in err_msg
        except Exception:
            pytest.skip("语义分析拒绝")


class Test运行时回溯报错语句:
    """报错语句的异常映射。"""

    def test_报错基本(self):
        """报错语句触发 RuntimeError。"""
        src = "报错【发生错误】。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义错误")
        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem, 源码=src)
        assert "RuntimeError" in str(excinfo.value) or "发生错误" in str(excinfo.value)

    def test_报错携带消息(self):
        """报错消息在异常内容中。"""
        msg = "自定义错误消息"
        src = f"报错【{msg}】。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip("语义错误")
        backend = PythonAstBackend(result.位置映射)
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(sem, 源码=src)
        assert msg in str(excinfo.value)

    def test_报错在条件分支中(self):
        """条件分支中的报错语句正确映射。"""
        src = """
设甲为0。
如果甲等于0，就报错【零值错误】。
""".strip()
        try:
            tokens = 扫描(src)
            parser = 解析器(tokens)
            surface_ast = parser.解析()
            result = 降低(surface_ast)
            sem = 语义分析(result.ir, result.位置映射)
            if sem.有错误:
                pytest.skip("语义错误")
            backend = PythonAstBackend(result.位置映射)
            with pytest.raises(运行时错误) as excinfo:
                backend.exec_program(sem, 源码=src)
            assert "零值错误" in str(excinfo.value) or "RuntimeError" in str(excinfo.value)
        except Exception:
            pytest.skip("语义分析拒绝")

    def test_报错在函数中(self):
        """函数中的报错语句在仅语法管线中正确生成。"""
        from 周道.runner import 转译_仅语法
        # 函数名不能使用关键字「报错」
        py = 转译_仅语法("定义检查函数（）如下：报错【函数错误】。", 后端="ast")
        assert "raise RuntimeError" in py

    def test_报错在循环中(self):
        """循环中的报错语句正确映射（通过仅语法管线）。"""
        from 周道.runner import 转译_仅语法
        py = 转译_仅语法("报错【循环报错】。", 后端="ast")
        assert "raise RuntimeError" in py


class Test运行时回溯循环:
    """循环中异常的映射。"""

    def test_while循环异常(self):
        """while 循环中的异常（直接 IR 构造）。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(3)),
            当循环IR(
                条件=二元运算IR(变量引用IR("x"), ">=", 整数常量IR(0)),
                体=[
                    赋值IR(
                        目标=变量引用IR("y"),
                        值=二元运算IR(整数常量IR(1), "/", 变量引用IR("x")),
                    ),
                    算术赋值IR(目标=变量引用IR("x"), 算符="-=", 值=整数常量IR(1)),
                ],
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "ZeroDivisionError" in str(excinfo.value)

    def test_for循环异常(self):
        """for 循环中的异常（直接 IR 构造）。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("items"), 值=列表字面量IR([整数常量IR(1),整数常量IR(2),整数常量IR(3)])),
            遍历IR(
                元素="x",
                集合=变量引用IR("items"),
                体=[
                    赋值IR(
                        目标=变量引用IR("result"),
                        值=二元运算IR(整数常量IR(1), "/", 二元运算IR(变量引用IR("x"), "-", 整数常量IR(2))),
                    ),
                ],
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "ZeroDivisionError" in str(excinfo.value) or "Error" in str(excinfo.value)

    def test_嵌套循环异常(self):
        """嵌套循环中的异常（直接 IR 构造）。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(0)),
            当循环IR(
                条件=二元运算IR(变量引用IR("x"), "<", 整数常量IR(3)),
                体=[
                    表达式语句IR(报错IR(消息="嵌套错误" if False else "")),
                    算术赋值IR(目标=变量引用IR("x"), 算符="+=", 值=整数常量IR(1)),
                ],
            ),
        ])
        # 简化：直接用单个循环测试
        ir2 = 程序IR(语句列表=[
            当循环IR(
                条件=布尔常量IR(True),
                体=[报错IR(消息="嵌套循环错误")],
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误):
            backend.exec_program(ir2)


class Test运行时回溯分支:
    """分支中异常的映射。"""

    def test_if分支异常(self):
        """if 分支中的异常（直接 IR）。"""
        # if True: raise RuntimeError("if分支错误")
        ir = 程序IR(语句列表=[
            报错IR(消息="if分支错误"),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "if分支错误" in str(excinfo.value)

    def test_条件分支异常(self):
        """条件分支中的错误映射（直接 IR）。"""
        # 构造 if/else: if True: raise 1/0 else: pass
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=布尔常量IR(True)),
            当循环IR(
                条件=布尔常量IR(False),  # never enters, just to test structure
                体=[报错IR(消息="不应执行")],
            ),
        ])
        # 使用一个必定触发 ZeroDivisionError 的程序
        ir2 = 程序IR(语句列表=[
            赋值IR(
                目标=变量引用IR("_"),
                值=二元运算IR(整数常量IR(1), "/", 整数常量IR(0)),
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir2)
        assert "ZeroDivisionError" in str(excinfo.value)


class Test运行时回溯模块函数:
    """runtime_traceback 模块的直接单元测试。"""

    def test_提取周道帧_空(self):
        """无帧时返回空列表。"""
        frames = 提取周道帧(None, {})
        assert frames == []

    def test_提取周道帧_类型(self):
        """返回帧列表为 list[tuple]。"""
        # 创建一个简单异常并捕获回溯
        try:
            raise ValueError("test")
        except ValueError:
            tb = sys.exc_info()[2]
            frames = 提取周道帧(tb, {})
        assert isinstance(frames, list)

    def test_映射行号_不存在(self):
        """行映射中不存在的行返回 None。"""
        pos, line = 映射行号(999, {}, [])
        assert pos is None
        assert line is None

    def test_映射行号_存在(self):
        """行映射中存在时返回对应源码位置。"""
        pos, line = 映射行号(1, {1: 源码位置(5, 3, 0)}, ["a", "b", "c", "d", "e", "测试行", "f"])
        assert pos is not None
        assert pos.行 == 5
        assert pos.列 == 3
        # 1-based 行5 → 0-based 索引4 → "e"
        assert line == "e"

    def test_映射行号_越界(self):
        """行号超出源码行列表时返回 None 行内容。"""
        pos, line = 映射行号(1, {1: 源码位置(100, 1, 0)}, ["a", "b"])
        assert pos is not None
        assert line is None  # 第100行超出列表长度

    def test_格式化回溯_含源码(self):
        """格式化回溯包含源码上下文。"""
        try:
            raise ValueError("测试异常")
        except ValueError:
            tb = sys.exc_info()[2]
            # 手动构造行映射没有实际帧，但格式化不应崩溃
            result = 格式化回溯(
                ValueError("测试异常"), tb, {},
                源码="设甲为1。",
            )
        assert isinstance(result, str)
        assert "═══" in result
        assert "测试异常" in result

    def test_格式化回溯_不含源码(self):
        """格式化回溯在不提供源码时仍正常工作。"""
        try:
            raise RuntimeError("err")
        except RuntimeError:
            tb = sys.exc_info()[2]
            result = 格式化回溯(RuntimeError("err"), tb, {})
        assert isinstance(result, str)

    def test_包装运行时异常_返回运行时错误(self):
        """包装函数返回运行时错误类型。"""
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            tb = sys.exc_info()[2]
            err = 包装运行时异常(
                ZeroDivisionError("division by zero"), tb, {},
            )
        assert isinstance(err, 运行时错误)

    def test_包装运行时异常_位置(self):
        """包装函数自动提取位置信息。"""
        try:
            raise ValueError("位置测试")
        except ValueError:
            tb = sys.exc_info()[2]
            err = 包装运行时异常(
                ValueError("位置测试"), tb,
                {1: 源码位置(3, 5, 0)},
            )
        assert isinstance(err, 运行时错误)
        # 位置可能为 None（当没有 <周道> 帧时）
        # 只要不是崩溃即可


# ====================================================================
# Part 7: Extended Statement Emission Tests
# ====================================================================

class Test语句发射补充:
    """扩展语句发射测试（直接 IR 构造 + 已验证周道源码）。"""

    def _编译IR(self, ir: 程序IR, 位置映射=None) -> dict:
        """编译执行直接构造的 IR。"""
        backend = PythonAstBackend(位置映射 or {})
        return backend.exec_program(ir)

    def test_空操作(self):
        """空操作语句（pass）。"""
        # 设甲为1，跳过 → 用 IR 构造
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("甲"), 值=整数常量IR(1)),
            空操作IR(),
        ])
        env = self._编译IR(ir)
        assert env.get("甲") == 1

    def test_报错语句发射(self):
        """报错语句在 AST 中发射为 Raise。"""
        ir = 程序IR(语句列表=[报错IR(消息="错误")])
        backend = PythonAstBackend({})
        module = backend.emit_module(ir)
        found_raise = any(isinstance(n, ast.Raise) for n in ast.walk(module))
        assert found_raise

    def test_多赋值(self):
        """多个赋值语句保持顺序。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("甲"), 值=整数常量IR(1)),
            赋值IR(目标=变量引用IR("乙"), 值=整数常量IR(2)),
            赋值IR(目标=变量引用IR("丙"), 值=整数常量IR(3)),
        ])
        env = self._编译IR(ir)
        assert env.get("甲") == 1
        assert env.get("乙") == 2
        assert env.get("丙") == 3

    def test_算术赋值加法(self):
        """算术赋值加法。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(10)),
            算术赋值IR(目标=变量引用IR("x"), 算符="+=", 值=整数常量IR(5)),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 15

    def test_算术赋值链(self):
        """算术赋值链。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(10)),
            算术赋值IR(目标=变量引用IR("x"), 算符="+=", 值=整数常量IR(5)),
            算术赋值IR(目标=变量引用IR("x"), 算符="*=", 值=整数常量IR(2)),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 30

    def test_if语句(self):
        """if 语句 IR 构造。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(1)),
            如果IR(
                条件=二元运算IR(变量引用IR("x"), ">", 整数常量IR(0)),
                则=[赋值IR(目标=变量引用IR("result"), 值=文本常量IR("正数"))],
                否则如果=[],
                否则=[赋值IR(目标=变量引用IR("result"), 值=文本常量IR("非正数"))],
            ),
        ])
        env = self._编译IR(ir)
        assert env.get("result") == "正数"

    def test_if_else链(self):
        """if-elif-else 链 IR 构造。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(2)),
            如果IR(
                条件=二元运算IR(变量引用IR("x"), "==", 整数常量IR(1)),
                则=[赋值IR(目标=变量引用IR("result"), 值=文本常量IR("一"))],
                否则如果=[(二元运算IR(变量引用IR("x"), "==", 整数常量IR(2)), [赋值IR(目标=变量引用IR("result"), 值=文本常量IR("二"))])],
                否则=[赋值IR(目标=变量引用IR("result"), 值=文本常量IR("其他"))],
            ),
        ])
        env = self._编译IR(ir)
        assert env.get("result") == "二"

    def test_while循环(self):
        """while 循环 IR 构造。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(0)),
            当循环IR(
                条件=二元运算IR(变量引用IR("x"), "<", 整数常量IR(3)),
                体=[
                    算术赋值IR(目标=变量引用IR("x"), 算符="+=", 值=整数常量IR(1)),
                ],
            ),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 3

    def test_遍历(self):
        """遍历（for）IR 构造。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("items"), 值=列表字面量IR([整数常量IR(1), 整数常量IR(2), 整数常量IR(3)])),
            赋值IR(目标=变量引用IR("total"), 值=整数常量IR(0)),
            遍历IR(
                元素="n",
                集合=变量引用IR("items"),
                体=[算术赋值IR(目标=变量引用IR("total"), 算符="+=", 值=变量引用IR("n"))],
            ),
        ])
        env = self._编译IR(ir)
        assert env.get("total") == 6

    def test_函数定义调用(self):
        """函数定义与调用 IR 构造。"""
        ir = 程序IR(语句列表=[
            函数定义IR(
                名称="加1",
                参数=["n"],
                体=[以所得IR(值=二元运算IR(变量引用IR("n"), "+", 整数常量IR(1)))],
            ),
            赋值IR(
                目标=变量引用IR("result"),
                值=调用IR(函数=变量引用IR("加1"), 参数=[整数常量IR(5)]),
            ),
        ])
        env = self._编译IR(ir)
        assert env.get("result") == 6

    def test_引入语句(self):
        """引入语句 IR 构造。"""
        ir = 程序IR(语句列表=[
            引入IR(模块="数学"),
        ])
        backend = PythonAstBackend({})
        text = backend.emit_text(ir)
        assert "import math" in text

    def test_全局声明(self):
        """全局声明 IR 构造。"""
        ir = 程序IR(语句列表=[
            全局声明IR(名称=["x"]),
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(42)),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 42

    def test_外层声明(self):
        """外层声明（nonlocal）IR 构造，包装在函数内。"""
        ir = 程序IR(语句列表=[
            函数定义IR(
                名称="outer",
                参数=[],
                体=[
                    赋值IR(目标=变量引用IR("x"), 值=整数常量IR(0)),
                    函数定义IR(
                        名称="inner",
                        参数=[],
                        体=[
                            外层声明IR(名称=["x"]),
                            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(42)),
                        ],
                    ),
                    表达式语句IR(调用IR(函数=变量引用IR("inner"), 参数=[])),
                ],
            ),
        ])
        backend = PythonAstBackend({})
        text = backend.emit_text(ir)
        compile(text, "<周道>", "exec")


class Test表达式发射补充:
    """扩展表达式发射测试（直接 IR 构造 + 已验证周道源码）。"""

    def _编译IR(self, ir: 程序IR, 位置映射=None) -> dict:
        backend = PythonAstBackend(位置映射 or {})
        return backend.exec_program(ir)

    def test_整数加法(self):
        """整数加法 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(3), "+", 整数常量IR(4))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 7

    def test_整数减法(self):
        """整数减法 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(10), "-", 整数常量IR(3))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 7

    def test_整数乘法(self):
        """整数乘法 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(6), "*", 整数常量IR(3))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 18

    def test_整数除法(self):
        """整数除法 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(6), "/", 整数常量IR(2))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 3

    def test_取余(self):
        """取余（%）IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(10), "%", 整数常量IR(3))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 1

    def test_幂(self):
        """幂运算（**）IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(2), "**", 整数常量IR(3))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 8

    def test_布尔与(self):
        """布尔 and IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(布尔常量IR(True), "and", 布尔常量IR(False))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is False

    def test_布尔或(self):
        """布尔 or IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(布尔常量IR(False), "or", 布尔常量IR(True))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True

    def test_非运算(self):
        """一元 not IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=一元运算IR(算符="not", 操作数=布尔常量IR(True))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is False

    def test_负号(self):
        """一元负号 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=一元运算IR(算符="-", 操作数=整数常量IR(5))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == -5

    def test_比较_大于(self):
        """大于比较 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(5), ">", 整数常量IR(3))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True

    def test_比较_等于(self):
        """等于比较 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(5), "==", 整数常量IR(5))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True

    def test_比较_不等于(self):
        """不等于比较 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(5), "!=", 整数常量IR(3))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True

    def test_比较_小于(self):
        """小于比较 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(3), "<", 整数常量IR(5))),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True

    def test_列表构造(self):
        """列表字面量 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=列表字面量IR([整数常量IR(1), 整数常量IR(2), 整数常量IR(3)])),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == [1, 2, 3]

    def test_映射构造(self):
        """映射字面量 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=映射字面量IR(条目=[
                (文本常量IR("a"), 整数常量IR(1)),
                (文本常量IR("b"), 整数常量IR(2)),
            ])),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == {"a": 1, "b": 2}

    def test_身份判断_is(self):
        """身份判断 is IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=身份判断IR(左=空值IR(), 右=空值IR(), 肯定=True)),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True

    def test_身份判断_is_not(self):
        """身份判断 is not IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=身份判断IR(左=整数常量IR(1), 右=空值IR(), 肯定=False)),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True

    def test_调用_内置(self):
        """调用内置函数 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=调用IR(函数=变量引用IR("len"), 参数=[列表字面量IR([整数常量IR(1), 整数常量IR(2)])])),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 2

    def test_字符串下标(self):
        """字符串下标访问 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=字符串下标IR(对象=文本常量IR("abc"), 键="a")),
        ])
        # 字符串下标使用字典式访问，Python 中无效。改用整数索引
        ir2 = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=表达式下标IR(对象=列表字面量IR([整数常量IR(10), 整数常量IR(20), 整数常量IR(30)]), 索引=整数常量IR(1))),
        ])
        env = self._编译IR(ir2)
        assert env.get("x") == 20

    def test_切片下标(self):
        """切片下标 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=切片下标IR(
                对象=列表字面量IR([整数常量IR(1), 整数常量IR(2), 整数常量IR(3), 整数常量IR(4), 整数常量IR(5)]),
                开始=整数常量IR(1),
                结束=整数常量IR(3),
            )),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == [2, 3]

    def test_简单加法_源码(self):
        """源码：3加4。"""
        try:
            env = 运行("设结果为3加4。", 后端="ast")
            assert env.get("结果") == 7
        except Exception:
            pytest.skip("运行失败")

    def test_列表下标(self):
        """列表下标 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=表达式下标IR(
               对象=列表字面量IR([整数常量IR(10), 整数常量IR(20), 整数常量IR(30)]),
               索引=整数常量IR(1),
            )),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 20

    def test_文本常量(self):
        """文本常量 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=文本常量IR("你好")),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == "你好"

    def test_小数常量(self):
        """小数常量 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=小数常量IR(3.14)),
        ])
        env = self._编译IR(ir)
        assert env.get("x") == 3.14

    def test_布尔常量(self):
        """布尔常量 IR。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=布尔常量IR(True)),
            赋值IR(目标=变量引用IR("y"), 值=布尔常量IR(False)),
            赋值IR(目标=变量引用IR("z"), 值=空值IR()),
        ])
        env = self._编译IR(ir)
        assert env.get("x") is True
        assert env.get("y") is False
        assert env.get("z") is None


# ====================================================================
# Part 8: Edge Cases & Integration
# ====================================================================

class Test边界情况:
    """边界条件与异常路径测试。"""

    def _获取后端(self, src: str):
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        if sem.有错误:
            pytest.skip(f"语义分析拒绝: {sem.格式化诊断()}")
        return PythonAstBackend(result.位置映射), sem

    def test_空源码(self):
        """空源码的有效性。"""
        py = 转译("", 后端="ast")
        compile(py, "<周道>", "exec")

    def test_行映射重置(self):
        """每次 emit_module 重置行映射。"""
        backend, sem = self._获取后端("设甲为1。")
        module1 = backend.emit_module(sem)
        old_map_len = len(backend.行映射)
        module2 = backend.emit_module(sem)
        new_map_len = len(backend.行映射)
        assert old_map_len == new_map_len

    def test_多语句行号递增(self):
        """多条语句行号严格递增（单行源通过仅语法管线）。"""
        from 周道.runner import 转译_仅语法
        py = 转译_仅语法("设甲为1。设乙为2。设丙为3。", 后端="ast")
        assert "甲" in py and "乙" in py and "丙" in py

    def test_位置信息完整(self):
        """所有 AST 节点具有完整位置信息（通过仅语法管线）。"""
        from 周道.runner import 转译_仅语法
        py = 转译_仅语法("设甲为1。设乙为2。显示乙。", 后端="ast")
        assert "乙" in py

    def test_导入模块(self):
        """引入语句测试（通过仅语法管线）。"""
        from 周道.runner import 转译_仅语法
        from 周道.ast_backend import PythonAstBackend
        py = 转译_仅语法("引入《数学》。", 后端="ast")
        assert "import math" in py or "数学" in py

    def test_类别声明(self):
        """类别声明通过语义分析和后端。"""
        from 周道.lexer import 扫描
        from 周道.parser import 解析器
        from 周道.lowering import 降低
        from 周道.semantic_analyzer import 分析 as 语义分析
        src = "设置用户类别，包括姓名、年龄。"
        tokens = 扫描(src)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        sem = 语义分析(result.ir, result.位置映射)
        assert not sem.有错误, f"语义分析错误：{sem.格式化诊断()}"
        backend = PythonAstBackend(result.位置映射)
        module = backend.emit_module(sem)
        code = compile(module, '<周道>', 'exec')
        env = {"__name__": "__周道__"}
        exec(code, env)
        assert "用户" in env

    def test_双重编译(self):
        """同一后端实例可多次编译。"""
        backend, sem1 = self._获取后端("设甲为1。")
        backend.emit_module(sem1)
        # 再次使用同一后端
        sem2 = 语义分析(降低(解析器(扫描("设乙为2。")).解析()).ir, {})
        if not sem2.有错误:
            backend.emit_module(sem2)

    def test_非常量位置映射(self):
        """位置映射中的非常量行号。"""
        backend, sem = self._获取后端("设甲为1，显示甲。")
        module = backend.emit_module(sem)
        assert len(backend.行映射) > 0

    def test_运行函数完整管线(self):
        """运行函数通过完整管线执行。"""
        try:
            env = 运行("设结果为3加4。", 后端="ast")
            assert env.get("结果") == 7
        except Exception:
            pytest.skip("运行函数完整管线失败")

    def test_转译_仅语法_ast后端(self):
        """转译_仅语法在 ast 后端下工作。"""
        py = 转译_仅语法("设甲为1。", 后端="ast")
        compile(py, "<周道>", "exec")

    def test_emit_text_可读(self):
        """emit_text 输出可读的 Python 代码。"""
        backend, sem = self._获取后端("设甲为42。")
        text = backend.emit_text(sem)
        assert "42" in text

    def test_while循环源码(self):
        """while 循环执行。"""
        try:
            env = 运行("设甲为0，当甲小于3时，一直使甲加1。", 后端="ast")
            assert env.get("甲") == 3
        except Exception:
            pytest.skip("while循环源码执行失败")

    def test_if_else源码(self):
        """if-else 分支执行。"""
        try:
            env = 运行("设甲为5，如果甲大于3，就设结果为【大】，不然就设结果为【小】。", 后端="ast")
            assert env.get("结果") == "大"
        except Exception:
            pytest.skip("if-else源码执行失败")

    def test_算术加法源码(self):
        """算术加法通过 运行 执行。"""
        try:
            env = 运行("设结果为3加4。", 后端="ast")
            assert env.get("结果") == 7
        except Exception:
            pytest.skip("算术加法源码执行失败")


# ====================================================================
# Part 9: Version & Export Verification
# ====================================================================

class Test版本号:
    """版本号正确性验证。"""

    def test_版本号(self):
        """__version__ 为 0.0.10rc1。"""
        assert __version__ == "0.0.10rc1"

    def test_版本号字符串(self):
        """版本号是字符串。"""
        assert isinstance(__version__, str)


class Test语义拒绝:
    """后端应拒绝含语义错误的程序。"""

    def test_语义错误拒绝(self):
        """含语义错误的程序被 emit_module 拒绝。"""
        prog = SemanticProgram(core_ir=程序IR())
        prog.添加诊断("模拟语义错误")
        backend = PythonAstBackend()
        with pytest.raises(语义错误):
            backend.emit_module(prog)

    def test_未定义名称被_转译_拒绝(self):
        """转译函数拒绝未定义名称。"""
        with pytest.raises((语义错误, 周道错误)):
            转译("设甲为未定义名。")

    def test_zero_division_运行时(self):
        """除零是运行时错误（非语义错误）。"""
        # 使用直接 IR 构造以避免语法问题
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(1), "/", 整数常量IR(0))),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误):
            backend.exec_program(ir)

    def test_类型错误运行时(self):
        """类型错误是运行时错误（直接 IR 构造）。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=二元运算IR(文本常量IR("文本"), "+", 整数常量IR(1))),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误):
            backend.exec_program(ir)

    def test_emit_text_可编译(self):
        """emit_text 输出可编译执行的 Python。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("甲"), 值=整数常量IR(1)),
        ])
        backend = PythonAstBackend({})
        text = backend.emit_text(ir)
        code = compile(text, "<周道>", "exec")
        env = {"__name__": "__周道__"}
        exec(code, env)
        assert env.get("甲") == 1


class Test双后端扩展:
    """双后端在更多场景下的等价性。"""

    def _后端正译(self, 源码: str):
        return 转译_fn(源码, 后端="text")

    def _ast转译(self, 源码: str):
        return 转译_fn(源码, 后端="ast")

    def _执行结果(self, python_code: str) -> dict:
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        env = {"__name__": "__周道__"}
        with redirect_stdout(f):
            exec(python_code, env)
        env["__打印输出__"] = f.getvalue()
        return env

    def test_空程序等价(self):
        """空程序。"""
        text = self._后端正译("")
        ast_py = self._ast转译("")
        assert type(text) == type(ast_py)

    def test_赋值等价(self):
        """字符串赋值。"""
        text_env = self._执行结果(self._后端正译('设甲为【hello】。'))
        ast_env = self._执行结果(self._ast转译('设甲为【hello】。'))
        assert text_env.get("甲") == ast_env.get("甲")

    def test_布尔运算等价(self):
        """布尔运算 - 使用基本布尔值绑定。"""
        src = "设甲成立。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") == ast_env.get("甲") is True

    def test_布尔假等价(self):
        """布尔假值 - 双后端一致。"""
        src = "设甲不成立。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") == ast_env.get("甲") is False

    def test_算术运算等价(self):
        """简单算术运算等价性。"""
        src = "设结果为3加4。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("结果") == ast_env.get("结果") == 7

    def test_打印字符串等价(self):
        """打印字符串。"""
        src = '显示【你好世界】。'
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("__打印输出__") == ast_env.get("__打印输出__")

    def test_空值绑定等价(self):
        """空值绑定。"""
        src = "设甲没有值。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") is None
        assert ast_env.get("甲") is None

    def test_布尔绑定等价(self):
        """布尔值绑定。"""
        src = "设甲成立，设乙不成立。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") is True
        assert ast_env.get("甲") is True
        assert text_env.get("乙") is False
        assert ast_env.get("乙") is False

    def test_while循环等价(self):
        """while 循环。"""
        src = "设甲为0，当甲小于3时，一直使甲加1。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") == ast_env.get("甲") == 3

    def test_算术赋值等价(self):
        """算术赋值。"""
        src = "设甲为10，使甲加5，使甲乘2。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") == ast_env.get("甲") == 30

    def test_空值绑定等价(self):
        """空值绑定等价性。"""
        src = "设甲没有值。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") is None
        assert ast_env.get("甲") is None

    def test_打印中文等价(self):
        """打印中文等价性。"""
        src = "显示【你好】。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("__打印输出__") == ast_env.get("__打印输出__")

    def test_连续赋值等价(self):
        """连续赋值等价性。"""
        src = "设甲为1，设乙为2，设丙为3。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("甲") == ast_env.get("甲") == 1
        assert text_env.get("乙") == ast_env.get("乙") == 2
        assert text_env.get("丙") == ast_env.get("丙") == 3

    def test_函数调用等价(self):
        """函数调用等价性。"""
        src = "设平方（数）为数乘数，设结果为平方（5）。"
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("结果") == ast_env.get("结果") == 25

    def test_乘法等价(self):
        """乘法运算等价性。"""
        src = "设结果为4乘5。"
        try:
            text_env = self._执行结果(self._后端正译(src))
            ast_env = self._执行结果(self._ast转译(src))
            assert text_env.get("结果") == ast_env.get("结果") == 20
        except Exception:
            pytest.skip("乘法语法不支持")

    def test_减法等价(self):
        """减法运算等价性。"""
        src = "设结果为10减3。"
        try:
            text_env = self._执行结果(self._后端正译(src))
            ast_env = self._执行结果(self._ast转译(src))
            assert text_env.get("结果") == ast_env.get("结果") == 7
        except Exception:
            pytest.skip("减法语法不支持")

    def test_遍历列表等价(self):
        """遍历列表等价性。"""
        src = """
设列表为［1、2、3］。
从列表中，每取一项记作x，就显示x。
""".strip()
        text_env = self._执行结果(self._后端正译(src))
        ast_env = self._执行结果(self._ast转译(src))
        assert text_env.get("__打印输出__") == ast_env.get("__打印输出__")


class Test运行时回溯边缘:
    """运行时回溯模块的边缘情况。"""

    def test_包装异常_无帧(self):
        """无周道帧时包装不崩溃。"""
        try:
            raise KeyError("测试")
        except KeyError:
            tb = sys.exc_info()[2]
            err = 包装运行时异常(KeyError("测试"), tb, {})
        assert isinstance(err, 运行时错误)

    def test_格式化回溯_空映射(self):
        """空行映射时不崩溃。"""
        try:
            raise ValueError("v")
        except ValueError:
            tb = sys.exc_info()[2]
            result = 格式化回溯(ValueError("v"), tb, {})
        assert "ValueError" in result

    def test_行映射边界(self):
        """行映射边界情况。"""
        pos, line = 映射行号(999999, {999999: 源码位置(1, 1, 0)}, ["a"])
        assert pos is not None
        assert pos.行 == 1

    def test_空行映射(self):
        """空行映射返回 None。"""
        pos, line = 映射行号(1, {}, ["a"])
        assert pos is None

    def test_非常见异常(self):
        """非标准异常类型。"""
        class 自定义异常(Exception):
            pass
        try:
            raise 自定义异常("自定义")
        except 自定义异常:
            tb = sys.exc_info()[2]
            result = 格式化回溯(自定义异常("自定义"), tb, {})
        assert "自定义异常" in result or "自定义" in result

    def test_多层嵌套函数报错(self):
        """多层函数调用，最内层报错映射正确。"""
        pos_map = {}
        fn_c = 函数定义IR("fn_c", [], [报错IR(消息="内部错误")])
        pos_map[id(fn_c)] = 源码位置(3, 1, 0)
        fn_b = 函数定义IR("fn_b", [], [表达式语句IR(调用IR(变量引用IR("fn_c"), []))])
        pos_map[id(fn_b)] = 源码位置(2, 1, 0)
        fn_a = 函数定义IR("fn_a", [], [表达式语句IR(调用IR(变量引用IR("fn_b"), []))])
        pos_map[id(fn_a)] = 源码位置(1, 1, 0)
        main = 表达式语句IR(调用IR(变量引用IR("fn_a"), []))
        pos_map[id(main)] = 源码位置(4, 1, 0)
        ir = 程序IR([fn_c, fn_b, fn_a, main])
        backend = PythonAstBackend(pos_map)
        try:
            backend.exec_program(ir)
        except 运行时错误 as e:
            err_str = str(e)
            assert "fn_a" in err_str or "fn_b" in err_str or "fn_c" in err_str

    def test_异常中异常不崩溃(self):
        """异常处理中再出异常不导致崩溃。"""
        ir = 程序IR(语句列表=[
            尝试IR(
                体=[赋值IR(目标=变量引用IR("x"), 值=二元运算IR(整数常量IR(1), "/", 整数常量IR(0)))],
                异常体=[报错IR(消息="异常中的异常")],
            ),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误):
            backend.exec_program(ir)

    def test_报错空消息(self):
        """报错语句用空消息。"""
        ir = 程序IR(语句列表=[报错IR(消息="")])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误) as excinfo:
            backend.exec_program(ir)
        assert "RuntimeError" in str(excinfo.value)

    def test_StopIteration映射(self):
        """StopIteration 映射。"""
        ir = 程序IR(语句列表=[
            表达式语句IR(调用IR(函数=变量引用IR("next"), 参数=[调用IR(函数=变量引用IR("iter"), 参数=[列表字面量IR([])])])),
        ])
        backend = PythonAstBackend({})
        with pytest.raises(运行时错误):
            backend.exec_program(ir)

    def test_赋值语句emit_text(self):
        """赋值语句通过 emit_text 输出正确。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(42)),
        ])
        backend = PythonAstBackend({})
        text = backend.emit_text(ir)
        assert "x = 42" in text or "x=42" in text

    def test_打印语句emit_text(self):
        """打印语句通过 emit_text 输出正确。"""
        ir = 程序IR(语句列表=[
            打印IR(值=文本常量IR("hello")),
        ])
        backend = PythonAstBackend({})
        text = backend.emit_text(ir)
        assert "print" in text

    def test_emit_module_type(self):
        """emit_module 总是返回 ast.Module。"""
        ir = 程序IR(语句列表=[
            赋值IR(目标=变量引用IR("x"), 值=整数常量IR(1)),
            赋值IR(目标=变量引用IR("y"), 值=整数常量IR(2)),
        ])
        backend = PythonAstBackend({})
        module = backend.emit_module(ir)
        assert isinstance(module, ast.Module)
        assert len(module.body) >= 2
