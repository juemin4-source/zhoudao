"""周道 v0.0.3：ContextResolver — 上下文解析器。

实现 CONTEXTUAL-KEYWORDS.md 中定义的上下文关键字消歧逻辑。
负责判断一个 token 在给定语法上下文中是否为关键字。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .tokens import Token, IDENTIFIER
from .nametable import NameTable, 绑定信息
from .name_lattice import NameLattice
from .errors import 源码位置, 语义错误


# 命令关键字位置（设/使/设置 后）
命令关键字 = frozenset({
    "K_TRUE_STATE",    # 成立
    "K_FALSE_STATE",   # 不成立
    "K_NONE",          # 没有值
    "K_AS",            # 为
    "K_BECOME",        # 变为
    "K_CATEGORY",      # 类别（设置后）
})

# 条件关键字位置
条件关键字 = frozenset({
    "OP_EQ", "OP_NE", "OP_GT", "OP_LT", "OP_GE", "OP_LE",
    "OP_AND", "OP_OR", "OP_NOT",
    "OP_IN", "OP_NOT_IN",
    "K_IS", "K_IS_NOT",
})

# 控制结构内部关键字
控制关键字 = frozenset({
    "K_THEN", "K_ELSE", "K_ALWAYS", "K_WHEN",
    "K_EACH_AS", "K_AS_RESULT", "K_RESULT",
    "K_EXCEPT", "K_FINALLY", "K_FINALLY_DO",
    "K_CASE", "K_DEFAULT",
    "K_AS_ALIAS", "K_SCOPE_DECL", "K_GLOBAL", "K_NONLOCAL",
})


@dataclass
class 上下文关键字判定:
    """上下文关键字判定结果。"""
    是关键字: bool
    关键字类型: str | None = None
    备选解释: str | None = None
    """如果不是关键字，给出备选解释。"""


class ContextResolver:
    """上下文解析器。

    负责在给定语法位置判断一个短语是否为关键字。
    实现 CONTEXTUAL-KEYWORDS.md 中的消歧算法。
    """

    def __init__(self, 名称格子: NameLattice | None = None):
        self.名称格子 = 名称格子 or NameLattice()
        # 当前解析上下文栈
        self._上下文栈: list[str] = ["module"]
        # 在定义内标记
        self.在定义内: bool = False
        # 在异常内标记
        self.在异常内: bool = False
        # 循环嵌套深度
        self.循环深度: int = 0

    # ==================== 上下文栈管理 ====================

    def 进入上下文(self, 上下文: str) -> None:
        """进入一个新的语法上下文。"""
        self._上下文栈.append(上下文)

    def 离开上下文(self) -> str:
        """离开当前语法上下文。"""
        return self._上下文栈.pop()

    @property
    def 当前上下文(self) -> str:
        """获取当前语法上下文。"""
        return self._上下文栈[-1] if self._上下文栈 else "module"

    # ==================== 关键字判定 ====================

    def 判定(self, token: Token, 位置: 语法位置) -> 上下文关键字判定:
        """判断一个 Token 在当前上下文是否为关键字。

        Args:
            token: 要判定的 Token
            位置: 当前语法位置描述

        Returns:
            上下文关键字判定
        """
        token_type = token.token_type

        # 完全关键字总是关键字
        if token_type in self._完全关键字集():
            return 上下文关键字判定(是关键字=True, 关键字类型=token_type)

        # 上下文关键字按位置判定
        if token_type in 命令关键字:
            return self._判定命令关键字(token, 位置)

        if token_type in 条件关键字:
            return self._判定条件关键字(token, 位置)

        if token_type in 控制关键字:
            return self._判定控制关键字(token, 位置)

        # 默认不是关键字
        return 上下文关键字判定(是关键字=False)

    def _完全关键字集(self) -> frozenset:
        """返回完全关键字集合（始终是关键字）。"""
        return frozenset({
            "K_SET", "K_MAKE", "K_IF", "K_WHILE", "K_FROM",
            "K_BREAK", "K_CONTINUE", "K_TRY", "K_PRINT",
            "K_IMPORT", "K_DEFINE", "K_SETUP",
            "K_DELETE", "K_PASS", "K_RAISE", "K_YIELD",
            "K_AWAIT", "K_DONE", "K_OF_RESULT",
            "K_MATCH", "K_MATCH_CASES",
            "K_MUST", "K_MUST_NOT", "K_ELSE_ERROR",
            "LIT_TRUE", "LIT_FALSE",
            "K_AND_THEN",
        })

    def _判定命令关键字(self, token: Token, 位置: 语法位置) -> 上下文关键字判定:
        """判定命令上下文中的关键字。

        在「设」「使」「设置」后出现的某些 token 可能是关键字。
        """
        if 位置.前导关键字 in ("K_SET", "K_SETUP", "K_MAKE"):
            return 上下文关键字判定(是关键字=True, 关键字类型=token.token_type)

        return 上下文关键字判定(
            是关键字=False,
            备选解释=f"「{token.值}」不在命令位置，作为普通标识符"
        )

    def _判定条件关键字(self, token: Token, 位置: 语法位置) -> 上下文关键字判定:
        """判定条件上下文中的关键字。"""
        if 位置.在条件中:
            return 上下文关键字判定(是关键字=True, 关键字类型=token.token_type)

        return 上下文关键字判定(
            是关键字=False,
            备选解释=f"「{token.值}」不在条件位置，作为普通算符或标识符"
        )

    def _判定控制关键字(self, token: Token, 位置: 语法位置) -> 上下文关键字判定:
        """判定控制结构上下文中的关键字。"""
        if 位置.在控制结构中:
            return 上下文关键字判定(是关键字=True, 关键字类型=token.token_type)

        return 上下文关键字判定(
            是关键字=False,
            备选解释=f"「{token.值}」不在控制结构位置，作为普通标识符"
        )

    # ==================== 语义检查工具 ====================

    def 检查名称合法(self, 名称: str, 位置: 源码位置) -> None:
        """检查名称是否可以作为标识符使用。

        结合上下文关键字规则，判断是否需要花括号转义。
        """
        from .exact_identifier import 完全关键字集

        if 名称 in 完全关键字集:
            raise 语义错误(
                f"「{名称}」是完全关键字，不可作为标识符。"
                f"如确实需要使用此名称，请使用花括号：{{{名称}}}",
                位置
            )

    def 建议转义(self, 名称: str) -> str:
        """对可能冲突的关键字名给出花括号转义建议。"""
        return f"{{{名称}}}"

    def 重置(self) -> None:
        """重置解析器状态。"""
        self._上下文栈 = ["module"]
        self.在定义内 = False
        self.在异常内 = False
        self.循环深度 = 0
        self.名称格子 = NameLattice()


@dataclass
class 语法位置:
    """描述当前语法位置。"""
    前导关键字: str | None = None
    """前一个结构关键字（如 K_SET、K_IF）。"""

    在条件中: bool = False
    """是否在条件表达式解析中。"""

    在控制结构中: bool = False
    """是否在控制结构内部（如果/当/遍历/尝试/分情形）。"""

    在定义体: bool = False
    """是否在函数定义体内。"""

    在表达式: bool = False
    """是否在表达式解析中。"""

    在参数列表: bool = False
    """是否在形参或实参列表中。"""

    def __str__(self) -> str:
        parts = []
        if self.前导关键字:
            parts.append(f"前导={self.前导关键字}")
        if self.在条件中:
            parts.append("条件")
        if self.在控制结构中:
            parts.append("控制结构")
        if self.在定义体:
            parts.append("定义体")
        if self.在表达式:
            parts.append("表达式")
        if self.在参数列表:
            parts.append("参数列表")
        return "|".join(parts) if parts else "未知"
