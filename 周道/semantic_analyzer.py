"""周道 v0.0.6: Semantic Analyzer — Core IR 语义分析器。

语义分析管线：Core IR → 作用域构建 → 名称解析 → 上下文检查 → SemanticProgram

职责：
- 建立作用域层次结构（借 NameLattice）
- 注册定义（变量、函数、类别、参数）
- 解析引用名称（先查用户作用域，再查 PreludeScope）
- 检查上下文约束（break/continue 在循环内、return 在函数内等）
- 拒绝未知名称进入 Emitter

约束：
- Core IR 保持不可变，不向其添加语义信息
- 语义信息存放于 SemanticProgram 中
- 每个诊断必须附带 SourceSpan
- SemanticProgram 不存放 Python 源码片段
"""

from __future__ import annotations

from .core_ir import (
    程序IR, 语句IR, 表达式IR,
    赋值IR, 算术赋值IR, 打印IR,
    如果IR, 当循环IR, 遍历IR, 尝试IR,
    跳出IR, 继续IR, 以所得IR, 函数定义IR,
    引入IR, 从中引入IR, 导入别名IR,
    断言IR, 类别声明IR,
    删除IR, 空操作IR, 报错IR, 依次给出IR,
    等待语句IR, 全局声明IR, 外层声明IR, 程序入口IR, 公开声明IR, 本地模块引入IR, 从本地模块引入IR, 异步遍历IR, 等待记作IR, 原样报出IR, 类别方法IR,
    最终收束IR, 分情形IR, 表达式语句IR,
    整数常量IR, 小数常量IR, 文本常量IR,
    布尔常量IR, 空值IR,
    列表字面量IR, 映射字面量IR,
    变量引用IR, 二元运算IR, 一元运算IR, 调用IR,
    身份判断IR, 等待表达式IR, 当前错误IR, 错误文本IR,
    成员访问IR, 字符串下标IR, 表达式下标IR,
    切片下标IR,
)
from .errors import 源码位置, 语义错误
from .nametable import 绑定信息
from .name_lattice import NameLattice
from .semantic_program import (
    类别方法绑定,
    SemanticProgram, 语义诊断, 作用域快照,
)
from .prelude_scope import 是否已知名称


class 语义分析器:
    """Core IR 语义分析器。

    遍历 Core IR 程序，构建作用域、解析名称、检查上下文约束，
    输出 SemanticProgram。

    Args:
        ir: Core IR 程序
        位置映射: id(IR_node) → 源码位置（由降低器提供）
    """

    def __init__(self, ir: 程序IR, 位置映射: dict[int, 源码位置] | None = None):
        self.ir = ir
        self.位置映射 = 位置映射 or {}
        # 作用域与名称管理
        self.格子 = NameLattice()
        # 上下文追踪
        self.循环深度: int = 0
        self.函数深度: int = 0  # 0 = 模块层, >0 = 在函数内
        self.在定义内: bool = False
        self.在异常内: bool = False
        self.在异步函数内: bool = False
        self.在类别方法内: bool = False
        self.当前类别名: str | None = None
        # 输出
        self.诊断列表: list[语义诊断] = []
        self.作用域列表: list[作用域快照] = []
        self.类别方法表: dict = {}
        self.入口是异步: bool = False

    # ── 入口 ────────────────────────────────────────────────

    def 分析(self) -> SemanticProgram:
        """执行语义分析，返回 SemanticProgram。"""
        # 全局作用域起点
        self._记录作用域("global")
        for stmt in self.ir.语句列表:
            self._分析语句(stmt)

        return SemanticProgram(
            core_ir=self.ir,
            诊断列表=self.诊断列表,
            作用域列表=self.作用域列表,
            类别方法表=self.类别方法表,
            入口是异步=self.入口是异步,
        )

    # ── 作用域管理 ──────────────────────────────────────────

    def _进入函数作用域(self, 名称: str, 参数: list[str]) -> None:
        """进入一个新函数作用域：注册函数名 + 参数。"""
        self.格子.进入作用域("function")
        self.函数深度 += 1
        self.在定义内 = True
        for param in 参数:
            self._注册绑定(param, "参数")
        self._记录作用域("function")

    def _离开函数作用域(self) -> None:
        """离开当前函数作用域。"""
        self.格子.离开作用域()
        self.函数深度 -= 1
        self.在定义内 = self.函数深度 > 0

    def _进入控制作用域(self) -> None:
        """进入控制结构作用域（如果/当/遍历/尝试体）。"""
        self.格子.进入作用域("control")

    def _离开控制作用域(self) -> None:
        """离开控制结构作用域。"""
        self.格子.离开作用域()

    def _记录作用域(self, 类型: str) -> None:
        """记录当前作用域快照。"""
        names = list(self.格子.当前表.所有名称) if hasattr(self.格子.当前表, '所有名称') else []
        self.作用域列表.append(作用域快照(类型=类型, 名称列表=names))

    # ── 名称注册与解析 ──────────────────────────────────────

    def _注册绑定(self, 名称: str, 类型: str, node=None) -> None:
        """在当前作用域注册一个名称绑定。"""
        if self.格子.检查重复(名称):
            位置 = self._取位置(node) if node else None
            self.诊断列表.append(语义诊断(
                f"重复定义：「{名称}」已在当前{self.格子.当前表.作用域类型}作用域中定义",
                位置=位置,
            ))
        else:
            位置 = self._取位置(node) if node else None
            self.格子.在当前域注册(名称, 绑定信息(
                名称=名称, 类型=类型, 位置=位置,
            ))

    def _解析名称(self, 名称: str, node) -> bool:
        """解析名称：先查用户作用域，再查 PreludeScope。

        Returns:
            True 表示名称已解析（用户定义或 PreludeScope）
            False 表示名称未知
        """
        try:
            self.格子.解析(名称)
            return True
        except 语义错误:
            if 是否已知名称(名称):
                return True
            位置 = self._取位置(node) if node else None
            # 收集名称来源信息（从 IR 节点的名称来源属性）
            名称来源 = getattr(node, "名称来源", "ORDINARY") if node else "ORDINARY"
            self.诊断列表.append(语义诊断(
                f"未定义的名称：「{名称}」",
                位置=位置,
            ))
            return False

    # ── 语句分析 ────────────────────────────────────────────

    def _分析语句(self, stmt: 语句IR) -> None:
        """根据语句类型分派分析。"""
        if isinstance(stmt, 赋值IR):
            self._分析赋值(stmt)
        elif isinstance(stmt, 算术赋值IR):
            self._分析算术赋值(stmt)
        elif isinstance(stmt, 打印IR):
            self._分析表达式(stmt.值)
        elif isinstance(stmt, 如果IR):
            self._分析如果(stmt)
        elif isinstance(stmt, 当循环IR):
            self._分析当循环(stmt)
        elif isinstance(stmt, 遍历IR):
            self._分析遍历(stmt)
        elif isinstance(stmt, 尝试IR):
            self._分析尝试(stmt)
        elif isinstance(stmt, 跳出IR):
            self._检查循环上下文("跳出循环", stmt)
        elif isinstance(stmt, 继续IR):
            self._检查循环上下文("继续下一轮", stmt)
        elif isinstance(stmt, 以所得IR):
            self._检查函数上下文("以…为所得", stmt)
            self._分析表达式(stmt.值)
        elif isinstance(stmt, 函数定义IR):
            self._分析函数定义(stmt)
        elif isinstance(stmt, 类别方法IR):
            self._分析类别方法(stmt)
        elif isinstance(stmt, 引入IR):
            # 不注册模块名为普通变量
            pass
        elif isinstance(stmt, 从中引入IR):
            for name in stmt.名称:
                self._注册绑定(name, "变量", stmt)
        elif isinstance(stmt, 导入别名IR):
            self._注册绑定(stmt.别名, "模块")
        elif isinstance(stmt, 断言IR):
            self._分析表达式(stmt.表达式)
        elif isinstance(stmt, 类别声明IR):
            self._注册绑定(stmt.名称, "类别", stmt)
            # 类别字段不进入普通名称解析
        elif isinstance(stmt, 删除IR):
            self._分析表达式(stmt.目标)
        elif isinstance(stmt, 空操作IR):
            pass
        elif isinstance(stmt, 程序入口IR):
            for s in stmt.体:
                self._分析语句(s)
        elif isinstance(stmt, 公开声明IR):
            # 接口名称已在函数/变量定义中注册，此处只验证
            pass
        elif isinstance(stmt, 本地模块引入IR):
            pass
        elif isinstance(stmt, 从本地模块引入IR):
            for name in stmt.名称:
                self._注册绑定(name, "变量", stmt)
        elif isinstance(stmt, 报错IR):
            if stmt.错误类型 and stmt.错误类型 not in ["运行出错","值出错","类型出错","键出错","索引出错","文件未找到出错"]:
                self.诊断列表.append(语义诊断(f"未知错误类型：{stmt.错误类型}"))
        elif isinstance(stmt, 依次给出IR):
            self._检查函数上下文("依次给出", stmt)
            self._分析表达式(stmt.值)
        elif isinstance(stmt, 等待语句IR):
            self._检查函数上下文("等待", stmt)
            self._分析表达式(stmt.调用)
        elif isinstance(stmt, 等待记作IR):
            self._检查函数上下文("等待", stmt)
            self._分析表达式(stmt.调用)
            self._注册绑定(stmt.记作名, "变量", stmt)
        elif isinstance(stmt, 异步遍历IR):
            self._检查函数上下文("每等到一项记作", stmt)
            self._分析表达式(stmt.集合)
            self._注册绑定(stmt.元素, "变量", stmt)
            for s in stmt.体:
                self._分析语句(s)
        elif isinstance(stmt, 原样报出IR):
            if not self.在异常内:
                self.诊断列表.append(语义诊断("原样报出只能在错误处理中使用"))
        elif isinstance(stmt, 全局声明IR):
            for name in stmt.名称:
                self.格子.注册跨越声明(name, "global")
        elif isinstance(stmt, 外层声明IR):
            self._检查函数上下文("下文所用…指本定义外层的", stmt)
            for name in stmt.名称:
                self.格子.注册跨越声明(name, "nonlocal")
        elif isinstance(stmt, 最终收束IR):
            for s in stmt.体:
                self._分析语句(s)
        elif isinstance(stmt, 分情形IR):
            self._分析表达式(stmt.对象)
            for val, body in stmt.分支列表:
                if val is not None:
                    self._分析表达式(val)
                self._进入控制作用域()
                for s in body:
                    self._分析语句(s)
                self._离开控制作用域()
        elif isinstance(stmt, 表达式语句IR):
            self._分析表达式(stmt.表达式)
        else:
            # 未知语句类型 — 安全地忽略（可能是未来扩展）
            pass

    # ── 赋值分析 ────────────────────────────────────────────

    def _分析赋值(self, stmt: 赋值IR) -> None:
        """分析赋值语句：目标为变量时注册绑定，值中的名称需要解析。

        规则：
        - 同域已存在的名称视为重新赋值，不重复注册
        - 同域不存在的名称注册为新绑定
        """
        # 分析目标
        if isinstance(stmt.目标, 变量引用IR):
            name = stmt.目标.名称
            # 是新绑定 → 注册新变量（设），否则是修改（使）
            if stmt.是新绑定:
                self._注册绑定(name, "变量", stmt.目标)
            else:
                self._解析名称(name, stmt.目标)
        elif isinstance(stmt.目标, 成员访问IR):
            self._分析表达式(stmt.目标.对象)
        elif isinstance(stmt.目标, (字符串下标IR, 表达式下标IR, 切片下标IR)):
            self._分析表达式(stmt.目标.对象)
            if isinstance(stmt.目标, 表达式下标IR):
                self._分析表达式(stmt.目标.索引)
        # 分析值
        if stmt.值 is not None:
            self._分析表达式(stmt.值)

    def _分析算术赋值(self, stmt: 算术赋值IR) -> None:
        """分析算术赋值：+= -= *= 等。"""
        # 目标解析（算术赋值的目标必须先定义）
        if isinstance(stmt.目标, 变量引用IR):
            self._解析名称(stmt.目标.名称, stmt.目标)
        elif isinstance(stmt.目标, 成员访问IR):
            self._分析表达式(stmt.目标.对象)
        self._分析表达式(stmt.值)

    # ── 复合语句分析 ────────────────────────────────────────

    def _分析如果(self, stmt: 如果IR) -> None:
        """分析条件分支。"""
        self._分析表达式(stmt.条件)
        self._进入控制作用域()
        for s in stmt.则:
            self._分析语句(s)
        self._离开控制作用域()
        for cond, body in stmt.否则如果:
            self._分析表达式(cond)
            self._进入控制作用域()
            for s in body:
                self._分析语句(s)
            self._离开控制作用域()
        self._进入控制作用域()
        for s in stmt.否则:
            self._分析语句(s)
        self._离开控制作用域()

    def _分析当循环(self, stmt: 当循环IR) -> None:
        """分析当循环（while）。"""
        self._分析表达式(stmt.条件)
        self.循环深度 += 1
        self._进入控制作用域()
        for s in stmt.体:
            self._分析语句(s)
        self._离开控制作用域()
        self.循环深度 -= 1

    def _分析遍历(self, stmt: 遍历IR) -> None:
        """分析遍历循环（for）。"""
        self._分析表达式(stmt.集合)
        self.循环深度 += 1
        self._进入控制作用域()
        # 元素名在当前控制作用域中注册
        self._注册绑定(stmt.元素, "变量")
        for s in stmt.体:
            self._分析语句(s)
        self._离开控制作用域()
        self.循环深度 -= 1

    def _分析尝试(self, stmt: 尝试IR) -> None:
        """分析尝试/异常处理。"""
        self._进入控制作用域()
        for s in stmt.体:
            self._分析语句(s)
        self._离开控制作用域()
        if stmt.异常体:
            旧 = self.在异常内
            self.在异常内 = True
            self._进入控制作用域()
            if stmt.异常名:
                self._注册绑定(stmt.异常名, "变量")
            for s in stmt.异常体:
                self._分析语句(s)
            self._离开控制作用域()
            self.在异常内 = 旧
        for s in stmt.最终体:
            self._分析语句(s)

    def _分析类别方法(self, stmt) -> None:
        类别名 = stmt.类别名
        try:
            self.格子.解析(类别名)
        except Exception:
            self.诊断列表.append(语义诊断(f"未定义的类别：{类别名}"))
            return
        if 类别名 in getattr(self, "类别方法表", {}) and stmt.名称 in self.类别方法表.get(类别名, {}):
            self.诊断列表.append(语义诊断(f"重复方法：{stmt.名称}"))
            return
        if 类别名 not in getattr(self, "类别方法表", {}):
            self.类别方法表[类别名] = {}
        self.类别方法表[类别名][stmt.名称] = 类别方法绑定(类别名=类别名, 方法名=stmt.名称, 参数=tuple(stmt.参数), 是异步=stmt.是异步, 是生成器=stmt.是生成器)
        旧定义, 旧函数, 旧异常, 旧异步 = self.在定义内, self.函数深度, self.在异常内, self.在异步函数内
        旧类别方法, 旧类别 = self.在类别方法内, self.当前类别名
        self._进入函数作用域(stmt.名称, stmt.参数)
        self.在异步函数内 = stmt.是异步
        self.在类别方法内 = True
        self.当前类别名 = 类别名
        self._注册绑定("自己", "变量", stmt)
        for s in stmt.体:
            self._分析语句(s)
        self._离开函数作用域()
        self.在定义内, self.函数深度, self.在异常内 = 旧定义, 旧函数, 旧异常
        self.在异步函数内 = 旧异步
        self.在类别方法内 = 旧类别方法
        self.当前类别名 = 旧类别

    def _分析函数定义(self, stmt: 函数定义IR) -> None:
        """分析函数定义。"""
        # 在当前作用域注册函数名
        self._注册绑定(stmt.名称, "函数", stmt)
        # 进入函数作用域
        旧定义 = self.在定义内
        旧函数 = self.函数深度
        旧异常 = self.在异常内
        旧异步 = self.在异步函数内
        self._进入函数作用域(stmt.名称, stmt.参数)
        self.在异步函数内 = stmt.是异步
        # 分析函数体
        for s in stmt.体:
            self._分析语句(s)
        # 离开函数作用域
        self._离开函数作用域()
        self.在定义内 = 旧定义
        self.函数深度 = 旧函数
        self.在异常内 = 旧异常
        self.在异步函数内 = 旧异步

    # ── 表达式分析 ──────────────────────────────────────────

    def _分析表达式(self, expr: 表达式IR) -> None:
        """分析表达式中的名称引用。"""
        if isinstance(expr, 变量引用IR):
            self._解析名称(expr.名称, expr)
        elif isinstance(expr, 二元运算IR):
            self._分析表达式(expr.左)
            self._分析表达式(expr.右)
        elif isinstance(expr, 一元运算IR):
            self._分析表达式(expr.操作数)
        elif isinstance(expr, 调用IR):
            self._分析表达式(expr.函数)
            for arg in expr.参数:
                self._分析表达式(arg)
        elif isinstance(expr, 身份判断IR):
            self._分析表达式(expr.左)
            self._分析表达式(expr.右)
        elif isinstance(expr, 成员访问IR):
            self._分析表达式(expr.对象)
        elif isinstance(expr, 字符串下标IR):
            self._分析表达式(expr.对象)
            # 键是字符串字面量，不是名称
        elif isinstance(expr, 表达式下标IR):
            self._分析表达式(expr.对象)
            self._分析表达式(expr.索引)
        elif isinstance(expr, 切片下标IR):
            self._分析表达式(expr.对象)
            if expr.开始:
                self._分析表达式(expr.开始)
            if expr.结束:
                self._分析表达式(expr.结束)
        elif isinstance(expr, 等待表达式IR):
            self._检查函数上下文("等待…的所得", expr)
            self._分析表达式(expr.调用)
        elif isinstance(expr, 当前错误IR):
            if not self.在异常内:
                位置 = self._取位置(expr) if expr else None
                self.诊断列表.append(语义诊断(
                    "「错误」只能在「如果出错」范围内使用",
                    位置=位置,
                ))
        elif isinstance(expr, 错误文本IR):
            if not self.在异常内:
                位置 = self._取位置(expr) if expr else None
                self.诊断列表.append(语义诊断(
                    "「错误内容」只能在「如果出错」范围内使用",
                    位置=位置,
                ))
        elif isinstance(expr, 列表字面量IR):
            for e in expr.元素:
                self._分析表达式(e)
        elif isinstance(expr, 映射字面量IR):
            for k, v in expr.条目:
                self._分析表达式(k)
                self._分析表达式(v)
        elif isinstance(expr, (整数常量IR, 小数常量IR, 文本常量IR,
                                布尔常量IR, 空值IR)):
            pass  # 字面量不包含名称
        else:
            # 未知表达式类型
            pass

    # ── 上下文检查 ──────────────────────────────────────────

    def _检查循环上下文(self, 操作: str, node) -> None:
        """检查 break/continue 是否在循环内。"""
        if self.循环深度 <= 0:
            位置 = self._取位置(node) if node else None
            self.诊断列表.append(语义诊断(
                f"「{操作}」只能在循环内使用",
                位置=位置,
            ))

    def _检查函数上下文(self, 操作: str, node) -> None:
        """检查 return/yield/await 是否在函数内。"""
        if not self.在定义内:
            位置 = self._取位置(node) if node else None
            self.诊断列表.append(语义诊断(
                f"「{操作}」只能在定义内使用",
                位置=位置,
            ))

    def _取位置(self, node) -> 源码位置 | None:
        """从位置映射获取 IR 节点的源码位置。"""
        if node is None:
            return None
        return self.位置映射.get(id(node))


def 分析(ir: 程序IR, 位置映射: dict[int, 源码位置] | None = None) -> SemanticProgram:
    """便捷函数：Core IR → 语义分析 → SemanticProgram。

    Args:
        ir: Core IR 程序
        位置映射: id(IR_node) → 源码位置（来自 lowering）

    Returns:
        SemanticProgram 包含分析结果和诊断
    """
    return 语义分析器(ir, 位置映射).分析()
