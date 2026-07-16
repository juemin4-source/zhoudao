"""周道 v0.0.10: Python 静态元数据读取。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class 成员元数据:
    """Python 成员元数据。"""
    名称: str = ""
    类型: str = "unknown"  # "function" | "class" | "variable" | "module" | "unknown"
    签名: str = ""  # 函数签名文本
    来源: str = "unknown"  # "stubs" | "runtime" | "unknown"


class PythonMetadataProvider:
    """Python 元数据提供者。

    根据配置模式读取 Python 类型存根或安全运行时元数据。
    """

    def __init__(self, 模式: str = "stubs_only"):
        """
        Args:
            模式: "off" | "stubs_only" | "stubs_then_safe_inspect"
        """
        self.模式 = 模式

    def 获取函数签名(self, 模块名: str, 函数名: str) -> 成员元数据 | None:
        """获取函数的签名元数据。

        Args:
            模块名: Python 模块名
            函数名: 函数名称

        Returns:
            成员元数据或 None
        """
        if self.模式 == "off":
            return None

        # stubs_only 和 stubs_then_safe_inspect 都先尝试存根
        stub = self._从存根读取(模块名, 函数名)
        if stub:
            return stub

        # stubs_then_safe_inspect 在存根缺失时尝试安全 inspect
        if self.模式 == "stubs_then_safe_inspect":
            return self._从安全运行时读取(模块名, 函数名)

        return None

    def 获取成员元数据(self, 模块名: str) -> list[成员元数据]:
        """获取模块的所有成员元数据。"""
        if self.模式 == "off":
            return []
        return self._从存根读取所有(模块名)

    def _从存根读取(self, 模块名: str, 成员名: str) -> 成员元数据 | None:
        """从 .pyi/typeshed 存根读取。"""
        # 简化实现：使用 typeshed 的有限查找
        # 完整实现需要解析 .pyi 文件
        return None

    def _从安全运行时读取(self, 模块名: str, 成员名: str) -> 成员元数据 | None:
        """通过安全 inspect 读取。"""
        try:
            import importlib
            import inspect

            mod = importlib.import_module(模块名)
            if not hasattr(mod, 成员名):
                return None

            obj = getattr(mod, 成员名)
            if inspect.isfunction(obj) or inspect.isbuiltin(obj):
                sig = str(inspect.signature(obj)) if not inspect.isbuiltin(obj) else "(...)"
                return 成员元数据(
                    名称=成员名,
                    类型="function",
                    签名=sig,
                    来源="runtime",
                )
            elif inspect.isclass(obj):
                return 成员元数据(
                    名称=成员名,
                    类型="class",
                    来源="runtime",
                )
            return 成员元数据(
                名称=成员名,
                类型="variable",
                来源="runtime",
            )
        except (ImportError, AttributeError, TypeError, ValueError):
            return None

    def _从存根读取所有(self, 模块名: str) -> list[成员元数据]:
        """从存根读取模块所有成员。"""
        return []
