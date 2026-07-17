"""周道 v0.0.10.5: 规范格式化器 — 三模式。

遍历 Surface AST 输出规范周道源码。
支持三种运算符风格：
  preserve（默认）：保留用户原始写法
  verbal：统一输出汉语式（加、减、等于……）
  symbolic：统一输出符号式（+、-、=……）

幂等：格式化结果再次格式化不变。
"""

from __future__ import annotations
from .lexer import 扫描
from .parser import 解析器
from . import ast_nodes as AST


# 风格映射表（只含算符，不含空格——间距由 Formatter 统一负责）
_汉语算符 = {
    "+": "加", "-": "减", "*": "乘", "/": "除",
    "==": "等于", "!=": "不等于",
    ">": "大于", "<": "小于", ">=": "不少于", "<=": "不多于",
    "**": "**", "//": "//", "%": "%",  # 无双表层，verbal 仍输出符号
}

_符号算符 = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "==": "=", "!=": "!=",
    ">": ">", "<": "<", ">=": ">=", "<=": "<=",
    "**": "**", "//": "//", "%": "%",
}


def 格式化(源码: str, 行宽: int = 100, *, 风格: str = "preserve") -> str:
    """格式化周道源码。

    Args:
        源码: 原始周道源码
        行宽: 最大行宽（保留接口）
        风格: "preserve"（保留原写法）、"verbal"（汉语式）、"symbolic"（符号式）

    Returns:
        格式化后的源码
    """
    tokens = 扫描(源码)
    parser = 解析器(tokens)
    program = parser.解析()
    fmt = 周道格式化器(风格=风格)
    return fmt.格式化程序(program)


def _判断风格(节点) -> str:
    """根据表层算符判断原始风格。汉语为 verbal，符号为 symbolic。"""
    表层 = getattr(节点, '表层算符', None) or getattr(节点, '表层文本', None) or ""
    if 表层 and ord(表层[0]) >= 0x4e00:
        return "verbal"
    return "symbolic"


def 检查格式差异(源码: str, 行宽: int = 100, *, 风格: str = "preserve") -> str | None:
    """检查格式差异。"""
    格式化后 = 格式化(源码, 行宽, 风格=风格)
    if 格式化后 == 源码:
        return None
    return 格式化后


def 迁移弃用句式(源码: str) -> str:
    """迁移弃用句式到正式语法。"""
    import re
    # 设结果为等待甲的所得 → 等待甲完成，记作结果
    def _替换(m):
        var, call = m.group(1), m.group(2)
        if "为" not in call and "加" not in call and "减" not in call:
            return f"等待{call}完成，记作{var}。"
        return m.group(0)
    return re.sub(r'设(.+?)为等待(.+?)的所得[。，]?', _替换, 源码)


class 周道格式化器:
    """Surface AST → 规范周道源码。"""

    def __init__(self, 风格: str = "preserve"):
        self.输出: list[str] = []
        self.缩进层级: int = 0
        self.行首: bool = True
        self.风格 = 风格  # "preserve" | "verbal" | "symbolic"

    def _实际风格(self, 节点) -> str:
        """确定当前节点的输出风格。"""
        if self.风格 == "preserve":
            return _判断风格(节点)
        return self.风格

    def _选算符(self, 语义算符: str, 表层算符: str = "") -> str:
        """根据风格和表层信息选择输出算符。"""
        if self.风格 == "preserve" and 表层算符:
            return 表层算符
        if self.风格 in ("verbal", "preserve"):
            return _汉语算符.get(语义算符, 语义算符)
        return _符号算符.get(语义算符, 语义算符)

    def _渲染二元(self, 节点):
        """渲染二元运算，根据风格决定间距。"""
        算符文 = self._选算符(节点.算符, getattr(节点, '表层算符', ''))
        if 算符文 and ord(算符文[0]) >= 0x4e00:
            # 汉语式：不加空格
            self._化表达式(节点.左)
            self._写(算符文)
            self._化表达式(节点.右)
        else:
            # 符号式：两侧各一个半角空格
            self._化表达式(节点.左)
            self._写(f" {算符文} ")
            self._化表达式(节点.右)

    def _渲染一元(self, 节点):
        """渲染一元运算，根据风格决定负号写法。"""
        实际风格 = self._实际风格(节点)
        if 节点.算符 == "-":
            if 实际风格 == "verbal":
                self._写("负")
            else:
                self._写("-")  # 一元负号无空格
            self._化表达式(节点.操作数)
        elif 节点.算符 == "not":
            self._写("并非（")
            self._化表达式(节点.操作数)
            self._写("）")

    @property
    def 缩进(self) -> str:
        return "    " * self.缩进层级

    def _写(self, 文本: str = ""):
        if self.行首:
            self.输出.append(self.缩进)
            self.行首 = False
        self.输出.append(文本)

    def _写行(self, 文本: str = ""):
        if self.行首:
            self.输出.append(self.缩进)
        self.输出.append(文本 + "\n")
        self.行首 = True

    def _增加缩进(self):
        self.缩进层级 += 1

    def _减少缩进(self):
        self.缩进层级 = max(0, self.缩进层级 - 1)

    def 格式化程序(self, 程序: AST.程序) -> str:
        self.输出 = []
        self.缩进层级 = 0
        self.行首 = True
        for 句子 in 程序.句子列表:
            for 注释 in 句子.前导注释:
                self._写行(注释)
            for 语句 in 句子.语句列表:
                self._格式化语句(语句)
            if 句子.语句列表 or 句子.前导注释:
                self._写("。")
                if 句子.尾行注释:
                    self._写(f" {句子.尾行注释}")
                self._写行()
        return "".join(self.输出).strip() + "\n"

    def _格式化语句(self, 节点):
        t = type(节点).__name__

        if isinstance(节点, AST.绑定):
            self._写(f"设{节点.名称}为")
            self._化表达式(节点.值)
        elif isinstance(节点, AST.空值绑定):
            self._写(f"设{节点.名称}没有值")
        elif isinstance(节点, AST.命题绑定):
            self._写(f"设{节点.名称}{'成立' if 节点.值 else '不成立'}")
        elif isinstance(节点, AST.变更):
            self._写("使"); self._化表达式(节点.目标); self._写("变为"); self._化表达式(节点.值)
        elif isinstance(节点, AST.算术变更):
            self._写("使"); self._化表达式(节点.目标)
            映射 = {"+=": "加", "-=": "减", "*=": "乘", "/=": "除"}
            self._写(映射.get(节点.算符, 节点.算符)); self._化表达式(节点.值)
        elif isinstance(节点, AST.命题变更):
            self._写("使"); self._化表达式(节点.目标); self._写('成立' if 节点.值 else '不成立')
        elif isinstance(节点, AST.打印):
            self._写("显示"); self._化表达式(节点.值)
        elif isinstance(节点, AST.如果):
            self._格式化如果(节点)
        elif isinstance(节点, AST.当循环):
            self._写("当"); self._化表达式(节点.条件); self._写("时，一直")
            self._增加缩进()
            for s in 节点.体: self._格式化语句(s)
            self._减少缩进()
        elif isinstance(节点, AST.遍历):
            self._写("从"); self._化表达式(节点.集合); self._写(f"中，每取一项记作{节点.元素}，就")
            self._增加缩进()
            for s in 节点.体: self._格式化语句(s)
            self._减少缩进()
        elif isinstance(节点, AST.尝试):
            self._格式化尝试(节点)
        elif isinstance(节点, AST.以所得):
            self._写("以"); self._化表达式(节点.值); self._写("为所得")
        elif isinstance(节点, AST.函数定义):
            if 节点.单表达式:
                self._写(f"设{节点.名称}（")
                self._参数列表(节点.参数, 节点.参数默认值)
                self._写("）为")
                self._化表达式(节点.体[0].值 if 节点.体 else AST.空值())
            else:
                self._写(f"定义{节点.名称}（")
                self._参数列表(节点.参数, 节点.参数默认值)
                self._写("）如下：")
                self._增加缩进()
                for s in 节点.体: self._格式化语句(s)
                self._减少缩进()
        elif isinstance(节点, AST.类别声明):
            self._写(f"设置{节点.名称}类别，包括")
            self._字段列表(节点.字段列表)
        elif isinstance(节点, AST.报错):
            self._写(f"报错【{节点.消息}】")
            if 节点.错误类型:
                self._写(f"，错误类型是{节点.错误类型}")
        elif isinstance(节点, AST.依次给出):
            self._写("依次给出"); self._化表达式(节点.值)
        elif isinstance(节点, AST.等待语句):
            self._写("等待"); self._化表达式(节点.调用); self._写("完成")
            if 节点.记作名:
                self._写(f"，记作{节点.记作名}")
        elif isinstance(节点, AST.引入):
            self._写(f"引入Python模块《{节点.模块}》")
        elif isinstance(节点, AST.从中引入):
            self._写(f"从Python模块《{节点.模块}》中引入{'、'.join(节点.名称)}")
        elif isinstance(节点, AST.导入别名):
            self._写(f"引入Python模块《{节点.模块}》，下文简称{节点.别名}")
        elif isinstance(节点, AST.本地模块引入):
            s = f"引入周道源文件《{节点.模块名}》"
            if 节点.别名: s += f"，下文简称{节点.别名}"
            self._写(s)
        elif isinstance(节点, AST.从本地模块引入):
            self._写(f"从周道源文件《{节点.模块名}》中引入{'、'.join(节点.名称)}")
        elif isinstance(节点, AST.公开声明):
            self._写(f"规定模块接口：{'、'.join(节点.名称)}")
        elif isinstance(节点, AST.运行入口):
            self._写("运行如下：")
            self._增加缩进()
            for s in 节点.体: self._格式化语句(s)
            self._减少缩进()
        elif isinstance(节点, AST.类别方法定义):
            self._写(f"定义{节点.类别名}类别的{节点.名称}（")
            self._参数列表(节点.参数, 节点.参数默认值)
            self._写("）如下：")
            self._增加缩进()
            for s in 节点.体: self._格式化语句(s)
            self._减少缩进()
        elif isinstance(节点, AST.异步遍历):
            self._写("从"); self._化表达式(节点.集合); self._写(f"中，每等到一项记作{节点.元素}，就")
            self._增加缩进()
            for s in 节点.体: self._格式化语句(s)
            self._减少缩进()
        elif isinstance(节点, AST.原样报出):
            self._写("原样报出当前错误")
        elif isinstance(节点, AST.空操作):
            self._写("不作处理")
        elif isinstance(节点, AST.删除):
            self._写("删去"); self._化表达式(节点.目标)
        elif isinstance(节点, AST.全局声明):
            self._写(f"下文所用{'、'.join(节点.名称)}，均指全局的")
        elif isinstance(节点, AST.外层声明):
            self._写(f"下文所用{'、'.join(节点.名称)}，指本定义外层的")
        elif isinstance(节点, AST.断言):
            self._化表达式(节点.表达式)
            if 节点.消息: self._写(f"，否则报错【{节点.消息}】")
        elif isinstance(节点, AST.表达式语句):
            for s in 节点.动作列表:
                self._格式化语句(s) if isinstance(s, AST.语句) else self._化表达式(s)
        else:
            self._写(f"<!-- {t} -->")

    def _格式化如果(self, 节点):
        self._写("如果"); self._化表达式(节点.条件); self._写("，就")
        self._增加缩进()
        for s in 节点.则: self._格式化语句(s)
        self._减少缩进()
        for cond, body in 节点.否则如果:
            self._写("；不然，如果"); self._化表达式(cond); self._写("，就")
            self._增加缩进()
            for s in body: self._格式化语句(s)
            self._减少缩进()
        if 节点.否则:
            self._写("；不然就")
            self._增加缩进()
            for s in 节点.否则: self._格式化语句(s)
            self._减少缩进()

    def _格式化尝试(self, 节点):
        self._写("尝试")
        self._增加缩进()
        for s in 节点.体: self._格式化语句(s)
        self._减少缩进()
        for 类型, 体 in 节点.错误类型处理:
            self._写(f"；如果错误类型是{类型}，就")
            self._增加缩进()
            for s in 体: self._格式化语句(s)
            self._减少缩进()
        if 节点.异常体:
            self._写("；如果出错")
            if 节点.异常名: self._写(f"为{节点.异常名}")
            self._写("，就")
            self._增加缩进()
            for s in 节点.异常体: self._格式化语句(s)
            self._减少缩进()
        for s in 节点.最终体:
            self._写("；无论是否出错，最后")
            self._增加缩进()
            for s in 节点.最终体: self._格式化语句(s)
            self._减少缩进()

    def _化表达式(self, 节点):
        if 节点 is None:
            return
        if isinstance(节点, AST.整数): self._写(str(节点.值))
        elif isinstance(节点, AST.小数): self._写(str(节点.值))
        elif isinstance(节点, AST.文本): self._写(f"【{节点.值}】")
        elif isinstance(节点, AST.布尔): self._写("成立" if 节点.值 else "不成立")
        elif isinstance(节点, AST.空值): self._写("没有值")
        elif isinstance(节点, AST.变量): self._写(节点.名称)
        elif isinstance(节点, AST.二元运算):
            self._渲染二元(节点)
        elif isinstance(节点, AST.一元运算):
            self._渲染一元(节点)
        elif isinstance(节点, AST.调用):
            self._化表达式(节点.函数); self._写("（")
            for i, a in enumerate(节点.参数):
                if i > 0: self._写("、")
                self._化表达式(a)
            for 名称, 值 in 节点.制定参数:
                if 节点.参数 or True: self._写("、")
                self._写(f"{名称}为"); self._化表达式(值)
            self._写("）")
        elif isinstance(节点, AST.成员访问):
            self._化表达式(节点.对象); self._写(f"的{节点.成员}")
        elif isinstance(节点, AST.上下文成员访问):
            self._写(f"其{节点.首成员}")
            for 成员 in 节点.后续访问:
                self._写(f"的{成员}")
        elif isinstance(节点, AST.列表字面量):
            self._写("［")
            for i, e in enumerate(节点.元素):
                if i > 0: self._写("、")
                self._化表达式(e)
            self._写("］")
        elif isinstance(节点, AST.元组字面量):
            self._写("固定序列［")
            for i, e in enumerate(节点.元素):
                if i > 0: self._写("、")
                self._化表达式(e)
            self._写("］")
        elif isinstance(节点, AST.集合字面量):
            self._写("集合［")
            for i, e in enumerate(节点.元素):
                if i > 0: self._写("、")
                self._化表达式(e)
            self._写("］")
        elif isinstance(节点, AST.映射字面量):
            self._写("［")
            for i, (k, v) in enumerate(节点.条目):
                if i > 0: self._写("、")
                self._化表达式(k); self._写("为"); self._化表达式(v)
            self._写("］")
        elif isinstance(节点, AST.字符串下标):
            self._化表达式(节点.对象); self._写(f"【{节点.键}】")
        elif isinstance(节点, AST.表达式下标):
            self._化表达式(节点.对象); self._写("［"); self._化表达式(节点.索引); self._写("］")
        elif isinstance(节点, AST.切片下标):
            self._化表达式(节点.对象); self._写("［")
            if 节点.开始: self._化表达式(节点.开始)
            self._写("：")
            if 节点.结束: self._化表达式(节点.结束)
            self._写("］")
        elif isinstance(节点, AST.身份判断):
            self._化表达式(节点.左); self._写("就是" if 节点.肯定 else "不是"); self._化表达式(节点.右)
            if not 节点.肯定: self._写("本身")

    def _参数列表(self, 参数: list[str], 默认值: list):
        for i, name in enumerate(参数):
            if i > 0: self._写("、")
            self._写(name)
            if i < len(默认值) and 默认值[i] is not None:
                self._写("默认为"); self._化表达式(默认值[i])

    def _字段列表(self, 字段列表: list):
        for i, f in enumerate(字段列表):
            if i > 0: self._写("、")
            self._写(f.名称)
            if f.类型: self._写(f"，须为{f.类型}")
            if f.不得为负: self._写("且不得为负")
            if f.默认值: self._写("，默认为"); self._化表达式(f.默认值)
            if f.可空: self._写("，可以没有值")
