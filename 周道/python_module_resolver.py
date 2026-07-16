"""周道 v0.0.10: Python 模块解析器。"""

from __future__ import annotations
import importlib.util
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

from .environment_resolver import 环境信息


@dataclass
class Python模块信息:
    """Python 模块解析信息。"""
    模块名: str = ""
    绝对路径: str = ""
    已加载: bool = False
    成员: dict[str, Any] = field(default_factory=dict)
    来源: str = ""  # "stubs" | "runtime" | "unknown"


class PythonModuleResolver:
    """Python 模块解析器。

    解析 Python 模块路径和成员信息。
    不自动汉化名称。
    """

    def __init__(self, 环境: 环境信息):
        self.环境 = 环境
        self._模块缓存: dict[str, Python模块信息] = {}

    def 解析模块(self, 模块名: str) -> Python模块信息:
        """解析一个 Python 模块。

        Args:
            模块名: Python 模块名

        Returns:
            Python模块信息
        """
        if 模块名 in self._模块缓存:
            return self._模块缓存[模块名]

        # 尝试使用 importlib 解析路径
        路径 = self._查找模块路径(模块名)

        if 路径:
            信息 = Python模块信息(
                模块名=模块名,
                绝对路径=路径,
                已加载=True,
                来源="runtime" if self.环境.解释器路径 else "unknown",
            )
        else:
            信息 = Python模块信息(
                模块名=模块名,
                已加载=False,
                来源="unknown",
            )

        self._模块缓存[模块名] = 信息
        return 信息

    def 获取成员(self, 模块名: str, 成员名: str) -> Any | None:
        """获取 Python 模块成员（不导入模块的静态信息）。

        Args:
            模块名: Python 模块名
            成员名: 成员名称

        Returns:
            成员信息或 None
        """
        信息 = self.解析模块(模块名)
        if not 信息.已加载:
            return None
        return 信息.成员.get(成员名)

    def 获取所有成员名(self, 模块名: str) -> list[str]:
        """获取 Python 模块的所有可访问成员名。"""
        信息 = self.解析模块(模块名)
        if not 信息.已加载:
            return []
        return list(信息.成员.keys())

    def _查找模块路径(self, 模块名: str) -> str | None:
        """查找 Python 模块的文件系统路径。"""
        try:
            spec = importlib.util.find_spec(模块名)
            if spec and spec.origin and spec.origin != "built-in":
                return spec.origin
        except (ImportError, ValueError, AttributeError):
            pass
        return None


def 解析引入语句(语句文本: str) -> tuple[str, list[str]] | None:
    """解析周道引入语句中的 Python 模块信息。

    Args:
        语句文本: 引入语句源码行

    Returns:
        (模块名, [成员列表]) 或 None（如果非 Python 引入）
    """
    文本 = 语句文本.strip()
    if 文本.startswith("引入Python模块"):
        # 引入Python模块《os》
        start = 文本.find("《")
        end = 文本.find("》")
        if start >= 0 and end > start:
            模块名 = 文本[start + 1:end]
            return (模块名, [])
    elif 文本.startswith("从Python模块"):
        # 从Python模块《os》中引入 path、name
        start = 文本.find("《")
        end = 文本.find("》")
        if start >= 0 and end > start:
            模块名 = 文本[start + 1:end]
            引入部分 = 文本[end + 1:]
            if "引入" in 引入部分:
                成员文本 = 引入部分.split("引入", 1)[1].strip()
                成员 = [m.strip() for m in 成员文本.replace("、", ",").split(",") if m.strip()]
                return (模块名, 成员)
    return None
