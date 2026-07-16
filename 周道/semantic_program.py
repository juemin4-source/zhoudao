"""周道 v0.0.6: SemanticProgram — 语义分析输出。

经过语义分析的程序，包含 Core IR + 已解析绑定信息。
SemanticProgram 是正式 Emitter 唯一允许的输入。
不得存放 Python 源码片段作为逃生数据。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .errors import 源码位置


# ── 语义诊断级别 ──────────────────────────────────────────────

class 诊断级别:
    """语义诊断级别。"""
    错误 = "ERROR"
    警告 = "WARNING"
    信息 = "INFO"


# ── 语义诊断 ──────────────────────────────────────────────────

@dataclass(frozen=True)
class 语义诊断:
    """一次语义分析的诊断结果，必须附带周道 SourceSpan。"""
    消息: str
    位置: 源码位置 | None = None
    级别: str = 诊断级别.错误
    代码: str = ""

    def 格式化(self) -> str:
        前缀 = f"[{self.位置.格式化()}]" if self.位置 else ""
        return f"{前缀} 语义{self.级别}: {self.消息}"

    def __str__(self) -> str:
        return self.格式化()


# ── 作用域快照 ────────────────────────────────────────────────

@dataclass
class 作用域快照:
    """语义分析中单个作用域的快照，用于调试和 Trace。"""
    类型: str  # "global" | "function" | "control" | "category" | "match"
    行范围: tuple[int, int] | None = None
    名称列表: list[str] = field(default_factory=list)

    @property
    def 名称数量(self) -> int:
        return len(self.名称列表)


# ── 已解析引用 ────────────────────────────────────────────────

@dataclass(frozen=True)
class 已解析引用:
    """语义分析完成后的一个已解析名称引用。

    将 Core IR 中的名称引用与其作用域中的绑定关联起来。
    """
    名称: str
    来源: str  # "user" | "prelude" | "module" | "parameter"
    作用域类型: str = ""
    位置: 源码位置 | None = None
    名称来源: str = "ORDINARY"  # ORDINARY | EXACT | CONTEXTUAL — 来自原始标识符


# ── 语义程序 ──────────────────────────────────────────────────

# ── v0.0.9 新增数据类型 ──────────────────────────────

@dataclass(frozen=True)
class 类别方法绑定:
    类别名: str
    方法名: str
    参数: tuple[str, ...]
    是异步: bool = False
    是生成器: bool = False

@dataclass(frozen=True)
class 错误处理计划:
    类型名: str
    处理体索引: int

# ── 预定义错误类型列表 ──────────────────────────────────

预定义错误类型表: dict[str, str] = {
    "运行出错": "RuntimeError",
    "值出错": "ValueError",
    "类型出错": "TypeError",
    "键出错": "KeyError",
    "索引出错": "IndexError",
    "文件未找到出错": "FileNotFoundError",
}

def 是否已知错误类型(名称: str) -> bool:
    return 名称 in 预定义错误类型表


@dataclass
class SemanticProgram:
    """语义分析后的程序。

    包装 Core IR 程序，附加完整的诊断和名称解析信息。
    正式 Emitter 唯一允许的输入类型。

    属性:
        core_ir: 经过语义验证的 Core IR 程序
        诊断列表: 语义分析过程中产生的全部诊断
        有错误: 是否存在级别为 ERROR 的诊断
    """
    core_ir: object  # 程序IR (forward ref to avoid circular at runtime)
    诊断列表: list[语义诊断] = field(default_factory=list)
    引用映射: dict[int, 已解析引用] = field(default_factory=dict)
    作用域列表: list[作用域快照] = field(default_factory=list)

    # v0.0.9 新增数据
    类别方法表: dict[str, dict[str, 类别方法绑定]] = field(default_factory=dict)
    入口是异步: bool = False

    # ── 查询 ────────────────────────────────────────────────

    @property
    def 有错误(self) -> bool:
        return any(d.级别 == 诊断级别.错误 for d in self.诊断列表)

    def 添加诊断(self, 消息: str, 位置: 源码位置 | None = None,
                  级别: str = 诊断级别.错误, 代码: str = "") -> None:
        """添加一条新的诊断。"""
        self.诊断列表.append(语义诊断(
            消息=消息, 位置=位置, 级别=级别, 代码=代码,
        ))

    def 全部错误(self) -> list[语义诊断]:
        """返回所有 ERROR 级别的诊断。"""
        return [d for d in self.诊断列表 if d.级别 == 诊断级别.错误]

    def 格式化诊断(self) -> str:
        """将所有诊断格式化为可读字符串。"""
        return "\n".join(d.格式化() for d in self.诊断列表)

    def __str__(self) -> str:
        状态 = "有错误" if self.有错误 else "通过"
        return f"SemanticProgram({状态}, {len(self.诊断列表)} 条诊断)"
