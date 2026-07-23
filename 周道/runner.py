"""周道：运行器与 CLI。

统一管线：
  完整：源码 → Lexer → Parser → Surface AST → Lowering → Core IR
        → Semantic Analysis → SemanticProgram → Backend → Python
  仅语法（测试用）：源码 → Lexer → Parser → Surface AST → Lowering → Core IR → Backend → Python

后端：
  ast（默认） — PythonAstBackend：直接构造 Python ast.AST，正式执行路径
  text — 发射器（LegacyTextBackend）：字符串拼接，调试/差分对照
"""

from __future__ import annotations

import sys
import os
from typing import Literal

from .lexer import 扫描
from .parser import 解析器
from .lowering import 降低, 降低_仅语法
from .semantic_analyzer import 分析 as 语义分析
from .emitter import 发射器
from .ast_backend import PythonAstBackend
from .errors import 周道错误, 词法错误, 语法错误, 语义错误, 运行时错误

# 后端类型
后端类型 = Literal["ast", "text"]


# ── 运行时助手注入 — 委托中立模块（单一事实源）
# 全局搜索「注入运行时助手」应只命中 runtime_environment.py

def _注入运行时助手(环境: dict) -> None:
    from .runtime_environment import 注入运行时助手 as _注入
    _注入(环境)


def 转译(源码: str, *, 后端: 后端类型 = "ast") -> str:
    """周道源码 → Python 源码（字符串）。

    完整管线：扫描 → 解析 → 降低 → 语义分析 → 后端发射。
    语义分析阶段拒绝未定义名称和非法上下文，确保进入后端的程序已通过语义验证。

    Args:
        源码: 周道源码
        后端: 使用的后端 — "ast"（默认，正式）或 "text"（调试/差分）

    Returns:
        Python 源码字符串
    """
    tokens = 扫描(源码)
    解析器实例 = 解析器(tokens)
    ast = 解析器实例.解析()
    降低结果 = 降低(ast)
    ir = 降低结果.ir
    位置映射 = 降低结果.位置映射

    # 语义分析
    sem_prog = 语义分析(ir, 位置映射)
    if sem_prog.有错误:
        first = sem_prog.全部错误()[0]
        raise 语义错误(first.消息, first.位置)

    if 后端 == "ast":
        backend = PythonAstBackend(位置映射)
        return backend.emit_text(sem_prog)
    else:
        emit = 发射器()
        return emit.发射(sem_prog)


def 转译_仅语法(源码: str, *, 后端: 后端类型 = "text") -> str:
    """周道源码 → Python 源码（字符串）。

    仅做语法转换，跳过语义分析。用于测试特定构造的翻译输出。
    注意：此函数不执行名称解析，生成的 Python 可能引用未定义名称。

    Args:
        源码: 周道源码
        后端: 使用的后端 — "ast"（默认）或 "text"

    Returns:
        Python 源码字符串
    """
    tokens = 扫描(源码)
    解析器实例 = 解析器(tokens)
    surface_ast = 解析器实例.解析()

    if 后端 == "ast":
        降低结果 = 降低(surface_ast)
        backend = PythonAstBackend(降低结果.位置映射)
        return backend.emit_text(降低结果.ir)
    else:
        ir = 降低_仅语法(surface_ast)
        emit = 发射器()
        return emit.发射(ir)


def 运行(源码: str, 全局变量: dict | None = None,
         *, 后端: 后端类型 = "ast") -> dict:
    """周道源码 → 编译 → 执行。返回执行后的全局变量字典。

    Args:
        源码: 周道源码
        全局变量: 可选的初始全局变量
        后端: 使用的后端 — "ast"（默认，带异常位置映射）或 "text"

    Returns:
        执行后的全局变量字典
    """
    tokens = 扫描(源码)
    解析器实例 = 解析器(tokens)
    surface_ast = 解析器实例.解析()
    降低结果 = 降低(surface_ast)
    ir = 降低结果.ir
    位置映射 = 降低结果.位置映射

    # 加载模块依赖（使语义分析能识别模块绑定）
    from .module_loader import ModuleLoader
    from .core_ir import 本地模块引入IR, 从本地模块引入IR, 导入别名IR
    _模块缓存: dict[str, dict[str, object]] = {}
    _loader = ModuleLoader()
    for stmt in ir.语句列表:
        if isinstance(stmt, (本地模块引入IR, 从本地模块引入IR)):
            _模块缓存[stmt.模块名] = _loader.load_module(stmt.模块名, os.getcwd())

    # 语义分析
    sem_prog = 语义分析(ir, 位置映射)
    if sem_prog.有错误:
        first = sem_prog.全部错误()[0]
        raise 语义错误(first.消息, first.位置)

    # 构建执行环境（含模块绑定）
    if 全局变量 is None:
        全局变量 = {}
    from types import SimpleNamespace
    _环境_模块: dict[str, object] = {}
    for stmt in ir.语句列表:
        if isinstance(stmt, 本地模块引入IR):
            dep = _模块缓存.get(stmt.模块名)
            if dep:
                _环境_模块[stmt.模块名] = SimpleNamespace(**dep)
        elif isinstance(stmt, 从本地模块引入IR):
            dep = _模块缓存.get(stmt.模块名)
            if dep:
                for 名称 in stmt.名称:
                    if 名称 in dep:
                        全局变量[名称] = dep[名称]

    if 后端 == "ast":
        # 合并模块绑定到执行环境
        全局变量.update(_环境_模块)
        backend = PythonAstBackend(位置映射)
        return backend.exec_program(sem_prog, 全局变量, 源码)

    # text 后端
    python_code = 发射器().发射(sem_prog)
    环境 = {"__name__": "__周道__"}
    if 全局变量:
        环境.update(全局变量)
    # 注入运行时助手
    _注入运行时助手(环境)
    exec(python_code, 环境)
    return 环境


def 运行文件(路径: str, *, 后端: 后端类型 = "ast"):
    """运行 .zd 文件。"""
    with open(路径, "r", encoding="utf-8") as f:
        源码 = f.read()
    python_code = 转译(源码, 后端=后端)
    exec(python_code, {"__name__": "__周道__"})


def _修复编码():
    """统一修复 stdout/stderr 编码，确保终端正确显示 UTF-8。

    1. Python 3.7+ 用 reconfigure（不重新包装）
    2. 回退到 detach() 重新包装（避免双重包装 bug）
    3. Windows 专有：设置控制台代码页为 UTF-8
    """
    import io
    for _名称 in ('stdout', 'stderr'):
        _流 = getattr(sys, _名称, None)
        if _流 is None:
            continue
        # 已经是 UTF-8，跳过
        if _流.encoding and _流.encoding.upper() in ('UTF-8', 'UTF8'):
            continue
        # Python 3.7+ reconfigure（最简单，不破坏流）
        if hasattr(_流, 'reconfigure'):
            try:
                _流.reconfigure(encoding='utf-8', errors='replace')
                continue
            except Exception:
                pass
        # 回退：detach 后重新包装
        if hasattr(_流, 'detach'):
            try:
                setattr(sys, _名称,
                    io.TextIOWrapper(_流.detach(), encoding='utf-8', errors='replace'))
            except Exception:
                pass

    # Windows：设置控制台为 UTF-8 代码页
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass


def CLI():
    """命令行入口。"""
    import argparse
    _修复编码()

    parser = argparse.ArgumentParser(description="周道 — 中文句法式 Python 方言")
    parser.add_argument("文件", nargs="?", help=".zd 源文件")
    parser.add_argument("-v", "--version", action="store_true", help="显示版本并退出")
    parser.add_argument("-o", "--输出", help="输出转译后的 Python 文件（不执行）")
    parser.add_argument("--emit", action="store_true", help="仅输出 Python 代码到 stdout")
    parser.add_argument("--show-py", action="store_true", help="仅显示生成的 Python 代码（同 --emit）")
    parser.add_argument("--check", action="store_true", help="仅检查语法")
    parser.add_argument("-i", "--interactive", action="store_true",
        help="执行后进入交互式 REPL（带当前程序所有变量）")
    parser.add_argument(
        "--backend", choices=["ast", "text"], default="ast",
        help='后端: "ast"（直接构造 Python AST，默认）或 "text"（字符串拼接）',
    )

    args = parser.parse_args()

    if args.version:
        from . import __version__
        print(f"Zhoudao v{__version__}")
        return

    if not args.文件:
        parser.print_help()
        return

    with open(args.文件, "r", encoding="utf-8") as f:
        源码 = f.read()

    if args.check:
        try:
            python_code = 转译(源码, 后端=args.backend)
            compile(python_code, "<周道>", "exec")
            print("✅ 语法检查通过")
        except (词法错误, 语法错误, 语义错误) as e:
            print(f"❌ {e}")
            sys.exit(1)
        except SyntaxError as e:
            位置 = f"第{e.lineno}行" if e.lineno else "未知位置"
            print(f"❌ 编译错误: 生成代码在{位置}不合法: {e.msg}")
            sys.exit(1)
        except 周道错误 as e:
            print(f"❌ 周道错误: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 内部错误: {type(e).__name__}: {e}")
            sys.exit(1)
        return

    python_code = 转译(源码, 后端=args.backend)

    if args.输出:
        with open(args.输出, "w", encoding="utf-8") as f:
            f.write(python_code)
        print(f"✅ 已输出 Python 到 {args.输出}")
    elif args.emit or args.show_py:
        print(python_code)
    else:
        _运行环境 = {"__name__": "__周道__"}
        import sys as _sys, types as _types
        if "__周道__" not in _sys.modules:
            _sys.modules["__周道__"] = _types.ModuleType("__周道__")
        _sys.modules["__周道__"].__dict__.update(_运行环境)
        _注入运行时助手(_运行环境)
        exec(python_code, _运行环境)

    # 交互式 REPL：执行后带着所有变量进入 Python REPL
    if args.interactive:
        import code
        print("\n── 周道交互式 REPL ──")
        print("当前程序的所有变量可直接使用。输入 exit() 或 Ctrl+Z 退出。\n")
        code.interact(local=_运行环境)


if __name__ == "__main__":
    CLI()
