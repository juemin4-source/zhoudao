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

    # 语义分析
    sem_prog = 语义分析(ir, 位置映射)
    if sem_prog.有错误:
        first = sem_prog.全部错误()[0]
        raise 语义错误(first.消息, first.位置)

    if 后端 == "ast":
        backend = PythonAstBackend(位置映射)
        return backend.exec_program(sem_prog, 全局变量, 源码)

    # text 后端
    python_code = 发射器().发射(sem_prog)
    环境 = {"__name__": "__周道__"}
    if 全局变量:
        环境.update(全局变量)
    exec(python_code, 环境)
    return 环境


def 运行文件(路径: str, *, 后端: 后端类型 = "ast"):
    """运行 .zd 文件。"""
    with open(路径, "r", encoding="utf-8") as f:
        源码 = f.read()
    python_code = 转译(源码, 后端=后端)
    exec(python_code, {"__name__": "__周道__"})


def CLI():
    """命令行入口。"""
    import argparse
    # Windows GBK 兼容输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="周道 — 中文句法式 Python 方言")
    parser.add_argument("文件", nargs="?", help=".zd 源文件")
    parser.add_argument("-o", "--输出", help="输出转译后的 Python 文件（不执行）")
    parser.add_argument("--emit", action="store_true", help="仅输出 Python 代码到 stdout")
    parser.add_argument("--check", action="store_true", help="仅检查语法")
    parser.add_argument(
        "--backend", choices=["ast", "text"], default="ast",
        help='后端: "ast"（直接构造 Python AST，默认）或 "text"（字符串拼接）',
    )

    args = parser.parse_args()

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
    elif args.emit:
        print(python_code)
    else:
        exec(python_code, {"__name__": "__周道__"})


if __name__ == "__main__":
    CLI()
