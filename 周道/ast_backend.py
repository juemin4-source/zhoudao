"""周道 v0.0.7: PythonAstBackend — 直接构造 Python ast.AST。

从 Core IR / SemanticProgram 直接构造 Python ast.AST 节点，
替代字符串拼接作为正式执行路径。

设计原则：
- 不 import Surface AST（ast_nodes.py）
- 不重新执行语义分析
- 不根据中文关键词判断语义
- 所有用户来源节点设置完整位置信息
- 运行时异常映射回周道源码位置

双重后端角色：
  PythonAstBackend — 正式执行路径
  LegacyTextBackend（发射器）— 调试/差分对照
"""

from __future__ import annotations

import ast
import sys
import types
from typing import Any

from .core_ir import (
    程序IR, 语句IR, 表达式IR,
    赋值IR, 算术赋值IR, 打印IR,
    如果IR, 当循环IR, 遍历IR, 尝试IR,
    跳出IR, 继续IR, 以所得IR, 函数定义IR,
    引入IR, 从中引入IR, 导入别名IR,
    断言IR, 类别声明IR, 类别字段IR,
    删除IR, 空操作IR, 报错IR, 依次给出IR,
    等待语句IR, 全局声明IR, 外层声明IR,
    最终收束IR, 分情形IR, 表达式语句IR, 公开声明IR, 程序入口IR, 本地模块引入IR, 从本地模块引入IR, 异步遍历IR, 等待记作IR, 原样报出IR, 类别方法IR,
    整数常量IR, 小数常量IR, 文本常量IR,
    布尔常量IR, 空值IR,
    列表字面量IR, 元组字面量IR, 集合字面量IR, 映射字面量IR,
    变量引用IR, 二元运算IR, 一元运算IR, 调用IR,
    身份判断IR, 等待表达式IR, 当前错误IR, 错误文本IR,
    成员访问IR, 字符串下标IR, 表达式下标IR,
    切片下标IR,
)
from .errors import 源码位置, 周道错误, 运行时错误, 语义错误
from .semantic_program import SemanticProgram
from .runtime_traceback import 包装运行时异常
from .method_aliases import 是否已知别名 as _是否已知别名
from .backend_source_map import BackendSourceMap, SourceMapRecord


# ── 算符映射表 ──────────────────────────────────────────────

# 二元算符 → ast 算符（用于 ast.BinOp）
_二元算符映射: dict[str, type[ast.operator]] = {
    "+": ast.Add, "-": ast.Sub, "*": ast.Mult, "/": ast.Div,
    "//": ast.FloorDiv, "%": ast.Mod, "**": ast.Pow,
    "<<": ast.LShift, ">>": ast.RShift,
    "|": ast.BitOr, "^": ast.BitXor, "&": ast.BitAnd,
}

# 比较算符（用于 ast.Compare）
# is/is not 由身份判断IR处理；但降低器会产生 二元运算IR(算符="is")
# 用于 "甲没有值" 这种模式，所以此处也保留 is
_比较算符映射: dict[str, type[ast.cmpop]] = {
    "==": ast.Eq, "!=": ast.NotEq,
    "<": ast.Lt, "<=": ast.LtE, ">": ast.Gt, ">=": ast.GtE,
    "in": ast.In, "not_in": ast.NotIn,
    "is": ast.Is,
}

# 布尔算符（and / or — 用 BoolOp 节点表达）
_布尔算符映射: dict[str, type[ast.boolop]] = {
    "and": ast.And,
    "or": ast.Or,
}

# 算术赋值算符
_算术赋值映射: dict[str, type[ast.operator]] = {
    "+": ast.Add, "-": ast.Sub, "*": ast.Mult, "/": ast.Div,
    "//": ast.FloorDiv, "%": ast.Mod,
}


# ================================================================
# PythonAstBackend
# ================================================================

class PythonAstBackend:
    """Core IR / SemanticProgram → Python ast.AST 后端。

    接收 SemanticProgram（正式）或 程序IR（语法测试），
    直接构造 Python ast.AST 节点。不拼接字符串。
    """

    def __init__(self, 位置映射: dict[int, 源码位置] | None = None,
                 源码: str | None = None):
        self.位置映射 = 位置映射 or {}
        self.源码 = 源码

        # 行号计数器（1-based, 每发射一条语句 +1）
        self._next_line: int = 1

        # 行映射：generated_line → 源码位置
        # 用于运行时异常追溯回周道原文
        self.行映射: dict[int, 源码位置] = {}

        # 异常处理中使用的错误变量名（由 _当前异常名 追踪）
        self._当前异常名: str | None = None

        # 标记各类需要在模块顶层预先产生的导入
        self._需要顶层导入: list[ast.stmt] = []
        self._类别方法self名: str | None = None
        self._错误类型映射: dict[str, str] = {"运行出错": "RuntimeError", "值出错": "ValueError", "类型出错": "TypeError", "键出错": "KeyError", "索引出错": "IndexError", "文件未找到出错": "FileNotFoundError"}
        # 013 阶段 D: 后端源码映射
        self.源码映射: BackendSourceMap = BackendSourceMap()

    # ── 位置管理 ─────────────────────────────────────────────

    def _new_line(self, 位置: 源码位置 | None = None) -> int:
        """分配一个新的行号并记录位置映射。"""
        line = self._next_line
        self._next_line += 1
        if 位置 is not None:
            self.行映射[line] = 位置
        return line

    def _取源码位置(self, ir_node) -> 源码位置 | None:
        """从位置映射获取 IR 节点的周道源码位置。"""
        if ir_node is None:
            return None
        return self.位置映射.get(id(ir_node))

    def _设位置(self, node: ast.AST, line: int, col: int = 0,
                 end_line: int | None = None, end_col: int = 0) -> None:
        """在 AST 节点上设置位置信息。"""
        node.lineno = line
        node.col_offset = col
        node.end_lineno = end_line if end_line is not None else line
        node.end_col_offset = end_col

    def _设节点位置(self, node: ast.AST, ir_node) -> None:
        """从 IR 节点取周道位置并设到 AST 节点上。同时记录源码映射。"""
        pos = self._取源码位置(ir_node)
        if pos is not None:
            py_col = max(0, pos.列 - 1)
            self._设位置(node, pos.行, py_col, pos.行, py_col + 1)
        self._记录映射(node, ir_node)

    # ── 源码映射 ──────────────────────────────────────────

    def _记录映射(self, py_node: ast.AST, ir_node=None,
                  is_synthetic: bool = False,
                  synthetic_reason: str = "") -> None:
        if not hasattr(py_node, 'lineno'):
            return
        周道位置 = self._取源码位置(ir_node) if ir_node is not None else None
        origin_id = id(ir_node) if ir_node is not None else None
        self.源码映射.add_mapping(
            backend_node_id=id(py_node), python_node=py_node,
            周道位置=周道位置, origin_node_id=origin_id,
            is_synthetic=is_synthetic, synthetic_reason=synthetic_reason,
        )

    # ── 入口 ─────────────────────────────────────────────────

    def emit_module(self, 输入: 程序IR | SemanticProgram) -> ast.Module:
        """生成完整的 Python AST 模块。

        Args:
            输入: Core IR 程序（语法测试）或 SemanticProgram（正式路径）

        Returns:
            可直接 compile() 的 ast.Module

        Raises:
            语义错误: 当输入为含语义错误的 SemanticProgram 时
        """
        if isinstance(输入, SemanticProgram):
            if 输入.有错误:
                raise 语义错误(
                    "不能发射包含语义错误的程序。"
                    f"发现 {len(输入.全部错误())} 个错误。"
                )
            ir = 输入.core_ir
        else:
            ir = 输入

        # 重置状态
        self._next_line = 1
        self.行映射 = {}
        self._当前异常名 = None
        self._需要顶层导入 = []

        # v0.0.9: 收集类别方法
        类别方法分组: dict = {}
        for stmt in ir.语句列表:
            if isinstance(stmt, 类别方法IR):
                类别方法分组.setdefault(stmt.类别名, []).append(stmt)
        self._类别方法分组 = 类别方法分组

        body: list[ast.stmt] = []
        for stmt in ir.语句列表:
            if isinstance(stmt, 类别方法IR):
                continue
            result = self._发射语句(stmt)
            if result is not None:
                if isinstance(result, list):
                    body.extend(result)
                else:
                    body.append(result)

        # 顶层导入插入最前
        body = self._需要顶层导入 + body

        module = ast.Module(body=body, type_ignores=[])
        ast.fix_missing_locations(module)
        return module

    def emit_text(self, 输入: 程序IR | SemanticProgram) -> str:
        """生成 Python 源码文本（用于调试 / 差分对照）。"""
        module = self.emit_module(输入)
        return ast.unparse(module)

    def compile_program(self, 输入: 程序IR | SemanticProgram) -> types.CodeType:
        """生成并编译为 Python 字节码。"""
        module = self.emit_module(输入)
        return compile(module, '<周道>', 'exec')

    def exec_program(self, 输入: 程序IR | SemanticProgram,
                     全局变量: dict | None = None,
                     源码: str | None = None) -> dict:
        """编译并执行，运行异常时自动将位置映射回周道源码。

        使用 runtime_traceback 模块提供全栈帧映射与周道源码上下文。

        Args:
            输入: Core IR 程序或 SemanticProgram
            全局变量: 可选的全局变量字典
            源码: 原始周道源码（可选，提供后可显示源码片段与列指示器）

        Returns:
            执行后的全局变量字典

        Raises:
            运行时错误: 携带原始异常和完整的周道源码回溯
        """
        module = self.emit_module(输入)
        code = compile(module, '<周道>', 'exec')

        环境: dict = {"__name__": "__周道__"}
        import sys as _sys, types as _types
        if "__周道__" not in _sys.modules:
            _sys.modules["__周道__"] = _types.ModuleType("__周道__")
        _sys.modules["__周道__"].__dict__.update(环境)
        if 全局变量:
            环境.update(全局变量)
        # 注入运行时助手（单一事实源）
        from .runtime_environment import 注入运行时助手
        注入运行时助手(环境)

        try:
            exec(code, 环境)
        except Exception:
            raise 包装运行时异常(
                sys.exc_info()[1], sys.exc_info()[2],
                self.行映射, 源码,
            ) from sys.exc_info()[1]

        return 环境

    # ============================================================
    # 语句发射
    # ============================================================

    def _发射语句(self, node: 语句IR) -> ast.stmt | list[ast.stmt] | None:
        """根据 Core IR 语句类型分发。"""
        if isinstance(node, 赋值IR):
            return self._发射赋值(node)
        elif isinstance(node, 算术赋值IR):
            return self._发射算术赋值(node)
        elif isinstance(node, 打印IR):
            return self._发射打印(node)
        elif isinstance(node, 如果IR):
            return self._发射如果(node)
        elif isinstance(node, 当循环IR):
            return self._发射当循环(node)
        elif isinstance(node, 遍历IR):
            return self._发射遍历(node)
        elif isinstance(node, 尝试IR):
            return self._发射尝试(node)
        elif isinstance(node, 跳出IR):
            return self._发射跳出(node)
        elif isinstance(node, 继续IR):
            return self._发射继续(node)
        elif isinstance(node, 以所得IR):
            return self._发射以所得(node)
        elif isinstance(node, 函数定义IR):
            return self._发射函数(node)
        elif isinstance(node, 引入IR):
            return self._发射引入(node)
        elif isinstance(node, 从中引入IR):
            return self._发射从中引入(node)
        elif isinstance(node, 导入别名IR):
            return self._发射导入别名(node)
        elif isinstance(node, 断言IR):
            return self._发射断言(node)
        elif isinstance(node, 类别声明IR):
            return self._发射类别(node)
        elif isinstance(node, 删除IR):
            return self._发射删除(node)
        elif isinstance(node, 空操作IR):
            return self._发射空操作(node)
        elif isinstance(node, 报错IR):
            return self._发射报错(node)
        elif isinstance(node, 依次给出IR):
            return self._发射依次给出(node)
        elif isinstance(node, 等待语句IR):
            return self._发射等待语句(node)
        elif isinstance(node, 全局声明IR):
            return self._发射全局声明(node)
        elif isinstance(node, 外层声明IR):
            return self._发射外层声明(node)
        elif isinstance(node, 最终收束IR):
            return self._发射最终收束(node)
        elif isinstance(node, 分情形IR):
            return self._发射分情形(node)
        elif isinstance(node, 程序入口IR):
            return self._发射语句列表(node.体)
        elif isinstance(node, 公开声明IR):
            return None
        elif isinstance(node, 本地模块引入IR):
            return None
        elif isinstance(node, 从本地模块引入IR):
            return None
        elif isinstance(node, 原样报出IR):
            return self._发射原样报出(node)
        elif isinstance(node, 等待记作IR):
            return self._发射等待记作(node)
        elif isinstance(node, 异步遍历IR):
            return self._发射异步遍历(node)
        elif isinstance(node, 类别方法IR):
            return self._发射类别方法(node)
        elif isinstance(node, 表达式语句IR):
            return self._发射表达式语句(node)
        else:
            raise 周道错误(
                f"未知 Core IR 语句类型：{type(node).__name__}"
            )

    def _发射语句列表(self, stmts: list[语句IR]) -> list[ast.stmt]:
        """发射一组语句。"""
        result: list[ast.stmt] = []
        for s in stmts:
            r = self._发射语句(s)
            if r is not None:
                if isinstance(r, list):
                    result.extend(r)
                else:
                    result.append(r)
        return result

    # ==================== 简单语句 ====================

    def _发射赋值(self, node: 赋值IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        target = self._发射表达式(node.目标, ctx=ast.Store())
        if node.值 is None:
            value: ast.expr = ast.Constant(value=None)
            self._设节点位置(value, node.目标)
        else:
            value = self._发射表达式(node.值)
        n = ast.Assign(targets=[target], value=value)
        self._设位置(n, line)
        return n

    def _发射算术赋值(self, node: 算术赋值IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        target = self._发射表达式(node.目标, ctx=ast.Store())
        value = self._发射表达式(node.值)
        # Core IR 算符为 "+= " -= " *= " 等形式，去掉末尾 "="
        op_key = node.算符.rstrip("=")
        op_class = _算术赋值映射.get(op_key)
        if op_class is None:
            raise 周道错误(f"未知算术赋值算符：{node.算符}")
        n = ast.AugAssign(target=target, op=op_class(), value=value)
        self._设位置(n, line)
        return n

    def _发射打印(self, node: 打印IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        value = self._发射表达式(node.值)
        # 用 str() 包装（兼容所有 exec 环境，runtime 通过重写 str 实现中文显示）
        shown = ast.Call(
            func=ast.Name(id="str", ctx=ast.Load()),
            args=[value], keywords=[],
        )
        call = ast.Call(
            func=ast.Name(id="print", ctx=ast.Load()),
            args=[shown], keywords=[],
        )
        self._设节点位置(call.func, node)
        n = ast.Expr(value=call)
        self._设位置(n, line)
        return n

    def _发射跳出(self, node: 跳出IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        n = ast.Break()
        self._设位置(n, line)
        return n

    def _发射继续(self, node: 继续IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        n = ast.Continue()
        self._设位置(n, line)
        return n

    def _发射以所得(self, node: 以所得IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        value = self._发射表达式(node.值)
        n = ast.Return(value=value)
        self._设位置(n, line)
        return n

    def _发射删除(self, node: 删除IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        target = self._发射表达式(node.目标, ctx=ast.Del())
        n = ast.Delete(targets=[target])
        self._设位置(n, line)
        return n

    def _发射空操作(self, node: 空操作IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        n = ast.Pass()
        self._设位置(n, line)
        return n

    def _发射报错(self, node: 报错IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        exc_name = "RuntimeError"
        if node.错误类型:
            exc_name = self._错误类型映射.get(node.错误类型, "RuntimeError")
        exc_call = ast.Call(
            func=ast.Name(id=exc_name, ctx=ast.Load()),
            args=[ast.Constant(value=node.消息)],
            keywords=[],
        )
        self._设节点位置(exc_call.func, node)
        n = ast.Raise(exc=exc_call, cause=None)
        self._设位置(n, line)
        return n


    def _发射原样报出(self, node: 原样报出IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        n = ast.Raise(exc=None, cause=None)
        self._设位置(n, line)
        return n

    def _发射等待记作(self, node: 等待记作IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        call = self._发射表达式(node.调用)
        aw = ast.Await(value=call)
        n = ast.Assign(targets=[ast.Name(id=node.记作名, ctx=ast.Store())], value=aw)
        self._设位置(n, line)
        return n

    def _发射异步遍历(self, node: 异步遍历IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        target = ast.Name(id=node.元素, ctx=ast.Store())
        self._设节点位置(target, node)
        iter_expr = self._发射表达式(node.集合)
        body = self._发射语句列表(node.体)
        n = ast.AsyncFor(target=target, iter=iter_expr, body=body, orelse=[])
        self._设位置(n, line)
        return n

    def _发射类别方法(self, node: 类别方法IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        inner_self = "__zd_self"
        old = self._类别方法self名
        self._类别方法self名 = inner_self
        func_args = ast.arguments(
            posonlyargs=[], args=[ast.arg(arg=inner_self)] + [ast.arg(arg=p) for p in node.参数],
            kwonlyargs=[], kw_defaults=[], defaults=[])
        func_body = self._发射语句列表(node.体)
        self._类别方法self名 = old
        if node.是异步:
            n = ast.AsyncFunctionDef(name=node.名称, args=func_args, body=func_body, decorator_list=[], returns=None)
        else:
            n = ast.FunctionDef(name=node.名称, args=func_args, body=func_body, decorator_list=[], returns=None)
        self._设位置(n, line)
        return n

    def _发射依次给出(self, node: 依次给出IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        value = self._发射表达式(node.值)
        n = ast.Expr(value=ast.Yield(value=value))
        self._设位置(n, line)
        return n

    def _发射等待语句(self, node: 等待语句IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        call = self._发射表达式(node.调用)
        n = ast.Expr(value=ast.Await(value=call))
        self._设位置(n, line)
        return n

    def _发射表达式语句(self, node: 表达式语句IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        expr = self._发射表达式(node.表达式)
        n = ast.Expr(value=expr)
        self._设位置(n, line)
        return n

    # ==================== 复合语句 ====================

    def _发射如果(self, node: 如果IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        test = self._发射表达式(node.条件)
        body = self._发射语句列表(node.则)

        # 构建 elif 链：从最内层开始向外嵌套
        # elif cond2: body2 | elif cond1: body1 | if test: body
        # → ast.If(test, body1, orelse=[ast.If(cond2, body2, orelse=[])])
        elif_chain: list[ast.stmt] | None = None
        if node.否则:
            elif_chain = self._发射语句列表(node.否则)

        # 逆序遍历 elif 分支，从最内层开始嵌套
        for cond, body_stmts in reversed(node.否则如果):
            elif_test = self._发射表达式(cond)
            elif_body = self._发射语句列表(body_stmts)
            elif_chain = [ast.If(
                test=elif_test, body=elif_body,
                orelse=elif_chain if elif_chain else [],
            )]

        orelse = elif_chain if elif_chain else []

        n = ast.If(test=test, body=body, orelse=orelse)
        self._设位置(n, line)
        return n

    def _发射当循环(self, node: 当循环IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        test = self._发射表达式(node.条件)
        body = self._发射语句列表(node.体)
        n = ast.While(test=test, body=body, orelse=[])
        self._设位置(n, line)
        return n

    def _发射遍历(self, node: 遍历IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        target = ast.Name(id=node.元素, ctx=ast.Store())
        self._设节点位置(target, node)
        iter_expr = self._发射表达式(node.集合)
        body = self._发射语句列表(node.体)
        n = ast.For(target=target, iter=iter_expr, body=body, orelse=[])
        self._设位置(n, line)
        return n

    def _发射尝试(self, node: 尝试IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        body = self._发射语句列表(node.体)

        handlers: list[ast.ExceptHandler] = []
        old_exc_name = self._当前异常名

        # v0.0.9: 分类捕获
        if node.错误类型处理:
            for 类型名, 处理体 in node.错误类型处理:
                py_type = self._错误类型映射.get(类型名, "Exception")
                exc_name = "_err_" + 类型名
                self._当前异常名 = exc_name
                handler_body = self._发射语句列表(处理体)
                handler = ast.ExceptHandler(
                    type=ast.Name(id=py_type, ctx=ast.Load()),
                    name=exc_name,
                    body=handler_body,
                )
                handlers.append(handler)

        # v0.0.9: 泛化捕获
        if node.有泛化处理 and node.异常体:
            exc_name = node.异常名 or "_err"
            self._当前异常名 = exc_name
            handler_body = self._发射语句列表(node.异常体)
            handler = ast.ExceptHandler(
                type=ast.Name(id="Exception", ctx=ast.Load()),
                name=exc_name,
                body=handler_body,
            )
            handlers.append(handler)
            self._当前异常名 = old_exc_name

        # 兼容旧语法
        if not node.错误类型处理 and not node.有泛化处理:
            if node.异常体:
                exc_name = node.异常名 or "_err"
                self._当前异常名 = exc_name
                handler_body = self._发射语句列表(node.异常体)
                handler = ast.ExceptHandler(
                    type=ast.Name(id="Exception", ctx=ast.Load()),
                    name=exc_name,
                    body=handler_body,
                )
                handlers.append(handler)
                self._当前异常名 = old_exc_name

        orelse: list[ast.stmt] = []
        finalbody = self._发射语句列表(node.最终体) if node.最终体 else []

        n = ast.Try(
            body=body,
            handlers=handlers,
            orelse=orelse,
            finalbody=finalbody,
        )
        self._设位置(n, line)
        return n

    def _发射函数(self, node: 函数定义IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        args = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=p) for p in node.参数],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[self._发射表达式(d) for d in node.参数默认值 if d is not None],
        )
        body = self._发射语句列表(node.体)

        decorator_list: list[ast.expr] = []
        returns: ast.expr | None = None

        n = ast.FunctionDef(
            name=node.名称,
            args=args,
            body=body,
            decorator_list=decorator_list,
            returns=returns,
        )
        self._设位置(n, line)

        if node.是异步 or node.是生成器:
            # 在 Python 3.12+ 中，async 函数用 ast.AsyncFunctionDef
            if node.是异步:
                async_n = ast.AsyncFunctionDef(
                    name=node.名称,
                    args=args,
                    body=body,
                    decorator_list=decorator_list,
                    returns=returns,
                )
                self._设位置(async_n, line)
                return async_n

        return n

    def _发射全局声明(self, node: 全局声明IR) -> list[ast.stmt] | ast.stmt:
        line = self._new_line(self._取源码位置(node))
        if not node.名称:
            return None
        n = ast.Global(names=list(node.名称))
        self._设位置(n, line)
        return n

    def _发射外层声明(self, node: 外层声明IR) -> list[ast.stmt] | ast.stmt:
        line = self._new_line(self._取源码位置(node))
        if not node.名称:
            return None
        n = ast.Nonlocal(names=list(node.名称))
        self._设位置(n, line)
        return n

    def _发射最终收束(self, node: 最终收束IR) -> list[ast.stmt]:
        return self._发射语句列表(node.体)

    # ==================== 引入 ====================

    # 中文→英文模块名映射（与 emitter.py 保持一致）
    _模块映射: dict[str, str] = {
        "随机": "random", "数学": "math", "时间": "time",
        "系统": "sys", "操作系统": "os", "路径": "pathlib",
        "正则": "re", "JSON": "json", "CSV": "csv",
        "HTTP": "http", "网络请求": "requests",
        "收藏": "collections", "类型提示": "typing",
        "数据类": "dataclasses",
    }

    # 中文→英文成员名映射
    _成员映射: dict[str, dict[str, str]] = {
        "随机": {
            "随机整数": "randint", "随机选择": "choice",
            "随机范围": "randrange", "统一随机": "uniform",
            "随机种子": "seed", "随机取样": "sample",
            "随机洗牌": "shuffle",
        },
        "数学": {
            "平方根": "sqrt", "正弦": "sin", "余弦": "cos",
            "正切": "tan", "向上取整": "ceil", "向下取整": "floor",
        },
        "__内置__": {
            "绝对值": "abs", "四舍五入": "round",
            "最大值": "max", "最小值": "min", "求和": "sum",
            "长度": "len", "范围": "range", "枚举": "enumerate",
            "排序": "sorted", "反转": "reversed",
            "过滤": "filter", "映射": "map", "压缩": "zip",
            "打印": "print", "输入": "input", "打开": "open",
            "类型": "type", "字符串": "str", "整数": "int",
            "小数": "float", "布尔": "bool", "列表": "list",
            "字典": "dict", "集合": "set", "元组": "tuple",
        },
    }

    def _发射引入(self, node: 引入IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        模块 = self._模块映射.get(node.模块, node.模块)
        n = ast.Import(names=[ast.alias(name=模块)])
        self._设位置(n, line)
        return n

    def _发射从中引入(self, node: 从中引入IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        模块 = self._模块映射.get(node.模块, node.模块)
        成员映射 = self._成员映射.get(node.模块, {})
        names: list[ast.alias] = []
        for n in node.名称:
            py_name = 成员映射.get(n, n)
            if py_name != n:
                names.append(ast.alias(name=py_name, asname=n))
            else:
                names.append(ast.alias(name=n, asname=None))
        n = ast.ImportFrom(module=模块, names=names, level=0)
        self._设位置(n, line)
        return n

    def _发射导入别名(self, node: 导入别名IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        模块 = self._模块映射.get(node.模块, node.模块)
        n = ast.Import(names=[ast.alias(name=模块, asname=node.别名)])
        self._设位置(n, line)
        return n

    # ==================== 断言 / 类别 / 分情形 ====================

    def _发射断言(self, node: 断言IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        test = self._发射表达式(node.表达式)
        msg: ast.Constant | None = None
        if node.消息:
            msg = ast.Constant(value=node.消息)
        n = ast.Assert(test=test, msg=msg)
        self._设位置(n, line)
        return n

    def _发射类别(self, node: 类别声明IR) -> list[ast.stmt]:
        """类别声明 → @dataclass class + 前置导入。"""
        line = self._new_line(self._取源码位置(node))

        # 生成前置导入（仅一次）
        if not self._需要顶层导入:
            self._需要顶层导入 = [
                ast.ImportFrom(
                    module="dataclasses",
                    names=[ast.alias(name="dataclass")],
                    level=0,
                ),
                ast.ImportFrom(
                    module="typing",
                    names=[ast.alias(name="Any")],
                    level=0,
                ),
            ]

        # 字段
        body: list[ast.stmt] = []
        has_validation = False
        for f in node.字段列表:
            ann = ast.Name(id=f.类型, ctx=ast.Load()) if f.类型 else ast.Name(id="Any", ctx=ast.Load())
            if f.可空:
                default = ast.Constant(value=None)
            elif f.默认值:
                default = self._发射表达式(f.默认值)
            else:
                default = None

            ann_assign = ast.AnnAssign(
                target=ast.Name(id=f.名称, ctx=ast.Store()),
                annotation=ann,
                value=default,
                simple=1,
            )
            self._设节点位置(ann_assign, node)
            body.append(ann_assign)

            if f.类型 or f.不得为负:
                has_validation = True

        if has_validation:
            # 生成 __post_init__
            post_body: list[ast.stmt] = []
            for f in node.字段列表:
                if f.类型:
                    check = ast.If(
                        test=ast.UnaryOp(
                            op=ast.Not(),
                            operand=ast.Call(
                                func=ast.Name(id="isinstance", ctx=ast.Load()),
                                args=[
                                    ast.Attribute(
                                        value=ast.Name(id="self", ctx=ast.Load()),
                                        attr=f.名称,
                                    ),
                                    ast.Name(id=f.类型, ctx=ast.Load()),
                                ],
                                keywords=[],
                            ),
                        ),
                        body=[ast.Raise(
                            exc=ast.Call(
                                func=ast.Name(id="TypeError", ctx=ast.Load()),
                                args=[ast.Constant(
                                    value=f"「{f.名称}」必须为 {f.类型}"
                                )],
                                keywords=[],
                            ),
                            cause=None,
                        )],
                        orelse=[],
                    )
                    post_body.append(check)
                if f.不得为负:
                    neg_check = ast.If(
                        test=ast.Compare(
                            left=ast.Attribute(
                                value=ast.Name(id="self", ctx=ast.Load()),
                                attr=f.名称,
                            ),
                            ops=[ast.Lt()],
                            comparators=[ast.Constant(value=0)],
                        ),
                        body=[ast.Raise(
                            exc=ast.Call(
                                func=ast.Name(id="ValueError", ctx=ast.Load()),
                                args=[ast.Constant(
                                    value=f"「{f.名称}」不得为负"
                                )],
                                keywords=[],
                            ),
                            cause=None,
                        )],
                        orelse=[],
                    )
                    post_body.append(neg_check)

            post_fn = ast.FunctionDef(
                name="__post_init__",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self")],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=post_body,
                decorator_list=[],
                returns=None,
            )
            body.append(post_fn)

                # 注入类别实例方法
        if hasattr(self, "_类别方法分组"):
            for 方法 in self._类别方法分组.get(node.名称, []):
                body.append(self._发射类别方法(方法))

        # 装饰器 @dataclass(kw_only=True)
        decorator = ast.Call(
            func=ast.Name(id="dataclass", ctx=ast.Load()),
            args=[],
            keywords=[ast.keyword(
                arg="kw_only",
                value=ast.Constant(value=True),
            )],
        )

        class_def = ast.ClassDef(
            name=node.名称,
            bases=[],
            keywords=[],
            body=body,
            decorator_list=[decorator],
        )
        self._设位置(class_def, line)
        return [class_def]

    def _发射分情形(self, node: 分情形IR) -> ast.stmt:
        line = self._new_line(self._取源码位置(node))
        subject = self._发射表达式(node.对象)

        cases: list[ast.match_case] = []
        for val, body_stmts in node.分支列表:
            if val is None:
                # 其余 → case _:
                pattern: ast.pattern = ast.MatchSingleton(value=None)
                # Python 3.10+ uses MatchSingleton for _
                # Actually, wildcard pattern in Python is:
                pattern = ast.MatchAs(pattern=None, name=None)
            else:
                pattern_val = self._发射表达式(val)
                pattern = ast.MatchValue(value=pattern_val)

            case_body = self._发射语句列表(body_stmts)
            cases.append(ast.match_case(
                pattern=pattern,
                guard=None,
                body=case_body,
            ))

        match_n = ast.Match(subject=subject, cases=cases)
        self._设位置(match_n, line)
        return match_n

    # ============================================================
    # 表达式发射
    # ============================================================

    def _发射表达式(self, node: 表达式IR,
                    ctx: ast.ExprContext = ast.Load()) -> ast.expr:
        """发射 Core IR 表达式。

        Args:
            node: Core IR 表达式节点
            ctx: 上下文（Load/Store/Del），用于左值

        Returns:
            ast.expr 节点
        """
        if isinstance(node, 整数常量IR):
            return self._const(node.值, node)
        elif isinstance(node, 小数常量IR):
            return self._const(node.值, node)
        elif isinstance(node, 文本常量IR):
            return self._const(node.值, node)
        elif isinstance(node, 布尔常量IR):
            return self._const(node.值, node)
        elif isinstance(node, 空值IR):
            return self._const(None, node)
        elif isinstance(node, 列表字面量IR):
            return self._发射列表字面量(node)
        elif isinstance(node, 元组字面量IR):
            return self._发射元组字面量(node)
        elif isinstance(node, 集合字面量IR):
            return self._发射集合字面量(node)
        elif isinstance(node, 映射字面量IR):
            return self._发射映射字面量(node)
        elif isinstance(node, 变量引用IR):
            return self._发射变量引用(node, ctx)
        elif isinstance(node, 二元运算IR):
            return self._发射二元运算(node)
        elif isinstance(node, 一元运算IR):
            return self._发射一元运算(node)
        elif isinstance(node, 调用IR):
            return self._发射调用(node)
        elif isinstance(node, 身份判断IR):
            return self._发射身份判断(node)
        elif isinstance(node, 等待表达式IR):
            return self._发射等待表达式(node)
        elif isinstance(node, 当前错误IR):
            return self._发射当前错误(node)
        elif isinstance(node, 错误文本IR):
            return self._发射错误文本(node)
        elif isinstance(node, 成员访问IR):
            return self._发射成员访问(node, ctx)
        elif isinstance(node, 字符串下标IR):
            return self._发射字符串下标(node, ctx)
        elif isinstance(node, 表达式下标IR):
            return self._发射表达式下标(node, ctx)
        elif isinstance(node, 切片下标IR):
            return self._发射切片下标(node, ctx)
        else:
            raise 周道错误(
                f"未知 Core IR 表达式类型：{type(node).__name__}"
            )

    def _const(self, value: object, ir_node) -> ast.Constant:
        """创建常量节点。"""
        n = ast.Constant(value=value)
        self._设节点位置(n, ir_node)
        return n

    def _发射列表字面量(self, node: 列表字面量IR) -> ast.List:
        elts = [self._发射表达式(e) for e in node.元素]
        n = ast.List(elts=elts, ctx=ast.Load())
        self._设节点位置(n, node)
        return n

    def _发射元组字面量(self, node: 元组字面量IR) -> ast.Tuple:
        elts = [self._发射表达式(e) for e in node.元素]
        n = ast.Tuple(elts=elts, ctx=ast.Load())
        self._设节点位置(n, node)
        return n

    def _发射集合字面量(self, node: 集合字面量IR) -> ast.expr:
        elts = [self._发射表达式(e) for e in node.元素]
        if not elts:
            n = ast.Call(func=ast.Name(id='set', ctx=ast.Load()), args=[], keywords=[])
            self._设节点位置(n, node)
            return n
        n = ast.Set(elts=elts)
        self._设节点位置(n, node)
        return n

    def _发射映射字面量(self, node: 映射字面量IR) -> ast.Dict:
        keys = [self._发射表达式(k) for k, _ in node.条目]
        values = [self._发射表达式(v) for _, v in node.条目]
        n = ast.Dict(keys=keys, values=values)
        self._设节点位置(n, node)
        return n

    _前置映射: dict[str, str] = {
        # 纯函数名：永远映射
        "绝对值": "abs", "四舍五入": "round",
        "最大值": "max", "最小值": "min", "求和": "sum",
        "长度": "len", "范围": "range", "枚举": "enumerate",
        "排序": "sorted", "反转": "reversed",
        "过滤": "filter", "压缩": "zip",
        "打印": "print", "输入": "input", "打开": "open",
        # 类型名：仅在作为函数（构造器）使用时映射
        # 变量引用时不映射（避免覆盖用户变量名如 "映射"）
        # Gate B: 标准库函数
        "读取文本": "读取文本", "写入文本": "写入文本", "追加文本": "追加文本",
        "判断存在": "判断存在", "建立目录": "建立目录", "列出目录": "列出目录",
        "路径连接": "路径连接", "文件名": "文件名", "扩展名": "扩展名",
        "删除文件": "删除文件", "复制文件": "复制文件", "移动文件": "移动文件",
        "CSV读取": "CSV读取", "CSV写入": "CSV写入",
        "正则查找": "正则查找", "正则查找全部": "正则查找全部",
        "正则替换": "正则替换", "正则匹配": "正则匹配",
        "此刻时间": "此刻时间", "今日日期": "今日日期",
        "格式时间": "格式时间", "休眠": "休眠",
        "随机整数": "随机整数", "随机小数": "随机小数",
        "随机选择": "随机选择", "随机打乱": "随机打乱",
        "命令行参数": "命令行参数", "环境变量": "环境变量",
        "目前目录": "目前目录", "退出": "退出", "执行命令": "执行命令",
        "断言相等": "断言相等", "断言为真": "断言为真", "断言抛出错误": "断言抛出错误",
    }

    def _发射变量引用(self, node: 变量引用IR,
                       ctx: ast.ExprContext = ast.Load()) -> ast.Name:
        # v0.0.9: 类别方法中的 自己 → 内部 self 名
        name = node.名称
        if name == "自己" and self._类别方法self名:
            name = self._类别方法self名
        # 012: 内置函数名 → Python 标准库名
        if name in self._前置映射:
            name = self._前置映射[name]
        n = ast.Name(id=name, ctx=ctx)
        self._设节点位置(n, node)
        return n

    def _发射二元运算(self, node: 二元运算IR) -> ast.expr:
        left = self._发射表达式(node.左)
        right = self._发射表达式(node.右)

        # 布尔操作: and / or → ast.BoolOp
        bool_cls = _布尔算符映射.get(node.算符)
        if bool_cls is not None:
            n = ast.BoolOp(op=bool_cls(), values=[left, right])
            self._设节点位置(n, node)
            return n

        # 比较操作: == != < <= > >= in not_in → ast.Compare
        cmp_cls = _比较算符映射.get(node.算符)
        if cmp_cls is not None:
            n = ast.Compare(left=left, ops=[cmp_cls()], comparators=[right])
            self._设节点位置(n, node)
            return n

        # 常规二元操作: + - * / // % ** << >> | ^ & → ast.BinOp
        op_cls = _二元算符映射.get(node.算符)
        if op_cls is None:
            raise 周道错误(f"未知二元算符：{node.算符}")
        n = ast.BinOp(left=left, op=op_cls(), right=right)
        self._设节点位置(n, node)
        return n

    def _发射一元运算(self, node: 一元运算IR) -> ast.expr:
        operand = self._发射表达式(node.操作数)
        if node.算符 == "not":
            n = ast.UnaryOp(op=ast.Not(), operand=operand)
        elif node.算符 == "-":
            n = ast.UnaryOp(op=ast.USub(), operand=operand)
        elif node.算符 == "+":
            n = ast.UnaryOp(op=ast.UAdd(), operand=operand)
        else:
            raise 周道错误(f"未知一元算符：{node.算符}")
        self._设节点位置(n, node)
        return n

    def _发射调用(self, node: 调用IR) -> ast.Call:
        # 成员调用 → 已知别名走运行时解析器，否则发射正常属性访问
        if isinstance(node.函数, 成员访问IR):
            成员 = node.函数
            # 只在成员名是已知别名时使用运行时解析器
            if 成员.成员 in self._前置映射 or _是否已知别名(成员.成员):
                obj = self._发射表达式(成员.对象)
                packed_args = ast.Tuple(
                    elts=[self._发射表达式(p) for p in node.参数],
                    ctx=ast.Load(),
                )
                # 将制定参数打包为字典传递给 制定参数= 关键字
                kwargs_dict = ast.Dict(
                    keys=[ast.Constant(value=名称) for 名称, _ in node.制定参数],
                    values=[self._发射表达式(值) for _, 值 in node.制定参数],
                )
                n = ast.Call(
                    func=ast.Name(id="_zd_调用成员", ctx=ast.Load()),
                    args=[obj, ast.Constant(value=成员.成员), packed_args],
                    keywords=[ast.keyword(arg="制定参数", value=kwargs_dict)] if node.制定参数 else [],
                )
                self._设节点位置(n, node)
                return n
            # 非别名成员调用：正常的属性访问 + 调用
            func = self._发射表达式(node.函数)
            args = [self._发射表达式(p) for p in node.参数]
            kwargs = [
                ast.keyword(arg=名称, value=self._发射表达式(值))
                for 名称, 值 in node.制定参数
            ]
            n = ast.Call(func=func, args=args, keywords=kwargs)
            self._设节点位置(n, node)
            return n

        # 普通函数调用
        func = self._发射表达式(node.函数)
        args = [self._发射表达式(p) for p in node.参数]
        kwargs = [
            ast.keyword(arg=名称, value=self._发射表达式(值))
            for 名称, 值 in node.制定参数
        ]
        n = ast.Call(func=func, args=args, keywords=kwargs)
        self._设节点位置(n, node)
        return n

    def _发射身份判断(self, node: 身份判断IR) -> ast.expr:
        left = self._发射表达式(node.左)
        right = self._发射表达式(node.右)
        op = ast.Is() if node.肯定 else ast.IsNot()
        n = ast.Compare(left=left, ops=[op], comparators=[right])
        self._设节点位置(n, node)
        return n

    def _发射等待表达式(self, node: 等待表达式IR) -> ast.expr:
        call = self._发射表达式(node.调用)
        n = ast.Await(value=call)
        self._设节点位置(n, node)
        return n

    def _发射当前错误(self, node: 当前错误IR) -> ast.Name:
        name = self._当前异常名 or "_err"
        n = ast.Name(id=name, ctx=ast.Load())
        self._设节点位置(n, node)
        return n

    def _发射错误文本(self, node: 错误文本IR) -> ast.Call:
        name = self._当前异常名 or "_err"
        n = ast.Call(
            func=ast.Name(id="str", ctx=ast.Load()),
            args=[ast.Name(id=name, ctx=ast.Load())],
            keywords=[],
        )
        self._设节点位置(n, node)
        return n

    def _发射成员访问(self, node: 成员访问IR,
                       ctx: ast.ExprContext = ast.Load()) -> ast.Attribute:
        obj = self._发射表达式(node.对象)
        # 成员访问的 Store/Del 上下文由外层决定
        if isinstance(ctx, ast.Store):
            # ast.Attribute with Store context
            n = ast.Attribute(value=obj, attr=node.成员, ctx=ast.Store())
        elif isinstance(ctx, ast.Del):
            n = ast.Attribute(value=obj, attr=node.成员, ctx=ast.Del())
        else:
            n = ast.Attribute(value=obj, attr=node.成员, ctx=ast.Load())
        self._设节点位置(n, node)
        return n

    def _发射字符串下标(self, node: 字符串下标IR,
                         ctx: ast.ExprContext = ast.Load()) -> ast.Subscript:
        obj = self._发射表达式(node.对象)
        slice_node: ast.expr = ast.Constant(value=node.键)
        n = ast.Subscript(value=obj, slice=slice_node, ctx=ctx)
        self._设节点位置(n, node)
        return n

    def _发射表达式下标(self, node: 表达式下标IR,
                         ctx: ast.ExprContext = ast.Load()) -> ast.Subscript:
        obj = self._发射表达式(node.对象)
        idx = self._发射表达式(node.索引)
        n = ast.Subscript(value=obj, slice=idx, ctx=ctx)
        self._设节点位置(n, node)
        return n

    def _发射切片下标(self, node: 切片下标IR,
                       ctx: ast.ExprContext = ast.Load()) -> ast.Subscript:
        obj = self._发射表达式(node.对象)
        lower = self._发射表达式(node.开始) if node.开始 else None
        upper = self._发射表达式(node.结束) if node.结束 else None
        slice_node = ast.Slice(lower=lower, upper=upper, step=None)
        n = ast.Subscript(value=obj, slice=slice_node, ctx=ctx)
        self._设节点位置(n, node)
        return n
