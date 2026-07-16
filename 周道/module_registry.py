"""周道模块注册表：缓存与循环检测 v0.0.8"""

from __future__ import annotations
from typing import Any


class ModuleRegistry:
    """模块注册表（单例）。

    管理模块缓存和循环引入检测。
    每个规范化模块路径在一个运行上下文中只初始化一次。
    """

    def __init__(self):
        self._缓存: dict[str, Any] = {}  # 规范化路径 → 模块对象
        self._加载中: list[str] = []     # 当前正在加载的路径（用于循环检测）

    # ── 循环检测 ──

    def 开始加载(self, 路径: str) -> None:
        """标记模块开始加载。检测循环引入。"""
        if 路径 in self._加载中:
            路径链 = " → ".join(self._加载中 + [路径])
            raise 循环引入错误(f"检测到循环引入：{路径链}")
        self._加载中.append(路径)

    def 完成加载(self, 路径: str) -> None:
        """标记模块加载完成。"""
        if 路径 in self._加载中:
            self._加载中.remove(路径)

    # ── 缓存管理 ──

    def is_loaded(self, 路径: str) -> bool:
        return 路径 in self._缓存

    def get_module(self, 路径: str) -> Any | None:
        return self._缓存.get(路径)

    def register(self, 路径: str, 模块对象: Any) -> None:
        self._缓存[路径] = 模块对象

    def clear(self) -> None:
        self._缓存.clear()
        self._加载中.clear()

    @property
    def 加载中(self) -> list[str]:
        return list(self._加载中)


class 循环引入错误(Exception):
    """循环引入错误。"""
    pass
