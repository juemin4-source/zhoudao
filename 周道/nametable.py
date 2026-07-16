"""周道 v0.0.3：NameTable — 单一作用域的名称映射表。

实现 NAME-RESOLUTION.md §1 的 NameTable 定义。
每个 NameTable 对应一个独立作用域，管理该域内的名称→绑定映射。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .errors import 源码位置, 语义错误


@dataclass(frozen=True)
class 绑定信息:
    """一个名称的完整绑定信息。

    符合歧义宪法「一名一指」原则：
    同一作用域内一个名称只能有一个绑定信息。
    """
    名称: str
    类型: str  # "变量" | "函数" | "类别" | "模块" | "参数" | "类别字段"
    位置: "源码位置 | None" = None
    是否可重绑定: bool = False  # 由「使」引入的名称

    def __str__(self) -> str:
        return f"绑定({self.名称!r}, {self.类型})"


@dataclass
class NameTable:
    """单一作用域的名称映射表。

    性质：
    - 同域不重名（同一作用域内一个名称只能绑定一次）
    - 冻结（绑定不可修改，只能删除）
    - 名称查找只在该域内
    """

    作用域类型: str  # "global" | "function" | "control" | "category" | "match"
    父表: Optional["NameTable"] = None
    _表: dict[str, 绑定信息] = field(default_factory=dict)

    def 绑定(self, 名称: str, 实体: 绑定信息) -> None:
        """在当前作用域中绑定一个名称。

        Raises:
            语义错误: 如果名称已存在（同域不重名）
        """
        if 名称 in self._表:
            raise 语义错误(
                f"重复定义：「{名称}」已在当前{self.作用域类型}作用域中定义"
            )
        self._表[名称] = 实体

    def 查找(self, 名称: str) -> Optional[绑定信息]:
        """在当前作用域中查找一个名称（仅当前表）。"""
        return self._表.get(名称)

    def 解除绑定(self, 名称: str) -> bool:
        """从当前作用域中删除名称绑定。"""
        if 名称 in self._表:
            del self._表[名称]
            return True
        return False

    def 已绑定(self, 名称: str) -> bool:
        """检查名称是否已绑定到当前作用域。"""
        return 名称 in self._表

    @property
    def 所有名称(self) -> frozenset[str]:
        """返回当前作用域中所有名称的集合。"""
        return frozenset(self._表.keys())

    @property
    def 数量(self) -> int:
        """当前作用域名称数量。"""
        return len(self._表)

    def 列出(self) -> list[绑定信息]:
        """按插入顺序列出所有绑定信息。"""
        # 在 Python 3.7+ 中 dict 保持插入顺序
        return list(self._表.values())

    def 导出(self) -> dict[str, dict]:
        """将 NameTable 导出为可序列化的字典。"""
        return {
            "作用域类型": self.作用域类型,
            "绑定数量": self.数量,
            "绑定列表": [
                {"名称": b.名称, "类型": b.类型}
                for b in self.列出()
            ]
        }

    def __repr__(self) -> str:
        return f"NameTable({self.作用域类型}, {self.数量} 个名称)"
