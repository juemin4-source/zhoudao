"""周道：Core IR（核心中间表示）。

Core IR 表示程序实际要做什么，不包含表层句法差异。
同一语义的不同表层句式在此降解为同一种 Core IR 节点。

设计原则：
- Core IR 不包含 Python 专属语法糖
- Core IR 不重新分词或重新判断精确名称
- Core IR 不自带源位置（Lowering 完成后位置信息不再需要）
- 所有降低逻辑在 lowering.py 中，不泄漏到 Core IR 自身
"""

from dataclasses import dataclass, field
from typing import Any


# ==================== 程序顶层 ====================

from enum import Enum

class 文章类型(Enum):
    自由 = "FREE"
    模块 = "MODULE"
    程序 = "PROGRAM"

@dataclass
class 程序IR:
    """Core IR 程序：顺序语句列表。"""
    语句列表: list["语句IR"] = field(default_factory=list)
    文章类型: "文章类型 | None" = None
    模块路径: str | None = None


# ==================== 语句基类 ====================

@dataclass
class 语句IR:
    """Core IR 语句基类。"""
    pass


# ==================== 语句类型 ====================

@dataclass
class 赋值IR(语句IR):
    """赋值：左值 = 表达式。统一了 绑定、变更、空值绑定、命题绑定、命题变更。

    是新绑定: True 表示设（新变量创建），False 表示使（已存在变量修改）。
    """
    目标: "表达式IR"
    值: "表达式IR | None" = None
    是新绑定: bool = False


@dataclass
class 算术赋值IR(语句IR):
    """算术赋值：左值 +=/-=/*=//= 表达式。"""
    目标: "表达式IR"
    算符: str
    值: "表达式IR"


@dataclass
class 打印IR(语句IR):
    """打印表达式。"""
    值: "表达式IR"


@dataclass
class 如果IR(语句IR):
    """条件分支。"""
    条件: "表达式IR"
    则: list["语句IR"] = field(default_factory=list)
    否则如果: list[tuple["表达式IR", list["语句IR"]]] = field(default_factory=list)
    否则: list["语句IR"] = field(default_factory=list)


@dataclass
class 当循环IR(语句IR):
    """当循环（while）。"""
    条件: "表达式IR"
    体: list["语句IR"] = field(default_factory=list)


@dataclass
class 遍历IR(语句IR):
    """遍历（for）。"""
    元素: str
    集合: "表达式IR"
    体: list["语句IR"] = field(default_factory=list)


@dataclass
class 尝试IR(语句IR):
    """尝试 / 异常处理。v0.0.9: 支持分类捕获。"""
    体: list["语句IR"] = field(default_factory=list)
    异常体: list["语句IR"] = field(default_factory=list)
    异常名: str | None = None
    最终体: list["语句IR"] = field(default_factory=list)
    错误类型处理: list[tuple[str, list["语句IR"]]] = field(default_factory=list)
    有泛化处理: bool = False


@dataclass
class 跳出IR(语句IR):
    """跳出循环（break）。"""
    pass


@dataclass
class 继续IR(语句IR):
    """继续下一轮（continue）。"""
    pass


@dataclass
class 以所得IR(语句IR):
    """以表达式为所得（return）。"""
    值: "表达式IR"


@dataclass
class 函数定义IR(语句IR):
    """函数定义。is_async 和 is_generator 由降低器检测并设置。"""
    名称: str
    参数: list[str] = field(default_factory=list)
    体: list["语句IR"] = field(default_factory=list)
    单表达式: bool = False
    是异步: bool = False
    是生成器: bool = False
    # v0.0.8: 参数默认值（追加在末尾，不破坏位置构造）
    参数默认值: list["表达式IR | None"] = field(default_factory=list)


@dataclass
class 引入IR(语句IR):
    """引入模块（import）。"""
    模块: str


@dataclass
class 从中引入IR(语句IR):
    """从模块中引入名称（from … import …）。"""
    模块: str
    名称: list[str] = field(default_factory=list)


@dataclass
class 导入别名IR(语句IR):
    """引入别名（import … as …）。"""
    模块: str
    别名: str


@dataclass
class 断言IR(语句IR):
    """断言条件成立。"""
    表达式: "表达式IR"
    消息: str | None = None


@dataclass
class 类别声明IR(语句IR):
    """类别声明（@dataclass class）。"""
    名称: str
    字段列表: list["类别字段IR"] = field(default_factory=list)


@dataclass
class 类别方法IR(语句IR):
    """v0.0.9: 类别实例方法。字段在末尾，不破坏位置构造。"""
    类别名: str
    名称: str
    参数: list[str] = field(default_factory=list)
    参数默认值: list['表达式IR | None'] = field(default_factory=list)
    体: list["语句IR"] = field(default_factory=list)
    单表达式: bool = False
    是异步: bool = False
    是生成器: bool = False


@dataclass
class 原样报出IR(语句IR):
    """v0.0.9: 原样报出当前错误。"""
    pass


@dataclass
class 等待记作IR(语句IR):
    """v0.0.9: 等待甲完成，记作乙。"""
    调用: "表达式IR"
    记作名: str


@dataclass
class 异步遍历IR(语句IR):
    """v0.0.9: 每等到一项记作（async for）。"""
    集合: "表达式IR"
    元素: str
    体: list["语句IR"] = field(default_factory=list)


@dataclass
class 删除IR(语句IR):
    """删除左值（del）。"""
    目标: "表达式IR"


@dataclass
class 空操作IR(语句IR):
    """空操作（pass）。"""
    pass


@dataclass
class 报错IR(语句IR):
    """报错（raise RuntimeError）。v0.0.9: 支持错误类型。"""
    消息: str
    错误类型: str | None = None


@dataclass
class 依次给出IR(语句IR):
    """依次给出（yield）。"""
    值: "表达式IR"


@dataclass
class 等待语句IR(语句IR):
    """等待调用完成（await …）。v0.0.9: 支持记作结果。"""
    调用: "表达式IR"
    记作名: str | None = None


@dataclass
class 全局声明IR(语句IR):
    """全局声明（global）。"""
    名称: list[str] = field(default_factory=list)


@dataclass
class 外层声明IR(语句IR):
    """外层声明（nonlocal）。"""
    名称: list[str] = field(default_factory=list)


@dataclass
class 最终收束IR(语句IR):
    """无论是否出错，最后执行。"""
    体: list["语句IR"] = field(default_factory=list)


@dataclass
class 分情形IR(语句IR):
    """依表达式分情形（match / case）。"""
    对象: "表达式IR"
    分支列表: list[tuple["表达式IR | None", list["语句IR"]]] = field(default_factory=list)


@dataclass
class 公开声明IR(语句IR):
    """v0.0.8: 本文公开声明。"""
    名称: list[str] = field(default_factory=list)


@dataclass
class 程序入口IR(语句IR):
    """v0.0.8: 运行如下入口。v0.0.9: 支持异步入口。"""
    体: list["语句IR"] = field(default_factory=list)
    是异步: bool = False


@dataclass
class 本地模块引入IR(语句IR):
    """v0.0.8: 引入周道文《工具》。"""
    模块名: str
    别名: str | None = None


@dataclass
class 从本地模块引入IR(语句IR):
    """v0.0.8: 从周道文《工具》中引入 整理、统计。"""
    模块名: str
    名称: list[str] = field(default_factory=list)


@dataclass
class 表达式语句IR(语句IR):
    """表达式作为语句执行（函数调用作为语句）。"""
    表达式: "表达式IR"


# ==================== 表达式基类 ====================

@dataclass
class 表达式IR:
    """Core IR 表达式基类。"""
    pass


# ==================== 表达式类型 ====================

@dataclass
class 整数常量IR(表达式IR):
    值: int


@dataclass
class 小数常量IR(表达式IR):
    值: float


@dataclass
class 文本常量IR(表达式IR):
    值: str


@dataclass
class 布尔常量IR(表达式IR):
    值: bool


@dataclass
class 空值IR(表达式IR):
    pass


@dataclass
class 列表字面量IR(表达式IR):
    元素: list["表达式IR"] = field(default_factory=list)


@dataclass
class 元组字面量IR(表达式IR):
    """v0.0.8: 元组字面量。"""
    元素: list["表达式IR"] = field(default_factory=list)


@dataclass
class 集合字面量IR(表达式IR):
    """v0.0.8: 集合字面量。"""
    元素: list["表达式IR"] = field(default_factory=list)


@dataclass
class 映射字面量IR(表达式IR):
    条目: list[tuple["表达式IR", "表达式IR"]] = field(default_factory=list)


@dataclass
class 变量引用IR(表达式IR):
    名称: str
    名称来源: str = "ORDINARY"  # ORDINARY | EXACT | CONTEXTUAL


@dataclass
class 二元运算IR(表达式IR):
    左: "表达式IR"
    算符: str
    右: "表达式IR"


@dataclass
class 一元运算IR(表达式IR):
    算符: str
    操作数: "表达式IR"


@dataclass
class 调用IR(表达式IR):
    """函数调用。v0.0.8: 支持制定参数。"""
    函数: "表达式IR"
    参数: list["表达式IR"] = field(default_factory=list)
    制定参数: list[tuple[str, "表达式IR"]] = field(default_factory=list)


@dataclass
class 身份判断IR(表达式IR):
    左: "表达式IR"
    右: "表达式IR"
    肯定: bool = True


@dataclass
class 等待表达式IR(表达式IR):
    调用: "表达式IR"


@dataclass
class 当前错误IR(表达式IR):
    """异常处理中引用的异常对象。"""
    pass


@dataclass
class 错误文本IR(表达式IR):
    """str(异常对象)。"""
    pass


@dataclass
class 成员访问IR(表达式IR):
    对象: "表达式IR"
    成员: str


@dataclass
class 字符串下标IR(表达式IR):
    对象: "表达式IR"
    键: str


@dataclass
class 表达式下标IR(表达式IR):
    对象: "表达式IR"
    索引: "表达式IR"


@dataclass
class 切片下标IR(表达式IR):
    对象: "表达式IR"
    开始: "表达式IR | None" = None
    结束: "表达式IR | None" = None


# ==================== 辅助类型 ====================

@dataclass
class 类别字段IR:
    """Core IR 类别字段定义。"""
    名称: str
    类型: str | None = None
    默认值: "表达式IR | None" = None
    可空: bool = False
    不得为负: bool = False
