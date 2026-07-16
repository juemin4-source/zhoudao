"""周道 InternalNameAllocator — 后端内部名称分配器 v0.0.7

确保内部生成的 Python 名称不会与用户定义名称冲突。
所有内部名称以 `_zd_` 为前缀，且由 Allocator 统一管理。

设计原则：
- 分配器必须检查 SemanticProgram 中所有用户名称，避免碰撞。
- 不得假定双下划线名称一定不会被用户使用。
- 内部名称必须稳定、可测试，并标记为 synthetic。
- 内部名称不得出现在正常用户诊断中。
"""

from __future__ import annotations


class InternalNameAllocator:
    """内部名称分配器。

    分配稳定、无冲突的内部 Python 名称。
    所有内部名称以 `_zd_` 为前缀，并检查不与用户名称冲突。

    Usage:
        alloc = InternalNameAllocator(用户名称集={"甲", "乙"})
        tmp = alloc.allocate("tmp")   # → "_zd_tmp_0"
        err = alloc.allocate("err")   # → "_zd_err_1"
    """

    def __init__(self, 用户名称集: set[str] | None = None):
        self._计数器: int = 0
        self._已分配: set[str] = set()
        self._用户名称集 = 用户名称集 or set()

    @property
    def 已分配(self) -> frozenset[str]:
        """返回所有已分配的内部名称（只读）。"""
        return frozenset(self._已分配)

    def allocate(self, 提示: str = "tmp") -> str:
        """分配一个不重复的内部名称。

        Args:
            提示: 名称提示词，用于生成可读的内部名称

        Returns:
            唯一的内部名称字符串

        Raises:
            RuntimeError: 当所有可能名称耗尽时（实际不可能发生）
        """
        while True:
            name = f"_zd_{提示}_{self._计数器}"
            self._计数器 += 1
            if name not in self._用户名称集 and name not in self._已分配:
                self._已分配.add(name)
                return name
            # 安全阀：防止无限循环（一百万次后放弃）
            if self._计数器 > 1_000_000:
                # 使用哈希后缀作为最终手段
                import hashlib
                name = f"_zd_{提示}_{hashlib.md5(str(self._计数器).encode()).hexdigest()[:8]}"
                self._已分配.add(name)
                return name

    def allocate_multiple(self, 数量: int, 提示: str = "tmp") -> list[str]:
        """批量分配多个内部名称。"""
        return [self.allocate(提示) for _ in range(数量)]

    def is_internal_name(self, name: str) -> bool:
        """判断一个名称是否为内部名称。"""
        return name.startswith("_zd_") or name in self._已分配

    def reserve(self, name: str) -> bool:
        """预占一个名称，防止后续分配器使用。

        Returns:
            True 如果成功预占，False 如果名称已被占用
        """
        if name in self._用户名称集 or name in self._已分配:
            return False
        self._已分配.add(name)
        return True
