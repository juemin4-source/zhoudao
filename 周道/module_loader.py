"""周道模块加载器 v0.0.8

加载管线：读取 .zd 源码 → Lexer → Parser → Lowering → Semantic Analysis
→ Python AST Backend → 执行模块初始化 → 建立模块对象
"""

from __future__ import annotations
import os
import sys
import types
from typing import Any

from .lexer import 扫描
from .parser import 解析器
from .lowering import 降低
from .semantic_analyzer import 分析 as 语义分析
from .ast_backend import PythonAstBackend
from .errors import 周道错误, 语法错误, 语义错误
from .core_ir import 文章类型, 程序入口IR, 公开声明IR, 本地模块引入IR
from .module_resolver import ModuleResolver
from .module_registry import ModuleRegistry, 循环引入错误


class ModuleLoader:
    """周道模块加载器。

    负责加载、编译、缓存周道模块，以及管理运行入口的隔离执行。
    """

    def __init__(self, 模块根目录: list[str] | None = None):
        self.resolver = ModuleResolver(模块根目录)
        self.registry = ModuleRegistry()
        self._跨模块映射: dict[str, dict[int, Any]] = {}  # 文件路径 → 行映射

    # ── 核心加载 ──

    def load_module(self, 模块名: str, 当前目录: str) -> dict[str, Any]:
        """加载一个周道模块，返回其公开成员字典。

        Args:
            模块名: 模块名（《工具》→ "工具"）
            当前目录: 当前文章所在目录

        Returns:
            模块的公开成员字典

        Raises:
            循环引入错误: 循环引入检测
            周道错误: 编译或运行时错误
        """
        路径 = self.resolver.resolve(模块名, 当前目录)
        if 路径 is None:
            raise 周道错误(f"未找到周道模块「{模块名}」")

        # 缓存命中
        if self.registry.is_loaded(路径):
            return self.registry.get_module(路径)

        # 循环检测
        self.registry.开始加载(路径)

        try:
            # 编译
            with open(路径, "r", encoding="utf-8") as f:
                源码 = f.read()

            tokens = 扫描(源码)
            parser = 解析器(tokens)
            surface_ast = parser.解析()
            result = 降低(surface_ast)
            ir = result.ir
            位置映射 = result.位置映射

            # 递归加载模块依赖
            for stmt in ir.语句列表:
                if isinstance(stmt, 本地模块引入IR):
                    self.load_module(stmt.模块名, 当前目录)

            # 语义分析
            sem_prog = 语义分析(ir, 位置映射)
            if sem_prog.有错误:
                diagnostics = sem_prog.格式化诊断()
                raise 语义错误(f"模块「{模块名}」语义错误：\n{diagnostics}")

            # 标记文章类型
            ir.模块路径 = 路径
            if ir.文章类型 == 文章类型.自由:
                # 自动检测结构化模式
                has_entry = any(isinstance(s, 程序入口IR) for s in ir.语句列表)
                has_public = any(isinstance(s, 公开声明IR) for s in ir.语句列表)
                if has_entry:
                    ir.文章类型 = 文章类型.程序
                elif has_public:
                    ir.文章类型 = 文章类型.模块

            # 编译并初始化（跳过运行入口）
            backend = PythonAstBackend(位置映射, 源码=源码)
            code = self._编译模块(backend, ir, 路径)

            # 执行模块初始化（只执行顶层定义）
            模块环境: dict = {"__name__": f"__周道__{模块名}__", "__spec__": None}
            exec(code, 模块环境)

            # 提取公开成员
            公开成员 = self._提取公开成员(ir, 模块环境)

            # 缓存
            self.registry.register(路径, 公开成员)
            self._跨模块映射[路径] = backend.行映射

            return 公开成员

        finally:
            self.registry.完成加载(路径)

    def _编译模块(self, backend: PythonAstBackend, ir, 路径: str) -> types.CodeType:
        """编译模块代码（跳过运行入口）。"""
        # 过滤掉 程序入口IR 语句
        过滤语句 = [s for s in ir.语句列表 if not isinstance(s, 程序入口IR)]
        ir.语句列表 = 过滤语句
        module = backend.emit_module(ir)
        return compile(module, 路径, 'exec')

    def _提取公开成员(self, ir, 模块环境: dict) -> dict[str, Any]:
        """从模块环境中提取公开成员。"""
        # 查找 公开声明IR
        公开名称: set[str] = set()
        for s in ir.语句列表:
            if isinstance(s, 公开声明IR):
                公开名称.update(s.名称)

        if 公开名称:
            # 显式公开模式：只返回列表中的名称
            return {name: 模块环境.get(name) for name in 公开名称 if name in 模块环境}

        # 默认公开模式：返回所有顶层普通绑定（非内部名称）
        result = {}
        for k, v in 模块环境.items():
            if not k.startswith("__"):
                result[k] = v
        return result

    # ── 程序执行 ──

    def run_program(self, 文件路径: str) -> dict[str, Any]:
        """执行一个周道程序文（执行运行入口）。"""
        当前目录 = os.path.dirname(os.path.abspath(文件路径))

        with open(文件路径, "r", encoding="utf-8") as f:
            源码 = f.read()

        tokens = 扫描(源码)
        parser = 解析器(tokens)
        surface_ast = parser.解析()
        result = 降低(surface_ast)
        ir = result.ir
        位置映射 = result.位置映射

        # 递归加载模块依赖
        for stmt in ir.语句列表:
            if isinstance(stmt, 本地模块引入IR):
                self.load_module(stmt.模块名, 当前目录)

        sem_prog = 语义分析(ir, 位置映射)
        if sem_prog.有错误:
            raise 语义错误(f"语义错误：\n{sem_prog.格式化诊断()}")

        # 标记路径
        ir.模块路径 = os.path.abspath(文件路径)

        backend = PythonAstBackend(位置映射, 源码=源码)
        # exec_program 执行全部语句（包括运行入口）
        return backend.exec_program(sem_prog, 源码=源码)

    # ── 跨模块映射 ──

    def 获取行映射(self, 文件路径: str) -> dict[int, Any] | None:
        return self._跨模块映射.get(文件路径)
