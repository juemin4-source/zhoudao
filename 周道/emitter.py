"""周道：Core IR / SemanticProgram → Python 代码生成器（Emitter）。

接受 SemanticProgram（推荐）或 Core IR（仅语法测试）作为输入，
输出可读、可独立执行的 Python 源码。

v0.0.6: 正式管线只接收 SemanticProgram。发射前检查程序没有语义错误。
"""

from .errors import 周道错误, 语义错误
from .semantic_program import SemanticProgram
from .core_ir import (
    程序IR, 语句IR, 表达式IR,
    赋值IR, 算术赋值IR, 打印IR,
    如果IR, 当循环IR, 遍历IR, 尝试IR,
    跳出IR, 继续IR, 以所得IR, 函数定义IR,
    引入IR, 从中引入IR, 导入别名IR,
    断言IR, 类别声明IR, 类别字段IR,
    删除IR, 空操作IR, 报错IR, 依次给出IR,
    等待语句IR, 全局声明IR, 外层声明IR,
    公开声明IR, 程序入口IR, 本地模块引入IR, 从本地模块引入IR, 异步遍历IR, 等待记作IR, 原样报出IR, 类别方法IR,
    最终收束IR, 分情形IR, 表达式语句IR,
    整数常量IR, 小数常量IR, 文本常量IR,
    布尔常量IR, 空值IR,
    列表字面量IR, 元组字面量IR, 集合字面量IR, 映射字面量IR,
    变量引用IR, 二元运算IR, 一元运算IR, 调用IR,
    身份判断IR, 等待表达式IR, 当前错误IR, 错误文本IR,
    成员访问IR, 字符串下标IR, 表达式下标IR,
    切片下标IR,
)

# 中文→英文模块名映射
_模块映射 = {
    "随机": "random",
    "数学": "math",
    "时间": "time",
    "系统": "sys",
    "操作系统": "os",
    "路径": "pathlib",
    "正则": "re",
    "JSON": "json",
    "CSV": "csv",
    "HTTP": "http",
    "网络请求": "requests",
    "收藏": "collections",
    "类型提示": "typing",
    "数据类": "dataclasses",
}

# 中文→英文成员名映射（嵌套结构：模块 → {周道名: Python名}）
_成员映射 = {
    "随机": {
        "随机整数": "randint",
        "随机选择": "choice",
        "随机范围": "randrange",
        "统一随机": "uniform",
        "随机种子": "seed",
        "随机取样": "sample",
        "随机洗牌": "shuffle",
    },
    "数学": {
        "平方根": "sqrt",
        "正弦": "sin",
        "余弦": "cos",
        "正切": "tan",
        "向上取整": "ceil",
        "向下取整": "floor",
    },
    "__内置__": {
        "绝对值": "abs",
        "四舍五入": "round",
        "最大值": "max",
        "最小值": "min",
        "求和": "sum",
        "长度": "len",
        "范围": "range",
        "枚举": "enumerate",
        "排序": "sorted",
        "反转": "reversed",
        "过滤": "filter",
        "映射": "map",
        "压缩": "zip",
        "打印": "print",
        "输入": "input",
        "打开": "open",
        "类型": "type",
        "字符串": "str",
        "整数": "int",
        "小数": "float",
        "布尔": "bool",
        "列表": "list",
        "字典": "dict",
        "集合": "set",
        "元组": "tuple",
    },
}


class 发射器:
    """Core IR → Python 发射器。"""

    def __init__(self, 缩进: str = "    "):
        self.缩进 = 缩进
        self.缩进层级 = 0
        self.行列表: list[str] = []
        self._行首 = True
        self.源位置映射: list[tuple[int, int]] = []
        self._当前异常名: str | None = None  # 异常处理中使用的错误变量名

    def 发射(self, 输入: 程序IR | SemanticProgram) -> str:
        """将程序发射为 Python 源码。

        正式管线接受 SemanticProgram。向后兼容接受 Core IR 程序IR。
        含有语义错误的程序会被拒绝。
        """
        if isinstance(输入, SemanticProgram):
            if 输入.有错误:
                raise 语义错误(
                    "不能发射包含语义错误的程序。"
                    f"发现 {len(输入.全部错误())} 个错误。"
                )
            ir = 输入.core_ir
        else:
            ir = 输入

        for 语句 in ir.语句列表:
            self._发射语句(语句)
        return "".join(self.行列表)

    # ==================== 行管理 ====================

    def _添加行(self, 文本: str = ""):
        """添加一行 Python 代码。"""
        if self._行首:
            self.行列表.append(self.缩进 * self.缩进层级)
        self.行列表.append(文本)
        self.行列表.append("\n")
        self._行首 = True

    def _追加(self, 文本: str):
        """在当前行追加文本。"""
        if self._行首:
            self.行列表.append(self.缩进 * self.缩进层级)
            self._行首 = False
        self.行列表.append(文本)

    def _行末(self):
        """结束当前行，后续内容在新行开始。"""
        self.行列表.append("\n")
        self._行首 = True

    def _缩进(self):
        self.缩进层级 += 1

    def _取消缩进(self):
        self.缩进层级 = max(0, self.缩进层级 - 1)

    def _发射语句列表(self, 语句列表: list[语句IR]):
        """发射多条 Core IR 语句。"""
        for 语句 in 语句列表:
            self._发射语句(语句)

    # ==================== 语句发射 ====================

    def _发射语句(self, 节点: 语句IR):
        """根据 Core IR 语句类型分发。"""
        if isinstance(节点, 赋值IR):
            self._发射赋值(节点)
        elif isinstance(节点, 算术赋值IR):
            self._添加行(f"{self._发射表达式(节点.目标)} {节点.算符} {self._发射表达式(节点.值)}")
        elif isinstance(节点, 打印IR):
            self._添加行(f"print({self._发射表达式(节点.值)})")
        elif isinstance(节点, 如果IR):
            self._发射如果(节点)
        elif isinstance(节点, 当循环IR):
            self._发射当循环(节点)
        elif isinstance(节点, 遍历IR):
            self._发射遍历(节点)
        elif isinstance(节点, 尝试IR):
            self._发射尝试(节点)
        elif isinstance(节点, 跳出IR):
            self._添加行("break")
        elif isinstance(节点, 继续IR):
            self._添加行("continue")
        elif isinstance(节点, 以所得IR):
            self._添加行(f"return {self._发射表达式(节点.值)}")
        elif isinstance(节点, 函数定义IR):
            self._发射函数(节点)
        elif isinstance(节点, 引入IR):
            模块 = _模块映射.get(节点.模块, 节点.模块)
            self._添加行(f"import {模块}")
        elif isinstance(节点, 从中引入IR):
            模块 = _模块映射.get(节点.模块, 节点.模块)
            模块成员 = _成员映射.get(节点.模块, {})
            导入列表 = []
            for n in 节点.名称:
                py_name = 模块成员.get(n, n)
                if py_name != n:
                    导入列表.append(f"{py_name} as {n}")
                else:
                    导入列表.append(n)
            self._添加行(f"from {模块} import {', '.join(导入列表)}")
        elif isinstance(节点, 导入别名IR):
            模块 = _模块映射.get(节点.模块, 节点.模块)
            self._添加行(f"import {模块} as {节点.别名}")
        elif isinstance(节点, 断言IR):
            expr_str = self._发射表达式(节点.表达式)
            if 节点.消息:
                self._添加行(f'assert {expr_str}, "{节点.消息}"')
            else:
                self._添加行(f"assert {expr_str}")
        elif isinstance(节点, 类别声明IR):
            self._发射类别(节点)
        elif isinstance(节点, 删除IR):
            self._添加行(f"del {self._发射表达式(节点.目标)}")
        elif isinstance(节点, 空操作IR):
            self._添加行("pass")
        elif isinstance(节点, 报错IR):
            self._添加行(f'raise RuntimeError("{节点.消息}")')
        elif isinstance(节点, 依次给出IR):
            self._添加行(f"yield {self._发射表达式(节点.值)}")
        elif isinstance(节点, 等待语句IR):
            self._添加行(f"await {self._发射表达式(节点.调用)}")
        elif isinstance(节点, 全局声明IR):
            if 节点.名称:
                self._添加行(f"global {', '.join(节点.名称)}")
        elif isinstance(节点, 外层声明IR):
            if 节点.名称:
                self._添加行(f"nonlocal {', '.join(节点.名称)}")
        elif isinstance(节点, 最终收束IR):
            self._发射语句列表(节点.体)
        elif isinstance(节点, 分情形IR):
            self._发射分情形(节点)
        elif isinstance(节点, 表达式语句IR):
            self._添加行(self._发射表达式(节点.表达式))
        elif isinstance(节点, (本地模块引入IR, 从本地模块引入IR, 公开声明IR, 程序入口IR)):
            pass
        else:
            raise 周道错误(f"未知 Core IR 语句类型：{type(节点).__name__}")

    def _发射赋值(self, 节点: 赋值IR):
        """发射赋值语句（绑定、变更、空值、命题的统一形式）。"""
        if 节点.值 is None:
            self._添加行(f"{self._发射表达式(节点.目标)} = None")
        else:
            self._添加行(f"{self._发射表达式(节点.目标)} = {self._发射表达式(节点.值)}")

    # ==================== 复合语句发射 ====================

    def _发射如果(self, 节点: 如果IR):
        self._追加(f"if {self._发射表达式(节点.条件)}:")
        self._行末()
        self._缩进()
        self._发射语句列表(节点.则)
        self._取消缩进()

        for 条件, 体 in 节点.否则如果:
            self._追加(f"elif {self._发射表达式(条件)}:")
            self._行末()
            self._缩进()
            self._发射语句列表(体)
            self._取消缩进()

        if 节点.否则:
            self._追加("else:")
            self._行末()
            self._缩进()
            self._发射语句列表(节点.否则)
            self._取消缩进()

    def _发射当循环(self, 节点: 当循环IR):
        self._追加(f"while {self._发射表达式(节点.条件)}:")
        self._行末()
        self._缩进()
        self._发射语句列表(节点.体)
        self._取消缩进()

    def _发射遍历(self, 节点: 遍历IR):
        self._追加(f"for {节点.元素} in {self._发射表达式(节点.集合)}:")
        self._行末()
        self._缩进()
        self._发射语句列表(节点.体)
        self._取消缩进()

    def _发射尝试(self, 节点: 尝试IR):
        self._追加("try:")
        self._行末()
        self._缩进()
        self._发射语句列表(节点.体)
        self._取消缩进()

        if 节点.异常体:
            旧异常 = self._当前异常名
            self._当前异常名 = "_err"
            异常子句 = f" as {self._当前异常名}" if 节点.异常名 else " as _err"
            self._追加(f"except Exception{异常子句}:")
            self._行末()
            self._缩进()
            self._发射语句列表(节点.异常体)
            self._取消缩进()
            self._当前异常名 = 旧异常

        if 节点.最终体:
            self._追加("finally:")
            self._行末()
            self._缩进()
            self._发射语句列表(节点.最终体)
            self._取消缩进()

    def _发射函数(self, 节点: 函数定义IR):
        参数 = ", ".join(节点.参数)
        if 节点.是异步 and 节点.是生成器:
            前缀 = "async def"
        elif 节点.是异步:
            前缀 = "async def"
        else:
            前缀 = "def"
        self._追加(f"{前缀} {节点.名称}({参数}):")
        self._行末()
        self._缩进()
        self._发射语句列表(节点.体)
        self._取消缩进()

    def _发射类别(self, 节点: 类别声明IR):
        """类别声明 → @dataclass class。"""
        self._添加行(f"from {_模块映射.get('数据类', 'dataclasses')} import dataclass")
        self._添加行("from typing import Any")

        字段定义: list[str] = []
        验证代码: list[str] = []

        for f in 节点.字段列表:
            类型提示 = f.类型 if f.类型 else "Any"
            if f.可空:
                字段定义.append(f"{f.名称}: {类型提示} = None")
            elif f.默认值:
                默认_str = self._发射表达式(f.默认值)
                字段定义.append(f"{f.名称}: {类型提示} = {默认_str}")
            else:
                字段定义.append(f"{f.名称}: {类型提示}")

            if f.类型:
                验证代码.append(f"        if not isinstance(self.{f.名称}, {f.类型}): raise TypeError(f'「{f.名称}」必须为 {f.类型}')")
            if f.不得为负:
                验证代码.append(f"        if self.{f.名称} < 0: raise ValueError(f'「{f.名称}」不得为负')")

        self._添加行("")
        self._添加行("@dataclass(kw_only=True)")
        self._追加(f"class {节点.名称}:")
        self._行末()
        self._缩进()
        for fd in 字段定义:
            self._添加行(fd)
        if 验证代码:
            self.行列表.append("\n")
            self._添加行("def __post_init__(self):")
            self._缩进()
            for vc in 验证代码:
                self._添加行(vc)
            self._取消缩进()
        self._取消缩进()
        self._添加行("")

    def _发射分情形(self, 节点: 分情形IR):
        对象_str = self._发射表达式(节点.对象)
        self._追加(f"match {对象_str}:")
        self._行末()
        self._缩进()
        for 值, 动作列表 in 节点.分支列表:
            if 值 is None:
                self._追加("case _:")
            else:
                值_str = self._发射表达式(值)
                self._追加(f"case {值_str}:")
            self._行末()
            self._缩进()
            self._发射语句列表(动作列表)
            self._取消缩进()
        self._取消缩进()

    # ==================== 表达式发射 ====================

    def _发射表达式(self, 节点: 表达式IR) -> str:
        """将 Core IR 表达式转换为 Python 字符串。"""
        if isinstance(节点, 整数常量IR):
            return str(节点.值)
        elif isinstance(节点, 小数常量IR):
            return str(节点.值)
        elif isinstance(节点, 文本常量IR):
            值 = 节点.值.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{值}"'
        elif isinstance(节点, 布尔常量IR):
            return "True" if 节点.值 else "False"
        elif isinstance(节点, 空值IR):
            return "None"
        elif isinstance(节点, 列表字面量IR):
            元素 = ", ".join(self._发射表达式(e) for e in 节点.元素)
            return f"[{元素}]"
        elif isinstance(节点, 元组字面量IR):
            elts = chr(12289).join(self._发射表达式(e) for e in 节点.元素)
            return chr(22266) + chr(23450) + chr(24207) + chr(21015) + chr(65339) + elts + chr(65341)
        elif isinstance(节点, 集合字面量IR):
            elts = chr(12289).join(self._发射表达式(e) for e in 节点.元素)
            return chr(38598) + chr(21512) + chr(65339) + elts + chr(65341)
        elif isinstance(节点, 映射字面量IR):
            items = ", ".join(
                f"{self._发射表达式(k)}: {self._发射表达式(v)}"
                for k, v in 节点.条目
            )
            return "{" + items + "}"
        elif isinstance(节点, 变量引用IR):
            return 节点.名称
        elif isinstance(节点, 二元运算IR):
            return self._发射二元运算(节点)
        elif isinstance(节点, 一元运算IR):
            return self._发射一元运算(节点)
        elif isinstance(节点, 调用IR):
            return self._发射调用(节点)
        elif isinstance(节点, 身份判断IR):
            op = "is" if 节点.肯定 else "is not"
            return f"{self._发射表达式(节点.左)} {op} {self._发射表达式(节点.右)}"
        elif isinstance(节点, 等待表达式IR):
            return f"await {self._发射表达式(节点.调用)}"
        elif isinstance(节点, 当前错误IR):
            return self._当前异常名 or "当前错误"
        elif isinstance(节点, 错误文本IR):
            return f"str({self._当前异常名 or '当前错误'})"
        elif isinstance(节点, 成员访问IR):
            return f"{self._发射表达式(节点.对象)}.{节点.成员}"
        elif isinstance(节点, 字符串下标IR):
            return f'{self._发射表达式(节点.对象)}["{节点.键}"]'
        elif isinstance(节点, 表达式下标IR):
            return f"{self._发射表达式(节点.对象)}[{self._发射表达式(节点.索引)}]"
        elif isinstance(节点, 切片下标IR):
            开始 = self._发射表达式(节点.开始) if 节点.开始 else ""
            结束 = self._发射表达式(节点.结束) if 节点.结束 else ""
            return f"{self._发射表达式(节点.对象)}[{开始}:{结束}]"
        else:
            raise 周道错误(f"未知 Core IR 表达式类型：{type(节点).__name__}")

    def _发射二元运算(self, 节点: 二元运算IR) -> str:
        """发射二元运算表达式。"""
        left = self._发射表达式(节点.左)
        right = self._发射表达式(节点.右)

        op_map = {
            "not_in": "not in",
            "is": "is",
            "in": "in",
            "and": "and",
            "or": "or",
        }
        op = op_map.get(节点.算符, 节点.算符)

        return f"{left} {op} {right}"

    def _发射一元运算(self, 节点: 一元运算IR) -> str:
        """发射一元运算表达式。"""
        operand = self._发射表达式(节点.操作数)
        if 节点.算符 == "not":
            return f"not {operand}"
        elif 节点.算符 == "-":
            return f"-{operand}"
        return f"{节点.算符}{operand}"

    def _发射调用(self, 节点: 调用IR) -> str:
        """发射函数调用。"""
        函数 = self._发射表达式(节点.函数)
        参数 = ", ".join(self._发射表达式(p) for p in 节点.参数)
        return f"{函数}({参数})"
