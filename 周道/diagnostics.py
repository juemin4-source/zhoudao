"""周道 v0.0.3：diagnostics — 结构化诊断与歧义报告。

实现歧义宪法 §1.5 要求的歧义错误格式：
  [第N行第M列] 歧义错误: <描述>
  候选解析:
    1. <解析A>
    2. <解析B>
  建议改写: <改写说明>
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .errors import 源码位置


# ── 错误严重级别 ────────────────────────────────────────────

class 级别:
    """诊断级别。"""
    编译错误 = "COMPILE_ERROR"
    歧义错误 = "AMBIGUITY_ERROR"
    名称错误 = "NAME_ERROR"
    作用域错误 = "SCOPE_ERROR"
    警告 = "WARNING"


# ── 结构化诊断 ──────────────────────────────────────────────

@dataclass
class 歧义诊断:
    """一个结构化的歧义诊断。

    符合歧义宪法 §1.5.1 要求的错误格式。
    """

    位置: 源码位置 | None = None
    描述: str = ""
    类型: str = ""
    级别: str = 级别.歧义错误
    候选解析: list[str] = field(default_factory=list)
    """两个或以上的候选解析说明。"""

    建议改写: str = ""
    """消除歧义的改写建议。"""

    搜索路径: list[str] = field(default_factory=list)
    """名称解析时的搜索路径（名称错误时有用）。"""

    附近: str = ""
    """附近源代码片段。"""

    def 格式化(self) -> str:
        """将诊断格式化为可读的歧义错误消息。"""
        parts = []

        # 位置
        if self.位置:
            parts.append(f"[{self.位置.格式化()}]")

        # 级别/类型
        type_label = self.类型 or "歧义错误"
        parts.append(f"{type_label}: {self.描述}")

        # 候选解析
        if len(self.候选解析) >= 2:
            parts.append("候选解析:")
            for i, cand in enumerate(self.候选解析, 1):
                parts.append(f"  {i}. {cand}")
        elif len(self.候选解析) == 1:
            parts.append(f"解析: {self.候选解析[0]}")

        # 建议改写
        if self.建议改写:
            parts.append(f"建议改写: {self.建议改写}")

        # 搜索路径（作用域错误）
        if self.搜索路径:
            parts.append(f"已搜索作用域: {' → '.join(self.搜索路径)}")

        # 附近源码
        if self.附近:
            parts.append(f"    附近: {self.附近}")

        return '\n'.join(parts)

    def __str__(self) -> str:
        return self.格式化()


# ── 生成辅助函数 ────────────────────────────────────────────

def 重复定义(名称: str, 位置: 源码位置 | None = None,
             作用域: str = "") -> 歧义诊断:
    """生成「重复定义」诊断的快捷方法。"""
    域信息 = f"在{作用域}作用域" if 作用域 else "在当前作用域"
    return 歧义诊断(
        位置=位置,
        描述=f"名称「{名称}」重复定义{域信息}",
        级别=级别.名称错误,
        建议改写=f"请移除或重命名其中一个「{名称}」",
    )


def 未定义名称(名称: str, 位置: 源码位置 | None = None,
               候选: list[str] | None = None,
               搜索路径: list[str] | None = None) -> 歧义诊断:
    """生成「未定义名称」诊断。"""
    诊断 = 歧义诊断(
        位置=位置,
        描述=f"未定义的名称「{名称}」",
        级别=级别.名称错误,
        搜索路径=搜索路径 or [],
    )
    if 候选:
        诊断.建议改写 = f"最接近的候选名称：{'、'.join(候选[:5])}"
    return 诊断


def 省略歧义(代码: str, 位置: 源码位置 | None = None,
              候选A: str = "", 候选B: str = "",
              建议: str = "") -> 歧义诊断:
    """生成「省略歧义」诊断。"""
    return 歧义诊断(
        位置=位置,
        描述=f"省略歧义：「{代码}」的解析不唯一",
        类型="OMISSION_AMBIGUITY",
        候选解析=[c for c in [候选A, 候选B] if c],
        建议改写=建议 or "请补充必要的关键字以避免歧义",
    )


def 字段重复(类别: str, 字段: str, 位置: 源码位置 | None = None) -> 歧义诊断:
    """类别字段重复。"""
    return 歧义诊断(
        位置=位置,
        描述=f"类别「{类别}」包含重复字段「{字段}」",
        级别=级别.名称错误,
    )


def 跨越冲突(名称: str, 位置: 源码位置 | None = None) -> 歧义诊断:
    """作用域跨越声明冲突。"""
    return 歧义诊断(
        位置=位置,
        描述=f"名称「{名称}」不能同时声明为 global 和 nonlocal",
        级别=级别.作用域错误,
    )
