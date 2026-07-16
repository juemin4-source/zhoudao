"""周道 BackendSourceMap — 后端源码映射与诊断代码 v0.0.7

提供完整的后端源码位置映射体系：

1. SourceMapRecord: 单条映射记录（含 synthetic 标记）
2. BackendSourceMap: 完整映射表（多方向索引）
3. 诊断代码常量: ZB7001-ZB7007 / ZR7101-ZR7102

设计不变量：
- 用户来源节点不得缺失 SourceSpan。
- Synthetic 节点必须说明生成原因。
- 同一个周道节点可以生成多个 Python AST 节点。
- 一个 Python AST 用户节点只能有一个主要 SourceSpan。
- SourceMap 不得存储生成 Python 文本作为定位依据。
"""

from __future__ import annotations

import ast
import sys
from typing import Any

from .errors import 源码位置


# ================================================================
# 诊断代码
# ================================================================

# ── ZB 类：编译器内部或后端错误，不得归咎于用户周道语法 ──

ZB7001_UNSUPPORTED_IR_NODE = "ZB7001"
"""不支持的 Core IR 节点类型。"""

ZB7002_INVALID_SEMANTIC_PROGRAM = "ZB7002"
"""SemanticProgram 状态不合法（例如含有语义错误时仍要求发射）。"""

ZB7003_PYTHON_AST_BUILD_FAILURE = "ZB7003"
"""Python AST 构建失败（内部不变量违反）。"""

ZB7004_PYTHON_COMPILE_FAILURE = "ZB7004"
"""Python compile() 失败（生成代码不合法）。"""

ZB7005_SOURCE_MAP_MISSING = "ZB7005"
"""缺少必需的 SourceMap 记录。"""

ZB7006_INVALID_PYTHON_LOCATION = "ZB7006"
"""Python 位置信息不合法（行列值超出范围）。"""

ZB7007_INTERNAL_NAME_COLLISION = "ZB7007"
"""内部名称与用户名称碰撞。"""

# ── ZR 类：运行时错误包装 ──

ZR7101_RUNTIME_ERROR = "ZR7101"
"""已包装的用户程序运行时错误。保留原始异常类型和因果链。"""

ZR7102_RUNTIME_LOCATION_UNAVAILABLE = "ZR7102"
"""运行时异常位置无法映射到周道原文。"""


def 诊断消息(代码: str, 消息: str) -> str:
    """生成带诊断代码的错误消息。"""
    return f"[{代码}] {消息}"


# ================================================================
# SourceMapRecord
# ================================================================


class SourceMapRecord:
    """一条后端源码映射记录。

    记录一个 Python AST 节点与周道源码位置之间的对应关系。
    """

    __slots__ = (
        "backend_node_id",
        "python_ast_kind",
        "python_lineno",
        "python_col_offset",
        "python_end_lineno",
        "python_end_col_offset",
        "周道位置",
        "origin_node_id",
        "is_synthetic",
        "synthetic_reason",
    )

    def __init__(
        self,
        backend_node_id: int,
        python_ast_kind: str,
        python_lineno: int | None = None,
        python_col_offset: int | None = None,
        python_end_lineno: int | None = None,
        python_end_col_offset: int | None = None,
        周道位置: 源码位置 | None = None,
        origin_node_id: int | None = None,
        is_synthetic: bool = False,
        synthetic_reason: str = "",
    ):
        self.backend_node_id = backend_node_id
        self.python_ast_kind = python_ast_kind
        self.python_lineno = python_lineno
        self.python_col_offset = python_col_offset
        self.python_end_lineno = python_end_lineno
        self.python_end_col_offset = python_end_col_offset
        self.周道位置 = 周道位置
        self.origin_node_id = origin_node_id
        self.is_synthetic = is_synthetic
        self.synthetic_reason = synthetic_reason

    @property
    def python_position(self) -> tuple[int, int, int, int] | None:
        """Python AST 位置元组 (lineno, col_offset, end_lineno, end_col_offset)。"""
        if self.python_lineno is None:
            return None
        return (
            self.python_lineno,
            self.python_col_offset or 0,
            self.python_end_lineno or self.python_lineno,
            self.python_end_col_offset or 0,
        )

    def __repr__(self) -> str:
        synthetic = " [SYNTHETIC]" if self.is_synthetic else ""
        pos = f"L{self.python_lineno}:{self.python_col_offset}" if self.python_lineno else "?"
        origin = f" ← IR#{self.origin_node_id}" if self.origin_node_id else ""
        周道 = f" 周道{self.周道位置.格式化()}" if self.周道位置 else ""
        return f"<{self.python_ast_kind}@{pos}{synthetic}{origin}{周道}>"


# ================================================================
# BackendSourceMap
# ================================================================


class BackendSourceMap:
    """后端源码映射表。

    维护四种查询索引：
    1. BackendNodeId → SourceSpan
    2. Python 行区间 → SourceSpan
    3. OriginNodeId → Python AST 节点集合
    4. 运行时代码位置 → SourceSpan
    """

    def __init__(self):
        # 主记录存储
        self._记录列表: list[SourceMapRecord] = []

        # 索引 1: backend_node_id → SourceMapRecord
        self._节点索引: dict[int, SourceMapRecord] = {}

        # 索引 2: python_lineno → list[SourceMapRecord]
        self._行索引: dict[int, list[SourceMapRecord]] = {}

        # 索引 3: origin_node_id → list[SourceMapRecord]
        self._来源索引: dict[int, list[SourceMapRecord]] = {}

    # ── 写入 ─────────────────────────────────────────────────

    def add_record(self, record: SourceMapRecord) -> None:
        """添加一条映射记录并更新索引。"""
        self._记录列表.append(record)

        bid = record.backend_node_id
        if bid is not None:
            self._节点索引[bid] = record

        lineno = record.python_lineno
        if lineno is not None:
            if lineno not in self._行索引:
                self._行索引[lineno] = []
            self._行索引[lineno].append(record)

        oid = record.origin_node_id
        if oid is not None:
            if oid not in self._来源索引:
                self._来源索引[oid] = []
            self._来源索引[oid].append(record)

    def add_mapping(
        self,
        backend_node_id: int,
        python_node: ast.AST,
        python_ast_kind: str | None = None,
        周道位置: 源码位置 | None = None,
        origin_node_id: int | None = None,
        is_synthetic: bool = False,
        synthetic_reason: str = "",
    ) -> SourceMapRecord:
        """便捷方法: 从 Python AST 节点创建映射记录。"""
        kind = python_ast_kind or type(python_node).__name__
        record = SourceMapRecord(
            backend_node_id=backend_node_id,
            python_ast_kind=kind,
            python_lineno=getattr(python_node, "lineno", None),
            python_col_offset=getattr(python_node, "col_offset", None),
            python_end_lineno=getattr(python_node, "end_lineno", None),
            python_end_col_offset=getattr(python_node, "end_col_offset", None),
            周道位置=周道位置,
            origin_node_id=origin_node_id,
            is_synthetic=is_synthetic,
            synthetic_reason=synthetic_reason,
        )
        self.add_record(record)
        return record

    # ── 查询 ─────────────────────────────────────────────────

    def by_backend_node_id(self, node_id: int) -> SourceMapRecord | None:
        """通过后端节点 ID 查询。"""
        return self._节点索引.get(node_id)

    def by_python_line(self, lineno: int) -> list[SourceMapRecord]:
        """通过 Python 行号查询。"""
        return self._行索引.get(lineno, [])

    def by_python_position(
        self, lineno: int, col_offset: int
    ) -> SourceMapRecord | None:
        """通过 Python 行列位置查询（精确匹配）。"""
        for record in self._行索引.get(lineno, []):
            if record.python_col_offset == col_offset:
                return record
        return None

    def by_origin_node_id(self, origin_id: int) -> list[SourceMapRecord]:
        """通过来源 IR 节点 ID 查询（一个 IR 节点可能生成多个 Python 节点）。"""
        return self._来源索引.get(origin_id, [])

    def by_runtime_line(self, py_line: int) -> SourceMapRecord | None:
        """通过运行时代码行号查询（用于 traceback 映射）。

        选择该行上具有最精确位置信息的记录。
        """
        records = self._行索引.get(py_line, [])
        if not records:
            return None
        # 优先返回有周道位置的非 synthetic 记录
        for r in records:
            if not r.is_synthetic and r.周道位置 is not None:
                return r
        # 其次返回任何有周道位置的记录
        for r in records:
            if r.周道位置 is not None:
                return r
        return records[0]

    def 周道位置_by_python_line(self, py_line: int) -> 源码位置 | None:
        """Python 行号 → 周道源码位置（最快路径，用于运行时回溯）。"""
        record = self.by_runtime_line(py_line)
        return record.周道位置 if record else None

    # ── 聚合 ─────────────────────────────────────────────────

    @property
    def all_records(self) -> list[SourceMapRecord]:
        """所有映射记录。"""
        return list(self._记录列表)

    @property
    def user_records(self) -> list[SourceMapRecord]:
        """所有用户来源的映射记录（非 synthetic）。"""
        return [r for r in self._记录列表 if not r.is_synthetic]

    @property
    def synthetic_records(self) -> list[SourceMapRecord]:
        """所有 synthetic 映射记录。"""
        return [r for r in self._记录列表 if r.is_synthetic]

    @property
    def record_count(self) -> int:
        return len(self._记录列表)

    @property
    def missing_source_records(self) -> list[SourceMapRecord]:
        """缺少周道位置的 user 记录（违反不变量）。"""
        return [r for r in self._记录列表 if not r.is_synthetic and r.周道位置 is None]

    # ── 序列化 ───────────────────────────────────────────────

    def to_dict_list(self) -> list[dict[str, Any]]:
        """导出为可序列化的字典列表（用于测试断言）。"""
        result = []
        for r in self._记录列表:
            d: dict[str, Any] = {
                "backend_node_id": r.backend_node_id,
                "python_ast_kind": r.python_ast_kind,
                "is_synthetic": r.is_synthetic,
            }
            if r.python_lineno is not None:
                d["python_lineno"] = r.python_lineno
            if r.周道位置 is not None:
                d["周道行"] = r.周道位置.行
                d["周道列"] = r.周道位置.列
            if r.origin_node_id is not None:
                d["origin_node_id"] = r.origin_node_id
            if r.is_synthetic and r.synthetic_reason:
                d["synthetic_reason"] = r.synthetic_reason
            result.append(d)
        return result
