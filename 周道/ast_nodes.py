"""周道：AST 节点类型定义。"""

from dataclasses import dataclass, field
from typing import Any
from .errors import 源码位置


@dataclass(kw_only=True)
class 节点:
    """所有节点的基类。"""
    位置: 源码位置 | None = None


# === 程序结构 ===

@dataclass
class 程序(节点):
    句子列表: list["句子"] = field(default_factory=list)


@dataclass
class 句子(节点):
    语句列表: list["语句"] = field(default_factory=list)
    前导注释: list[str] = field(default_factory=list)
    尾行注释: str | None = None


# === 语句 ===

@dataclass
class 语句(节点):
    """语句基类。"""
    pass


@dataclass
class 绑定(语句):
    名称: str
    值: "表达式 | None" = None


@dataclass
class 空值绑定(语句):
    """设标识符没有值。"""
    名称: str


@dataclass
class 命题绑定(语句):
    """设标识符成立 / 设标识符不成立。"""
    名称: str
    值: bool  # True=成立, False=不成立


@dataclass
class 变更(语句):
    """使左值变为表达式。"""
    目标: "表达式"
    值: "表达式"


@dataclass
class 算术变更(语句):
    """使左值加/减/乘/除表达式。"""
    目标: "表达式"
    算符: str  # += -= *= /=
    值: "表达式"


@dataclass
class 命题变更(语句):
    """使左值成立 / 使左值不成立。"""
    目标: "表达式"
    值: bool


@dataclass
class 打印(语句):
    值: "表达式"


@dataclass
class 如果(语句):
    条件: "表达式"
    则: list[语句] = field(default_factory=list)
    否则如果: list[tuple["表达式", list[语句]]] = field(default_factory=list)
    否则: list[语句] = field(default_factory=list)


@dataclass
class 当循环(语句):
    条件: "表达式"
    体: list[语句] = field(default_factory=list)


@dataclass
class 遍历(语句):
    元素: str  # 记作的元素名
    集合: "表达式"
    体: list[语句] = field(default_factory=list)


@dataclass
class 尝试(语句):
    体: list[语句] = field(default_factory=list)
    异常体: list[语句] = field(default_factory=list)
    异常名: str | None = None
    最终体: list[语句] = field(default_factory=list)  # 无论是否出错，最后
    错误类型处理: list[tuple[str, list[语句]]] = field(default_factory=list)
    有泛化处理: bool = False


@dataclass
class 跳出(语句):
    pass


@dataclass
class 继续(语句):
    pass


@dataclass
class 以所得(语句):
    """以表达式为所得（函数结果）。"""
    值: "表达式"


@dataclass
class 函数定义(语句):
    名称: str
    参数: list[str] = field(default_factory=list)
    体: list[语句] = field(default_factory=list)
    单表达式: bool = False
    参数默认值: list["表达式 | None"] = field(default_factory=list)


@dataclass
class 引入(语句):
    模块: str


@dataclass
class 从中引入(语句):
    模块: str
    名称: list[str] = field(default_factory=list)
    别名: str | None = None  # 引入《甲》，下文简称乙


@dataclass
class 导入别名(语句):
    """引入《甲》，下文简称乙。"""
    模块: str
    别名: str


@dataclass
class 断言(语句):
    """甲须/不得满足条件。"""
    表达式: "表达式"
    消息: str | None = None  # 否则报错【消息】


@dataclass
class 类别声明(语句):
    """设置甲类别，包括乙、丙。"""
    名称: str
    字段列表: list["类别字段"] = field(default_factory=list)


@dataclass
class 类别字段:
    """类别中的一个字段。"""
    名称: str
    类型: str | None = None  # 文本/整数
    默认值: "表达式 | None" = None
    可空: bool = False
    不得为负: bool = False


@dataclass
class 删除(语句):
    """删去（名称、成员或项目）。"""
    目标: "表达式"


@dataclass
class 空操作(语句):
    """不作处理。"""
    pass


@dataclass
class 报错(语句):
    """报错【说明】。v0.0.9: 支持错误类型。"""
    消息: str
    错误类型: str | None = None


@dataclass
class 依次给出(语句):
    """依次给出甲。"""
    值: "表达式"


@dataclass
class 等待语句(语句):
    """等待甲完成。v0.0.9: 支持 等待…完成，记作结果。"""
    调用: "调用"
    记作名: str | None = None


@dataclass
class 异步遍历(语句):
    """v0.0.9: 从甲中，每等到一项记作乙，就丙。"""
    集合: "表达式"
    元素: str
    体: list[语句] = field(default_factory=list)


@dataclass
class 原样报出(语句):
    """v0.0.9: 原样报出当前错误。"""
    pass





@dataclass
class 全局声明(语句):
    """下文所用甲，均指全局的甲。"""
    名称: list[str] = field(default_factory=list)


@dataclass
class 外层声明(语句):
    """下文所用甲，指本定义外层的甲。"""
    名称: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class 本地模块引入(语句):
    """v0.0.8: 引入周道文《工具》。"""
    模块名: str
    别名: str | None = None


@dataclass(kw_only=True)
class 从本地模块引入(语句):
    """v0.0.8: 从周道文《工具》中引入 整理、统计。"""
    模块名: str
    名称: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class 类别方法定义(语句):
    """v0.0.9: 定义甲类别的乙（参数）如下：。"""
    类别名: str
    名称: str
    参数: list[str] = field(default_factory=list)
    参数默认值: list['表达式 | None'] = field(default_factory=list)
    体: list['语句'] = field(default_factory=list)


@dataclass(kw_only=True)
class 公开声明(语句):
    """v0.0.8: 本文公开 整理、统计。"""
    名称: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class 运行入口(语句):
    """v0.0.8: 运行如下入口。"""
    体: list['语句'] = field(default_factory=list)


@dataclass
class 最终收束(语句):
    """无论是否出错，最后甲。"""
    体: list[语句] = field(default_factory=list)


@dataclass
class 分情形(语句):
    """依甲分情形：若为乙，就丙；其余就丁。"""
    对象: "表达式"
    分支列表: list[tuple[str | None, list[语句]]] = field(default_factory=list)
    # 分支： (字面量值或 None(其余), 语句列表)


@dataclass
class 表达式语句(语句):
    """括号分组内的动作序列。"""
    表达式: "表达式 | None" = None
    动作列表: list["语句"] = field(default_factory=list)

# === 表达式 ===

@dataclass
class 表达式(节点):
    """表达式基类。"""
    pass


@dataclass
class 整数(表达式):
    值: int


@dataclass
class 小数(表达式):
    值: float


@dataclass
class 文本(表达式):
    值: str


@dataclass
class 布尔(表达式):
    值: bool


@dataclass
class 空值(表达式):
    pass


@dataclass
class 列表字面量(表达式):
    元素: list["表达式"] = field(default_factory=list)


@dataclass
class 元组字面量(表达式):
    """v0.0.8: 元组字面量。"""
    元素: list["表达式"] = field(default_factory=list)


@dataclass
class 集合字面量(表达式):
    """v0.0.8: 集合字面量。"""
    元素: list["表达式"] = field(default_factory=list)


@dataclass
class 变量(表达式):
    名称: str
    名称来源: str = "ORDINARY"  # ORDINARY | EXACT | CONTEXTUAL


@dataclass
class 二元运算(表达式):
    左: "表达式"
    算符: str  # + - * / // % ** == != > < >= <= in not_in and or is
    右: "表达式"
    表层算符: str = field(default="", kw_only=True)  # 原文："加" / "+"


@dataclass
class 一元运算(表达式):
    算符: str  # not -
    操作数: "表达式"
    表层算符: str = field(default="", kw_only=True)  # 原文："负" / "-"


@dataclass
class 调用(表达式):
    """函数调用。v0.0.8: 支持制定参数。"""
    函数: 表达式
    参数: list["表达式"] = field(default_factory=list)
    制定参数: list[tuple[str, "表达式"]] = field(default_factory=list)


# === 第二批表达式 ===

@dataclass
class 身份判断(表达式):
    """甲就是乙 / 甲不是乙本身。"""
    左: "表达式"
    右: "表达式"
    肯定: bool = True  # True=就是, False=不是...本身


@dataclass
class 等待表达式(表达式):
    """等待甲的所得"""
    调用: "调用"


@dataclass
class 当前错误(表达式):
    """错误（捕获到的异常对象）。"""
    pass


@dataclass
class 错误文本(表达式):
    """错误内容（str(异常)）。"""
    pass


@dataclass
class 成员访问(表达式):
    """表达式.成员名    对应 的 运算符"""
    对象: "表达式"
    成员: str


@dataclass
class 字符串下标(表达式):
    """表达式["键"]    对应 【键"""
    对象: "表达式"
    键: str


@dataclass
class 表达式下标(表达式):
    """表达式[索引]    对应 ［索引］"""
    对象: "表达式"
    索引: "表达式"


@dataclass
class 切片下标(表达式):
    """表达式[开始:结束]    对应 ［开始：结束］"""
    对象: "表达式"
    开始: "表达式 | None" = None
    结束: "表达式 | None" = None


@dataclass
class 映射字面量(表达式):
    """［【键】为【值】、…］ 映射字面量"""
    条目: list[tuple["表达式", "表达式"]] = field(default_factory=list)
