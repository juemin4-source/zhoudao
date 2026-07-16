"""周道模块解析器：模块名 → .zd 文件路径 v0.0.8"""

from __future__ import annotations
import os


class ModuleResolver:
    """周道模块路径解析器。

    将模块名《工具》解析为 .zd 文件绝对路径。
    搜索顺序：
    1. 当前文章所在目录
    2. 显式配置的周道模块根目录
    """

    def __init__(self, 模块根目录: list[str] | None = None):
        self._额外根目录 = 模块根目录 or []

    def resolve(self, 模块名: str, 当前目录: str) -> str | None:
        """解析模块名到 .zd 文件路径。

        Args:
            模块名: 周道模块名（《工具》 → "工具"）
            当前目录: 当前文章所在目录

        Returns:
            .zd 文件的绝对路径，或 None 表示未找到
        """
        文件名 = f"{模块名}.zd"

        # 1. 当前目录
        candidate = os.path.join(当前目录, 文件名)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

        # 2. 额外根目录
        for root in self._额外根目录:
            candidate = os.path.join(root, 文件名)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

        return None

    def add_root(self, 目录: str) -> None:
        """添加周道模块搜索根目录。"""
        if 目录 not in self._额外根目录:
            self._额外根目录.append(目录)
