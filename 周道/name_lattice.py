"""周道 v0.0.3：NameLattice — 完整程序的作用域层次结构。

实现 NAME-RESOLUTION.md §2 的 NameLattice 定义。
管理 NameTable 的层次化结构，提供按作用域链查找名称的能力。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .nametable import NameTable, 绑定信息
from .errors import 源码位置, 语义错误


class 查找结果:
    """名称查找结果。

    封装查找的完整路径信息，用于错误报告和调试。
    """

    def __init__(self, 绑定: 绑定信息, 搜索路径: list[str]):
        self.绑定 = 绑定
        self.搜索路径 = 搜索路径  # 按搜索顺序列出查找过的作用域类型

    def __str__(self) -> str:
        return f"{self.绑定} 路径={'→'.join(self.搜索路径)}"


@dataclass
class NameLattice:
    """完整程序的作用域层次结构。

    由一个根表（全局）和嵌套的子表组成。
    提供从当前作用域向上查找名称的标准算法。

    规则：
    - 从当前作用域开始查找
    - 如果当前作用域未找到，递归到父作用域
    - 找到第一个匹配即返回（最近的遮蔽优先）
    - 找到根表仍未找到时报告语义错误
    """

    根表: NameTable
    当前表: NameTable

    # 跨越声明栈：每层函数作用域一个独立 dict
    # 格式: [{名称: "global" | "nonlocal"}, ...]
    _跨越声明栈: list[dict[str, str]] = field(default_factory=list)

    def __init__(self):
        全局表 = NameTable(作用域类型="global")
        self.根表 = 全局表
        self.当前表 = 全局表
        self._跨越声明栈 = [{}]

    @property
    def _跨越声明(self) -> dict[str, str]:
        """当前函数作用域的跨越声明（兼容旧属性名）。"""
        return self._跨越声明栈[-1]

    def 进入作用域(self, 类型: str) -> NameTable:
        """进入一个新的嵌套作用域。

        新作用域的父表指向当前作用域。
        当前作用域指针移动到新作用域。
        函数作用域会创建独立跨越声明栈层。
        """
        新表 = NameTable(作用域类型=类型, 父表=self.当前表)
        self.当前表 = 新表
        if 类型 == "function":
            self._跨越声明栈.append({})
        return 新表

    def 离开作用域(self) -> NameTable:
        """离开当前作用域，回到父作用域。

        Returns:
            被离开的作用域

        Raises:
            语义错误: 如果已在根作用域
        """
        旧表 = self.当前表
        if 旧表.父表 is None:
            raise 语义错误("已在根作用域，无法离开")
        self.当前表 = 旧表.父表
        if 旧表.作用域类型 == "function":
            self._跨越声明栈.pop()
        return 旧表

    def 在当前域注册(self, 名称: str, 实体: 绑定信息) -> None:
        """在当前作用域注册一个名称（遇到重复则报错）。"""
        self.当前表.绑定(名称, 实体)

    def 解析(self, 名称: str, 位置: 源码位置 | None = None) -> 绑定信息:
        """名称解析：从当前作用域向上查找。

        规则：
        1. 如果名称有跨越声明，按跨越规则查找
        2. 否则标准查找（当前→父→...→全局）

        Args:
            名称: 要解析的名称
            位置: 源码位置（用于错误报告）

        Returns:
            绑定信息

        Raises:
            语义错误: 如果未找到
        """
        # 先检查跨越声明
        if 名称 in self._跨越声明:
            声明类型 = self._跨越声明[名称]
            if 声明类型 == "global":
                return self._全局解析(名称, 位置)
            elif 声明类型 == "nonlocal":
                return self._外层解析(名称, 位置)

        # 标准查找
        搜索路径: list[str] = []
        表: NameTable | None = self.当前表

        while 表 is not None:
            搜索路径.append(表.作用域类型)
            绑定 = 表.查找(名称)
            if 绑定 is not None:
                return 绑定
            表 = 表.父表

        # 未找到
        候选 = self._找候选(名称)
        候选提示 = ""
        if 候选:
            候选提示 = f"最接近的候选名称：{'、'.join(候选[:5])}"

        路径描述 = " → ".join(搜索路径)
        msg = f"未定义的名称：「{名称}」\n已搜索作用域：{路径描述}"

        if 候选提示:
            msg += f"\n{候选提示}"

        raise 语义错误(msg, 位置)

    def 在当前域解析(self, 名称: str) -> Optional[绑定信息]:
        """仅在当前作用域查找，不递归到父表。"""
        return self.当前表.查找(名称)

    def 检查重复(self, 名称: str) -> bool:
        """检查当前作用域是否已存在同名绑定。"""
        return self.当前表.已绑定(名称)

    def 注册跨越声明(self, 名称: str, 声明类型: str) -> None:
        """注册一个跨越声明（全局或外层）。

        Args:
            名称: 跨越声明的名称
            声明类型: "global" 或 "nonlocal"

        Raises:
            语义错误: 如果已存在不同声明类型的跨越声明
        """
        if 名称 in self._跨越声明 and self._跨越声明[名称] != 声明类型:
            raise 语义错误(
                f"名称「{名称}」已有「{self._跨越声明[名称]}」跨越声明，"
                f"不能同时声明为「{声明类型}」"
            )
        self._跨越声明[名称] = 声明类型

    def 解除绑定(self, 名称: str) -> bool:
        """从当前作用域解除名称绑定。"""
        return self.当前表.解除绑定(名称)

    def _全局解析(self, 名称: str, 位置: 源码位置 | None = None) -> 绑定信息:
        """全局跨越查找——直接从根表（全局）查找。"""
        绑定 = self.根表.查找(名称)
        if 绑定 is None:
            raise 语义错误(
                f"未定义的全局名称：「{名称}」",
                位置
            )
        return 绑定

    def _外层解析(self, 名称: str, 位置: 源码位置 | None = None) -> 绑定信息:
        """外层跨越查找——跳过当前定义层。

        从当前作用域向上找到最近的 function 类型作用域，
        然后从它的父作用域开始标准查找。
        """
        # 跳过当前层
        表: NameTable | None = self.当前表

        # 找到最近的 function 类型作用域并跳转到其父表
        while 表 is not None and 表.作用域类型 != "function":
            表 = 表.父表

        if 表 is None or 表.父表 is None:
            raise 语义错误(
                f"「{名称}」的外层查找失败：当前不在定义内",
                位置
            )

        # 从函数的外部作用域开始查找
        搜索路径: list[str] = [f"外层({表.父表.作用域类型})"]
        查找表: NameTable | None = 表.父表
        while 查找表 is not None:
            绑定 = 查找表.查找(名称)
            if 绑定 is not None:
                return 绑定
            查找表 = 查找表.父表

        raise 语义错误(
            f"未定义的外层名称：「{名称}」",
            位置
        )

    def _找候选(self, 名称: str) -> list[str]:
        """在名称相似度上找候选名称（简单的包含关系匹配）。"""
        所有名称: set[str] = set()

        表: NameTable | None = self.当前表
        while 表 is not None:
            所有名称.update(表.所有名称)
            表 = 表.父表

        # 简单的包含关系匹配
        候选 = []
        for n in 所有名称:
            if 名称 in n or n in 名称:
                候选.append(n)
            # 编辑距离太复杂，暂不实现

        return sorted(候选, key=len)[:5]

    def 导出(self) -> dict:
        """将 NameLattice 导出为可序列化的字典。"""
        作用域链: list[dict] = []
        表: NameTable | None = self.当前表
        while 表 is not None:
            作用域链.append(表.导出())
            表 = 表.父表

        return {
            "当前作用域类型": self.当前表.作用域类型,
            "作用域链深度": len(作用域链),
        }

    def __repr__(self) -> str:
        return (
            f"NameLattice(root={self.根表.作用域类型}, "
            f"current={self.当前表.作用域类型}, "
            f"depth={...})"
        )
