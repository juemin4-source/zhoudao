"""跨模块 SourceMap 注册表 v0.0.8

维护多个周道文件的 SourceMap，用于跨文件运行时错误回溯。
"""

from __future__ import annotations
import os
from .errors import 源码位置


class 跨模块SourceMap:
    """多模块 SourceMap 注册表。

    跨模块运行时错误需要将 Python 调用栈中的每个帧
    映射到对应的周道文件位置。
    """

    def __init__(self):
        # 文件路径 → {Python行号 → 周道源码位置}（简易映射）
        self._模块映射: dict[str, dict[int, 源码位置]] = {}
        # 文件路径 → BackendSourceMap（全量映射）
        self._source_maps: dict[str, object] = {}

    def register(self, 文件路径: str, 行映射: dict[int, 源码位置] | None = None) -> None:
        """注册一个模块的行映射（兼容旧式 dict 映射）。"""
        if 行映射 is not None:
            self._模块映射[文件路径] = 行映射

    def lookup(self, 文件路径: str, py_lineno: int) -> 源码位置 | None:
        """查询 Python 行号对应的周道源码位置。"""
        行映射 = self._模块映射.get(文件路径)
        if 行映射 is None:
            return None
        return 行映射.get(py_lineno)

    @property
    def registered_modules(self) -> list[str]:
        return list(self._模块映射.keys())

    def register_source_map(self, 文件路径: str, source_map) -> None:
        """注册一个模块的全量 BackendSourceMap（含 Python AST 级映射）。"""
        self._source_maps[文件路径] = source_map

    def get_source_map(self, 文件路径: str):
        """获取模块的全量 BackendSourceMap。"""
        return self._source_maps.get(文件路径)

    @property
    def 所有模块(self) -> list[str]:
        return list(self._模块映射.keys())

    def format_traceback(self, frames: list[tuple[str, int, str]]) -> str:
        """将 Python 帧列表格式化为周道调用栈。"""
        lines = []
        for i, (文件, py_line, func_name) in enumerate(frames):
            zd_pos = self.lookup(文件, py_line)
            if zd_pos is not None:
                位置 = f"第{zd_pos.行}行第{zd_pos.列}列"
                if func_name and func_name != '<module>':
                    lines.append(f"  [{i}] {func_name} 位于 {位置}")
                else:
                    lines.append(f"  [{i}] 顶层 位于 {位置}")
            else:
                lines.append(f"  [{i}] {os.path.basename(文件)}:{py_line}")
        return '\n'.join(lines)
