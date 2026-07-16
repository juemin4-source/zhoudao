"""周道 v0.0.10: 语义 Token 提供者。

根据 SemanticProgram 输出准确的语义角色。
先由词法提供基础颜色，再由语义覆盖。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .core_ir import (
    程序IR, 语句IR, 表达式IR,
    变量引用IR, 函数定义IR, 类别声明IR, 类别方法IR,
    赋值IR, 打印IR, 遍历IR, 调用IR,
    成员访问IR,
)
from .semantic_program import SemanticProgram


# LSP SemanticTokenTypes
TOKEN_KEYWORD = 0
TOKEN_OPERATOR = 1
TOKEN_PUNCTUATION = 2
TOKEN_STRING = 3
TOKEN_NUMBER = 4
TOKEN_BOOLEAN = 5
TOKEN_VARIABLE = 6
TOKEN_PARAMETER = 7
TOKEN_FUNCTION = 8
TOKEN_METHOD = 9
TOKEN_CLASS = 10
TOKEN_PROPERTY = 11
TOKEN_NAMESPACE = 12
TOKEN_TYPE = 13

# LSP SemanticTokenModifiers
MOD_DECLARATION = 1 << 0
MOD_DEFINITION = 1 << 1
MOD_READONLY = 1 << 2
MOD_IMPORTED = 1 << 3
MOD_ASYNC = 1 << 4
MOD_GENERATOR = 1 << 5
MOD_DEPRECATED = 1 << 6
MOD_UNRESOLVED = 1 << 7


@dataclass
class 语义Token:
    行: int = 0
    列: int = 0
    长度: int = 0
    类型: int = 0
    修饰: int = 0


def 获取语义Tokens(sem_prog: SemanticProgram, 源码: str) -> list[语义Token]:
    """从 SemanticProgram 获取语义 Token 列表。

    Args:
        sem_prog: 语义分析结果
        源码: 原始周道源码

    Returns:
        语义Token 列表
    """
    tokens: list[语义Token] = []
    行列表 = 源码.split("\n")
    ir = sem_prog.core_ir

    if ir and isinstance(ir, 程序IR):
        for stmt in ir.语句列表:
            _处理语句(stmt, tokens)

    return tokens


def _处理语句(stmt: 语句IR, tokens: list[语义Token]):
    """处理语句级别的 Token。"""
    if isinstance(stmt, 赋值IR):
        if isinstance(stmt.目标, 变量引用IR):
            tokens.append(语义Token(
                类型=TOKEN_VARIABLE,
            ))
    elif isinstance(stmt, 函数定义IR):
        tokens.append(语义Token(
            类型=TOKEN_FUNCTION,
            修饰=MOD_DECLARATION | (MOD_ASYNC if stmt.是异步 else 0) | (MOD_GENERATOR if stmt.是生成器 else 0),
        ))
        for param in stmt.参数:
            tokens.append(语义Token(
                类型=TOKEN_PARAMETER,
            ))
    elif isinstance(stmt, 类别声明IR):
        tokens.append(语义Token(
            类型=TOKEN_CLASS,
            修饰=MOD_DECLARATION,
        ))
    elif isinstance(stmt, 类别方法IR):
        tokens.append(语义Token(
            类型=TOKEN_METHOD,
            修饰=MOD_DECLARATION | (MOD_ASYNC if stmt.是异步 else 0) | (MOD_GENERATOR if stmt.是生成器 else 0),
        ))


def 词法高亮(源码: str) -> list[语义Token]:
    """纯词法高亮（不依赖语义分析）。

    用于 LSP 的快速初始响应。
    """
    from .lexer import 扫描
    from .tokens import NUMBER, STRING, IDENTIFIER

    tokens = 扫描(源码)
    结果: list[语义Token] = []

    for tok in tokens:
        if tok.token_type == NUMBER:
            结果.append(语义Token(行=tok.位置.行 - 1, 列=tok.位置.列 - 1, 长度=len(tok.值), 类型=TOKEN_NUMBER))
        elif tok.token_type == STRING:
            结果.append(语义Token(行=tok.位置.行 - 1, 列=tok.位置.列 - 1, 长度=len(tok.值), 类型=TOKEN_STRING))

    return 结果
