"""周道：Surface AST → Core IR 降低（Lowering）。

将解析器产生的表层 AST（含句法差异）降低为 Core IR（纯语义表示）。

核心规则：
- 同一语义的不同表层句式降解为同一种 Core IR 节点
- 不重新分词或重新判断精确名称内容
- Lowering 只消费 Parser 已经确定的 AST
- v0.0.6: 同时记录 AST → Core IR 的位置映射，供语义分析使用
"""

from dataclasses import dataclass, field
from .errors import 源码位置
from .ast_nodes import (
    程序, 句子,
    绑定, 空值绑定, 命题绑定,
    变更, 算术变更, 命题变更,
    打印, 如果, 当循环, 遍历, 尝试,
    跳出, 继续, 以所得, 函数定义,
    引入, 从中引入, 导入别名,
    断言, 类别声明, 类别字段,
    删除, 空操作, 报错, 依次给出,
    等待语句, 全局声明, 外层声明,
    最终收束, 分情形,
    公开声明, 运行入口, 本地模块引入, 从本地模块引入, 类别方法定义, 异步遍历, 原样报出,    表达式语句,
    整数, 小数, 文本, 布尔, 空值,
    列表字面量, 变量, 二元运算, 一元运算, 调用,
    身份判断, 等待表达式, 当前错误, 错误文本,
    成员访问, 字符串下标, 表达式下标,
    切片下标, 映射字面量,
    上下文成员访问,
    元组字面量, 集合字面量,
    表达式, 语句,
)
from .core_ir import (
    程序IR, 语句IR, 表达式IR,
    赋值IR, 算术赋值IR, 打印IR,
    如果IR, 当循环IR, 遍历IR, 尝试IR,
    跳出IR, 继续IR, 以所得IR, 函数定义IR,
    引入IR, 从中引入IR, 导入别名IR,
    断言IR, 类别声明IR, 类别字段IR,
    删除IR, 空操作IR, 报错IR, 依次给出IR,
    等待语句IR, 全局声明IR, 外层声明IR,
    最终收束IR, 分情形IR, 表达式语句IR, 公开声明IR, 程序入口IR, 本地模块引入IR, 从本地模块引入IR, 异步遍历IR, 等待记作IR, 原样报出IR, 类别方法IR,
    整数常量IR, 小数常量IR, 文本常量IR,
    布尔常量IR, 空值IR,
    列表字面量IR, 元组字面量IR, 集合字面量IR, 映射字面量IR,
    变量引用IR, 二元运算IR, 一元运算IR, 调用IR,
    身份判断IR, 等待表达式IR, 当前错误IR, 错误文本IR,
    成员访问IR, 字符串下标IR, 表达式下标IR,
    切片下标IR,
)


# ── 降低结果 ──────────────────────────────────────────────────

@dataclass
class 降低结果:
    """降低结果：Core IR 程序 + AST→IR 位置映射。

    位置映射用于语义分析阶段的错误定位。
    映射键为 id(IR_node)，值为对应 AST 节点的源码位置。
    """
    ir: "程序IR"
    位置映射: dict[int, 源码位置] = field(default_factory=dict)

    @property
    def 程序(self) -> "程序IR":
        return self.ir


class 降低器:
    """Surface AST → Core IR 降低器。"""

    def __init__(self, ast: 程序):
        self.ast = ast
        self.位置映射: dict[int, 源码位置] = {}

    def _记录位置(self, ir_node, ast_node) -> None:
        """从 AST 节点记录源码位置到 IR 节点。

        仅当 AST 节点携带位置信息时记录。
        """
        位置 = getattr(ast_node, "位置", None)
        if 位置 is not None:
            self.位置映射[id(ir_node)] = 位置

    def 降低(self) -> 降低结果:
        """将 Surface AST 程序降低为 Core IR 程序。

        Returns:
            降低结果 包含 Core IR 程序和 AST→IR 位置映射。
        """
        ir语句列表: list[语句IR] = []
        for 句子节点 in self.ast.句子列表:
            for 语句节点 in 句子节点.语句列表:
                ir_stmt = self._降低语句(语句节点)
                if ir_stmt is not None:
                    ir语句列表.append(ir_stmt)
        ir程序 = 程序IR(语句列表=ir语句列表)
        self._记录位置(ir程序, self.ast)
        return 降低结果(ir=ir程序, 位置映射=self.位置映射)

    # ==================== 语句降低 ====================

    def _降低语句(self, 节点) -> 语句IR | None:
        """将 Surface AST 语句降低为 Core IR 语句。"""
        if isinstance(节点, 绑定):
            ir = 赋值IR(
                目标=变量引用IR(名称=节点.名称),
                值=self._降低表达式(节点.值),
                是新绑定=True,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 空值绑定):
            ir = 赋值IR(
                目标=变量引用IR(名称=节点.名称),
                值=空值IR(),
                是新绑定=True,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 命题绑定):
            ir = 赋值IR(
                目标=变量引用IR(名称=节点.名称),
                值=布尔常量IR(值=节点.值),
                是新绑定=True,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 变更):
            ir = 赋值IR(
                目标=self._降低表达式(节点.目标),
                值=self._降低表达式(节点.值),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 算术变更):
            ir = 算术赋值IR(
                目标=self._降低表达式(节点.目标),
                算符=节点.算符,
                值=self._降低表达式(节点.值),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 命题变更):
            ir = 赋值IR(
                目标=self._降低表达式(节点.目标),
                值=布尔常量IR(值=节点.值),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 打印):
            ir = 打印IR(值=self._降低表达式(节点.值))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 如果):
            return self._降低如果(节点)
        elif isinstance(节点, 当循环):
            ir = 当循环IR(
                条件=self._降低表达式(节点.条件),
                体=self._降低语句列表(节点.体),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 遍历):
            ir = 遍历IR(
                元素=节点.元素,
                集合=self._降低表达式(节点.集合),
                体=self._降低语句列表(节点.体),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 尝试):
            return self._降低尝试(节点)
        elif isinstance(节点, 跳出):
            ir = 跳出IR()
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 继续):
            ir = 继续IR()
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 以所得):
            ir = 以所得IR(值=self._降低表达式(节点.值))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 函数定义):
            return self._降低函数定义(节点)
        elif isinstance(节点, 引入):
            ir = 引入IR(模块=节点.模块)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 从中引入):
            ir = 从中引入IR(模块=节点.模块, 名称=list(节点.名称))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 导入别名):
            ir = 导入别名IR(模块=节点.模块, 别名=节点.别名)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 断言):
            ir = 断言IR(
                表达式=self._降低表达式(节点.表达式),
                消息=节点.消息,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 类别声明):
            return self._降低类别声明(节点)
        elif isinstance(节点, 删除):
            ir = 删除IR(目标=self._降低表达式(节点.目标))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 空操作):
            ir = 空操作IR()
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 报错):
            ir = 报错IR(消息=节点.消息, 错误类型=节点.错误类型)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 依次给出):
            ir = 依次给出IR(值=self._降低表达式(节点.值))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 等待语句):
            if 节点.记作名:
                ir = 等待记作IR(
                    调用=self._降低表达式(节点.调用),
                    记作名=节点.记作名,
                )
                self._记录位置(ir, 节点)
                return ir
            ir = 等待语句IR(调用=self._降低表达式(节点.调用))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 全局声明):
            ir = 全局声明IR(名称=list(节点.名称))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 外层声明):
            ir = 外层声明IR(名称=list(节点.名称))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 最终收束):
            ir = 最终收束IR(体=self._降低语句列表(节点.体))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 分情形):
            return self._降低分情形(节点)
        elif isinstance(节点, 表达式语句):
            return self._降低表达式语句(节点)
        elif isinstance(节点, 调用):
            ir = 表达式语句IR(表达式=self._降低表达式(节点))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 本地模块引入):
            ir = 本地模块引入IR(模块名=节点.模块名, 别名=节点.别名)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 从本地模块引入):
            ir = 从本地模块引入IR(模块名=节点.模块名, 名称=list(节点.名称))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 公开声明):
            ir = 公开声明IR(名称=list(节点.名称))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 运行入口):
            ir = 程序入口IR(体=self._降低语句列表(节点.体))
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 类别方法定义):
            return self._降低类别方法定义(节点)
        elif isinstance(节点, 异步遍历):
            ir = 异步遍历IR(
                集合=self._降低表达式(节点.集合),
                元素=节点.元素,
                体=self._降低语句列表(节点.体),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 原样报出):
            ir = 原样报出IR()
            self._记录位置(ir, 节点)
            return ir
        else:
            raise TypeError(f"降低器：未知语句类型 {type(节点).__name__}")

    def _降低语句列表(self, 语句列表: list) -> list[语句IR]:
        """降低一组语句。"""
        return [self._降低语句(s) for s in 语句列表 if s is not None]

    def _降低如果(self, 节点: 如果) -> 如果IR:
        return 如果IR(
            条件=self._降低表达式(节点.条件),
            则=self._降低语句列表(节点.则),
            否则如果=[
                (self._降低表达式(cond), self._降低语句列表(body))
                for cond, body in 节点.否则如果
            ],
            否则=self._降低语句列表(节点.否则),
        )

    def _降低尝试(self, 节点: 尝试) -> 尝试IR:
        return 尝试IR(
            体=self._降低语句列表(节点.体),
            异常体=self._降低语句列表(节点.异常体),
            异常名=节点.异常名,
            最终体=self._降低语句列表(节点.最终体),
            错误类型处理=[(t, self._降低语句列表(b)) for t, b in 节点.错误类型处理],
            有泛化处理=节点.有泛化处理,
        )

    def _降低类别方法定义(self, 节点: 类别方法定义) -> 类别方法IR:
        """v0.0.9: 降低类别方法定义。"""
        体IR = self._降低语句列表(节点.体)
        is_async = self._体含等待(体IR)
        is_gen = self._体含依次给出(体IR)
        ir = 类别方法IR(
            类别名=节点.类别名,
            名称=节点.名称,
            参数=list(节点.参数),
            参数默认值=[
                self._降低表达式(d) if d is not None else None
                for d in 节点.参数默认值
            ],
            体=体IR,
            是异步=is_async,
            是生成器=is_gen,
        )
        self._记录位置(ir, 节点)
        return ir

    def _降低函数定义(self, 节点: 函数定义) -> 函数定义IR:
        """降低函数定义并检测 async/generator 标志。"""
        体IR = self._降低语句列表(节点.体)
        is_async = self._体含等待(体IR)
        is_gen = self._体含依次给出(体IR)
        ir = 函数定义IR(
            名称=节点.名称,
            参数=list(节点.参数),
            体=体IR,
            单表达式=节点.单表达式,
            是异步=is_async,
            是生成器=is_gen,
            参数默认值=[
                self._降低表达式(d) if d is not None else None
                for d in 节点.参数默认值
            ],
        )
        self._记录位置(ir, 节点)
        return ir

    def _降低类别声明(self, 节点: 类别声明) -> 类别声明IR:
        """降低类别声明。"""
        return 类别声明IR(
            名称=节点.名称,
            字段列表=[
                类别字段IR(
                    名称=f.名称,
                    类型=f.类型,
                    默认值=self._降低表达式(f.默认值) if f.默认值 else None,
                    可空=f.可空,
                    不得为负=f.不得为负,
                )
                for f in 节点.字段列表
            ],
        )

    def _降低分情形(self, 节点: 分情形) -> 分情形IR:
        分支列表: list = []
        for val, body in 节点.分支列表:
            val_ir = self._降低表达式(val) if val is not None else None
            分支列表.append((val_ir, self._降低语句列表(body)))
        return 分情形IR(
            对象=self._降低表达式(节点.对象),
            分支列表=分支列表,
        )

    def _降低表达式语句(self, 节点: 表达式语句) -> 语句IR | list[语句IR]:
        """降低表达式语句：括号分组透明，调用包装为表达式语句。"""
        # 如果动作列表只有一个调用，将其包装为表达式语句IR
        if 节点.动作列表:
            lowered = []
            for stmt in 节点.动作列表:
                lowered.append(self._降低语句(stmt) or 空操作IR())
            # 如果只有一个调用，使用表达式语句IR
            return lowered[0] if len(lowered) == 1 else 最终收束IR(体=lowered)
        return 空操作IR()

    # ==================== 表达式降低 ====================

    def _降低表达式(self, 节点) -> 表达式IR:
        """将 Surface AST 表达式降低为 Core IR 表达式。"""
        if isinstance(节点, 整数):
            ir = 整数常量IR(值=节点.值)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 小数):
            ir = 小数常量IR(值=节点.值)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 文本):
            ir = 文本常量IR(值=节点.值)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 布尔):
            ir = 布尔常量IR(值=节点.值)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 空值):
            ir = 空值IR()
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 列表字面量):
            ir = 列表字面量IR(
                元素=[self._降低表达式(e) for e in 节点.元素],
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 元组字面量):
            ir = 元组字面量IR(
                元素=[self._降低表达式(e) for e in 节点.元素],
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 集合字面量):
            ir = 集合字面量IR(
                元素=[self._降低表达式(e) for e in 节点.元素],
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 变量):
            ir = 变量引用IR(名称=节点.名称, 名称来源=节点.名称来源)
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 二元运算):
            ir = 二元运算IR(
                左=self._降低表达式(节点.左),
                算符=节点.算符,
                右=self._降低表达式(节点.右),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 一元运算):
            ir = 一元运算IR(
                算符=节点.算符,
                操作数=self._降低表达式(节点.操作数),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 调用):
            ir = 调用IR(
                函数=self._降低表达式(节点.函数),
                参数=[self._降低表达式(p) for p in 节点.参数],
                制定参数=[(名称, self._降低表达式(值)) for 名称, 值 in 节点.制定参数],
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 身份判断):
            ir = 身份判断IR(
                左=self._降低表达式(节点.左),
                右=self._降低表达式(节点.右),
                肯定=节点.肯定,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 等待表达式):
            ir = 等待表达式IR(
                调用=self._降低表达式(节点.调用),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 当前错误):
            ir = 当前错误IR()
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 错误文本):
            ir = 错误文本IR()
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 成员访问):
            ir = 成员访问IR(
                对象=self._降低表达式(节点.对象),
                成员=节点.成员,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 上下文成员访问):
            # 临时降低：其姓名 → 其.姓名（语义分析后将解析为实际焦点变量）
            obj = 变量引用IR(名称="其")
            ir = 成员访问IR(对象=obj, 成员=节点.首成员)
            self._记录位置(ir, 节点)
            for 成员 in 节点.后续访问:
                ir = 成员访问IR(对象=ir, 成员=成员)
            return ir
        elif isinstance(节点, 字符串下标):
            ir = 字符串下标IR(
                对象=self._降低表达式(节点.对象),
                键=节点.键,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 表达式下标):
            ir = 表达式下标IR(
                对象=self._降低表达式(节点.对象),
                索引=self._降低表达式(节点.索引),
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 切片下标):
            ir = 切片下标IR(
                对象=self._降低表达式(节点.对象),
                开始=self._降低表达式(节点.开始) if 节点.开始 else None,
                结束=self._降低表达式(节点.结束) if 节点.结束 else None,
            )
            self._记录位置(ir, 节点)
            return ir
        elif isinstance(节点, 映射字面量):
            ir = 映射字面量IR(
                条目=[
                    (self._降低表达式(k), self._降低表达式(v))
                    for k, v in 节点.条目
                ],
            )
            self._记录位置(ir, 节点)
            return ir
        else:
            raise TypeError(f"降低器：未知表达式类型 {type(节点).__name__}")

    # ==================== 辅助检测 ====================

    def _体含等待(self, 语句列表: list[语句IR]) -> bool:
        """检测 Core IR 语句列表中是否包含异步操作。"""
        for s in 语句列表:
            if self._语句含等待(s):
                return True
        return False

    def _语句含等待(self, s: 语句IR) -> bool:
        """递归检测单条 Core IR 语句是否含有异步操作。"""
        if isinstance(s, (等待语句IR,)):
            return True
        if isinstance(s, 以所得IR):
            return self._表达式含等待(s.值)
        if isinstance(s, 赋值IR):
            return (s.值 is not None and self._表达式含等待(s.值)) or self._表达式含等待(s.目标)
        if isinstance(s, 算术赋值IR):
            return self._表达式含等待(s.值) or self._表达式含等待(s.目标)
        if isinstance(s, 打印IR):
            return self._表达式含等待(s.值)
        if isinstance(s, 依次给出IR):
            return self._表达式含等待(s.值)
        if isinstance(s, 表达式语句IR):
            return self._表达式含等待(s.表达式)
        if isinstance(s, 函数定义IR):
            return False  # 嵌套定义不影响外层 async 标志
        # 复合语句：递归检查子语句
        for child in self._遍历子语句(s):
            if self._语句含等待(child):
                return True
        return False

    def _表达式含等待(self, e: 表达式IR) -> bool:
        """检测 Core IR 表达式中是否包含等待表达式。"""
        if isinstance(e, 等待表达式IR):
            return True
        if isinstance(e, 调用IR):
            return self._表达式含等待(e.函数) or any(self._表达式含等待(p) for p in e.参数)
        if isinstance(e, 二元运算IR):
            return self._表达式含等待(e.左) or self._表达式含等待(e.右)
        if isinstance(e, 一元运算IR):
            return self._表达式含等待(e.操作数)
        if isinstance(e, 成员访问IR):
            return self._表达式含等待(e.对象)
        if isinstance(e, (表达式下标IR, 字符串下标IR, 切片下标IR)):
            result = self._表达式含等待(e.对象)
            if isinstance(e, 表达式下标IR):
                result = result or self._表达式含等待(e.索引)
            if isinstance(e, 切片下标IR):
                if e.开始:
                    result = result or self._表达式含等待(e.开始)
                if e.结束:
                    result = result or self._表达式含等待(e.结束)
            return result
        if isinstance(e, 身份判断IR):
            return self._表达式含等待(e.左) or self._表达式含等待(e.右)
        if isinstance(e, 列表字面量IR):
            return any(self._表达式含等待(el) for el in e.元素)
        if isinstance(e, 映射字面量IR):
            return any(self._表达式含等待(k) or self._表达式含等待(v) for k, v in e.条目)
        return False

    def _体含依次给出(self, 语句列表: list[语句IR]) -> bool:
        """检测 Core IR 语句列表中是否包含依次给出（yield）。"""
        for s in 语句列表:
            if self._语句含依次给出(s):
                return True
        return False

    def _语句含依次给出(self, s: 语句IR) -> bool:
        """递归检测单条 Core IR 语句是否含有依次给出。"""
        if isinstance(s, 依次给出IR):
            return True
        if isinstance(s, 函数定义IR):
            return False  # 嵌套定义不影响外层
        for child in self._遍历子语句(s):
            if self._语句含依次给出(child):
                return True
        return False

    def _遍历子语句(self, s: 语句IR) -> list[语句IR]:
        """获取 Core IR 复合语句的直接子语句。"""
        children: list[语句IR] = []
        if isinstance(s, 如果IR):
            children.extend(s.则)
            for _, body in s.否则如果:
                children.extend(body)
            children.extend(s.否则)
        elif isinstance(s, 当循环IR):
            children.extend(s.体)
        elif isinstance(s, 遍历IR):
            children.extend(s.体)
        elif isinstance(s, 尝试IR):
            children.extend(s.体)
            children.extend(s.异常体)
            children.extend(s.最终体)
        elif isinstance(s, 分情形IR):
            for _, body in s.分支列表:
                children.extend(body)
        elif isinstance(s, 最终收束IR):
            children.extend(s.体)
        elif isinstance(s, 函数定义IR):
            children.extend(s.体)
        return children


def 降低(ast: 程序) -> 降低结果:
    """便捷函数：Surface AST → Core IR（含位置映射）。

    Returns:
        降低结果 包含 Core IR 程序和 AST→IR 位置映射。
    """
    return 降低器(ast).降低()


def 降低_仅语法(ast: 程序) -> 程序IR:
    """便捷函数：仅获取 Core IR 程序，不跟踪位置。

    用于只需要 Core IR 而不需要位置信息的场景（如语法测试）。
    """
    return 降低器(ast).降低().ir
