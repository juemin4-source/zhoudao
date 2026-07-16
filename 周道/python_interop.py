"""周道 v0.0.10: Python 生态互通层。

实现 Python 类型存根读取、安全 inspect 元数据、模块解析。
"""

from __future__ import annotations
import os
import sys
import importlib.util
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

from .environment_resolver import 环境信息
from .project_config import ProjectConfig


@dataclass
class 成员元数据:
    名称: str = ""
    类型: str = "unknown"  # function | class | variable | module
    签名: str = ""
    来源: str = "unknown"  # stubs | runtime | unknown


class StubsReader:
    """Python 类型存根读取器。

    读取 .pyi 文件和 typeshed 中的类型信息。
    不导入目标模块。
    """

    def __init__(self, 搜索路径: list[str]):
        self.搜索路径 = 搜索路径

    def 读取函数签名(self, 模块名: str, 函数名: str) -> 成员元数据 | None:
        """从存根读取函数签名。"""
        # 直接尝试 import 模块的 __module__
        try:
            spec = importlib.util.find_spec(模块名)
            if spec and spec.origin:
                # 检查是否有 .pyi 文件
                pyi_path = spec.origin + "i"  # .py → .pyi
                if os.path.isfile(pyi_path):
                    return self._解析pyi(pyi_path, 函数名)
        except (ImportError, ValueError, AttributeError):
            pass
        return None

    def 读取模块成员(self, 模块名: str) -> list[成员元数据]:
        """读取模块所有成员的元数据。"""
        return []

    def _解析pyi(self, 路径: str, 函数名: str) -> 成员元数据 | None:
        """解析 .pyi 文件中的函数签名（简化实现）。"""
        try:
            with open(路径, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("def " + 函数名):
                        sig_start = line.find("(")
                        sig_end = line.rfind(":")
                        if sig_start >= 0:
                            sig = line[sig_start:sig_end if sig_end > sig_start else None]
                            return 成员元数据(
                                名称=函数名,
                                类型="function",
                                签名=sig.strip() if sig else "(...)",
                                来源="stubs",
                            )
        except (OSError, UnicodeDecodeError):
            pass
        return None


class SafeInspector:
    """安全运行时元数据读取器。

    使用有限 inspect 读取模块成员信息。
    失败时静默降级。
    """

    def __init__(self, 模式: str = "stubs_then_safe_inspect"):
        self.模式 = 模式

    def 获取函数签名(self, 模块名: str, 函数名: str) -> 成员元数据 | None:
        if self.模式 == "off":
            return None
        try:
            import importlib
            import inspect
            mod = importlib.import_module(模块名)
            if not hasattr(mod, 函数名):
                return None
            obj = getattr(mod, 函数名)
            if inspect.isfunction(obj):
                sig = str(inspect.signature(obj))
                return 成员元数据(名称=函数名, 类型="function", 签名=sig, 来源="runtime")
            elif inspect.isclass(obj):
                return 成员元数据(名称=函数名, 类型="class", 来源="runtime")
            return 成员元数据(名称=函数名, 类型="variable", 来源="runtime")
        except Exception:
            return None

    def 获取模块成员(self, 模块名: str) -> list[成员元数据]:
        """获取模块的所有可访问成员。"""
        if self.模式 == "off":
            return []
        try:
            import importlib
            mod = importlib.import_module(模块名)
            members = []
            for name in dir(mod):
                if name.startswith("_"):
                    continue
                obj = getattr(mod, name)
                if callable(obj):
                    members.append(成员元数据(名称=name, 类型="function" if not isinstance(obj, type) else "class", 来源="runtime"))
                else:
                    members.append(成员元数据(名称=name, 类型="variable", 来源="runtime"))
            return members[:100]
        except Exception:
            return []
