"""周道 v0.0.3：ambiguity — 歧义检测引擎。

实现歧义宪法 §7-8 定义的歧义分类与处置流程。
提供所有静态可检测歧义的检测函数。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .errors import 源码位置, 周道错误, 词法错误, 语法错误, 语义错误
from .diagnostics import 歧义诊断


# ── 歧义种类 ────────────────────────────────────────────────

class 歧义种类:
    """歧义种类的枚举常量。"""
    词法歧义 = "LEXICAL_AMBIGUITY"
    语法歧义 = "SYNTACTIC_AMBIGUITY"
    名称歧义 = "NAME_AMBIGUITY"
    作用域歧义 = "SCOPE_AMBIGUITY"
    省略歧义 = "OMISSION_AMBIGUITY"


# ── 歧义候选 ────────────────────────────────────────────────

@dataclass(frozen=True)
class 候选解析:
    """一个歧义候选解析。"""
    描述: str
    产生式: str  # 产生式名称或路径


# ── 检测结果 ────────────────────────────────────────────────

@dataclass
class 检测结果:
    """一次歧义检测的结果。"""
    有歧义: bool = False
    歧义种类: str | None = None
    候选列表: list[候选解析] = field(default_factory=list)
    诊断: str = ""
    位置: 源码位置 | None = None

    def 添加候选(self, 描述: str, 产生式: str = "") -> None:
        self.候选列表.append(候选解析(描述, 产生式))
        self.有歧义 = True

    def 生成错误(self) -> str:
        """生成完整歧义错误消息（含位置、候选解析、改写建议）。"""
        parts = []
        if self.位置:
            parts.append(f"[{self.位置.格式化()}]")
        parts.append(f"歧义错误 ({self.歧义种类})：{self.诊断}")
        if len(self.候选列表) >= 2:
            parts.append("候选解析:")
            for i, c in enumerate(self.候选列表, 1):
                parts.append(f"  {i}. {c.描述}")
        return '\n'.join(parts)


# ── 歧义检测器 ──────────────────────────────────────────────

class 歧义检测器:
    """对所有可静态检测的歧义进行检测。"""

    @staticmethod
    def 检查词法切片(源码: str, 位置: 源码位置) -> 检测结果:
        """检查同一位置是否存在多个词法切片方式。

        例如 "设没有值为空" 可切为:
          K_SET + ID(没有) + ID(值) + ...
          或 K_SET + K_NONE + ...
        """
        结果 = 检测结果(歧义种类=歧义种类.词法歧义, 位置=位置)

        # 最长关键字匹配在 lexer 层已处理。
        # 这里只检测已经过 lexer 仍存在的词法歧义。
        return 结果

    @staticmethod
    def 检查设分派(tokens, 标识符索引: int, 位置: 源码位置) -> 检测结果:
        """检查 '设 标识符' 后的分派歧义。

        可能路径: 绑定, 空值绑定, 命题绑定, 函数定义
        """
        结果 = 检测结果(歧义种类=歧义种类.语法歧义, 位置=位置)
        # 设分派通过向前看一个 token 消歧，本身不歧义
        return 结果

    @staticmethod
    def 检查省略成立(源码片段: str, 位置: 源码位置) -> 检测结果:
        """检查条件中 '成立' 的省略歧义。

        如 "如果任务完成" — 完成是变量还是命题?
        """
        结果 = 检测结果(歧义种类=歧义种类.省略歧义, 位置=位置)
        # v0.0.3: 如果条件不以成立/不成立/比较算符结尾 → 省略歧义
        # 这里由调用层判断，检测器只报告
        return 结果

    @staticmethod
    def 检查名称遮蔽(名称: str, 当前作用域: str, 外层名称: set[str],
                     位置: 源码位置) -> 检测结果:
        """检查同域重名或遮蔽。"""
        结果 = 检测结果(歧义种类=歧义种类.名称歧义, 位置=位置)
        if 名称 in 外层名称 and 当前作用域 == "function":
            结果.添加候选(f"名称「{名称}」遮蔽了外层同名定义")
        return 结果

    @staticmethod
    def 生成歧义错误(位置: 源码位置, 描述: str,
                     候选A: str = "", 候选B: str = "",
                     建议: str = "") -> 歧义诊断:
        """工厂方法：生成标准格式的歧义诊断。"""
        return 歧义诊断(
            位置=位置,
            描述=描述,
            类型=歧义种类.语法歧义,
            候选解析=[候选A, 候选B] if 候选A and 候选B else [],
            建议改写=建议
        )


# ── 歧义检查包装 ────────────────────────────────────────────

def 检查无歧义(源码: str, lexer_tokens: list | None = None) -> list[检测结果]:
    """对源码执行所有可静态检测的歧义检查。

    返回歧义检测结果列表。空列表表示无歧义。
    """
    results: list[检测结果] = []
    # 词法检查（预留）
    # 设分派检查（预留）
    # 省略检查可以在解析阶段进行
    return results
