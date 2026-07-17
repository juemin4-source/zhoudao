"""周道：递归下降解析器（Parser）。

将 Token 流解析为 AST（程序 → 句子 → 语句 → 表达式）。
使用向前看（lookahead）处理「设」的分派歧义和「不然」/「否则」链。
"""

import sys
sys.setrecursionlimit(10000)

from .errors import 源码位置, 语法错误
from .tokens import (
    Token,
    NUMBER, STRING, IDENTIFIER,
    LIST_OPEN, LIST_CLOSE,
    MODULE_OPEN, MODULE_CLOSE,
    PAREN_OPEN, PAREN_CLOSE,
    COMMA, DUN_HAO, PERIOD, COLON, SEMICOLON, EOF, COMMENT,
    K_SET, K_MAKE, K_AS, K_BECOME,
    K_TRUE_STATE, K_FALSE_STATE, K_NONE,
    K_IF, K_THEN, K_ELSE,
    K_WHILE, K_WHEN, K_ALWAYS,
    K_FROM, K_IN, K_EACH_AS,
    K_BREAK, K_CONTINUE,
    K_TRY, K_EXCEPT,
    K_WITH, K_RESULT, K_AS_RESULT,
    K_IMPORT,
    OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_FLOOR_DIV, OP_MOD,
    OP_EQ, OP_NE, OP_GT, OP_LT, OP_GE, OP_LE,
    OP_AND, OP_OR, OP_NOT,
    OP_IN, OP_NOT_IN,
    SYM_ADD, SYM_SUB, SYM_MUL, SYM_DIV, SYM_POW,
    SYM_FLOOR_DIV, SYM_MOD,
    SYM_EQ, SYM_NE, SYM_GT, SYM_LT, SYM_GE, SYM_LE,
    WORD_NEG,
    K_ITS,
    LIT_TRUE, LIT_FALSE,
    K_AND_THEN, K_PRINT,
    K_DEFINE, K_SETUP, K_CATEGORY, K_INCLUDE, K_INCLUDE_LONG, K_DEFAULT_AS,
    K_MUST, K_MUST_NOT, K_ELSE_ERROR,
    K_DELETE, K_IS, K_IS_NOT, K_SELF,
    K_PASS, K_RAISE, K_YIELD,
    K_AWAIT, K_DONE, K_OF_RESULT, K_AWAIT_EACH, K_RERAISE,
    K_FINALLY, K_FINALLY_DO,
    K_MATCH, K_MATCH_CASES, K_CASE, K_DEFAULT,
    K_AS_ALIAS, K_SCOPE_DECL, K_GLOBAL, K_NONLOCAL, K_CAN, K_DE, K_INTERFACE, K_ENTRY,
)
from .ast_nodes import (
    程序, 句子, 绑定, 空值绑定, 命题绑定,
    变更, 算术变更, 命题变更,
    打印, 如果, 当循环, 遍历, 尝试,
    跳出, 继续, 以所得, 函数定义,
    引入, 从中引入, 导入别名,
    断言, 类别声明, 类别字段,
    删除, 空操作, 报错, 依次给出,
    等待语句, 全局声明, 外层声明, 公开声明, 运行入口, 本地模块引入, 从本地模块引入, 类别方法定义, 异步遍历, 原样报出,
    最终收束, 分情形,
    表达式语句,
    整数, 小数, 文本, 布尔, 空值,
    列表字面量, 变量, 二元运算, 一元运算, 调用,
    身份判断, 等待表达式, 当前错误, 错误文本,
    成员访问, 字符串下标, 表达式下标,
    切片下标, 映射字面量,
    上下文成员访问,
    元组字面量, 集合字面量,
    表达式,
)


class 解析器:
    """周道递归下降解析器。"""

    def __init__(self, 令牌列表: list[Token]):
        self.令牌 = 令牌列表
        self.当前位置 = 0
        self._在定义内 = False  # 是否在函数定义中
        self._在异常内 = False  # 是否在 except 子句中
        self._循环深度 = 0     # 嵌套循环深度（用于检查 break/continue）
        self._待定注释: list[str] = []  # 待附着的注释行

    # ==================== 辅助方法 ====================

    def _当前(self) -> Token:
        return self.令牌[self.当前位置]

    def _看(self, 偏移: int = 0) -> Token:
        索引 = self.当前位置 + 偏移
        return self.令牌[索引] if 索引 < len(self.令牌) else self.令牌[-1]

    def _吃(self) -> Token:
        tok = self.令牌[self.当前位置]
        self.当前位置 += 1
        return tok

    def _回归(self, 数量: int = 1):
        self.当前位置 -= 数量

    def _期望(self, *类型列表: str, 错误消息: str = "") -> Token:
        tok = self._当前()
        if tok.token_type in 类型列表:
            return self._吃()
        消息 = 错误消息 or f"期望 {' 或 '.join(类型列表)}，实际得到 {tok.token_type}({tok.值!r})"
        raise 语法错误(消息, tok.位置)

    def _匹配(self, *类型列表: str) -> bool:
        if self._当前().token_type in 类型列表:
            self._吃()
            return True
        return False

    def _跳过逗号(self):
        if self._当前().token_type == COMMA:
            self._吃()

    # ==================== 程序 / 句子 ====================

    def 解析(self) -> 程序:
        程序节点 = 程序()
        self._待定注释: list[str] = []
        while self._当前().token_type != EOF:
            句子节点 = self._解析一句()
            if 句子节点.语句列表 or 句子节点.前导注释 or 句子节点.尾行注释:
                程序节点.句子列表.append(句子节点)
        return 程序节点

    def _吃注释(self):
        """消费前置的 COMMENT Token 并收集到待定注释列表。"""
        while self._当前().token_type == COMMENT:
            self._待定注释.append(self._吃().值)

    def _解析一句(self) -> 句子:
        语句列表: list = []
        # 收集句子前的注释
        self._吃注释()
        前导注释 = list(self._待定注释)
        self._待定注释.clear()
        尾行注释 = None

        while self._当前().token_type not in (PERIOD, EOF):
            # 遇到注释：如果当前句子已有内容则视为尾行注释，否则为前导
            if self._当前().token_type == COMMENT:
                注释 = self._吃().值
                if 语句列表:
                    尾行注释 = 注释
                else:
                    前导注释.append(注释)
                continue
            语句 = self._解析顶层语句()
            if 语句 is not None:
                语句列表.append(语句)
            if self._当前().token_type == COMMA:
                self._吃()
            elif self._当前().token_type == SEMICOLON:
                self._吃()  # 分号作为句内动作分隔符，继续下一动作
        if self._当前().token_type == PERIOD:
            self._吃()

        # 句子末尾的注释作为尾行注释
        if self._当前().token_type == COMMENT:
            尾行注释 = self._吃().值
        elif not 语句列表 and not 前导注释:
            pass  # 空句子

        return 句子(语句列表=语句列表, 前导注释=前导注释, 尾行注释=尾行注释)

    # ==================== 顶层语句分派 ====================

    def _解析顶层语句(self):
        位置 = self._当前().位置

        if self._匹配(K_DEFINE):
            return self._解析新定义(位置)
        elif self._匹配(K_SET):
            return self._解析设定(位置)
        elif self._匹配(K_SETUP):
            return self._解析设置(位置)
        elif self._匹配(K_MAKE):
            return self._解析使(位置)
        elif self._匹配(K_PRINT):
            return self._解析打印(位置)
        elif self._匹配(K_IF):
            return self._解析如果链(位置)
        elif self._匹配(K_WHILE):
            return self._解析当(位置)
        elif self._匹配(K_FROM):
            if self._看().token_type == MODULE_OPEN:
                return self._解析从中引入(位置)
            elif self._当前().token_type == IDENTIFIER and self._当前().值 == "周道源文件":
                return self._解析从本地模块引入(位置)
            elif self._当前().token_type == IDENTIFIER and self._当前().值.startswith("Python"):
                return self._解析从Python模块引入(位置)
            else:
                return self._解析遍历(位置)
        elif self._匹配(K_TRY):
            return self._解析尝试(位置)
        elif self._匹配(K_BREAK):
            if self._循环深度 <= 0:
                raise 语法错误("「跳出循环」只能在循环内使用", 位置)
            return 跳出(位置=位置)
        elif self._匹配(K_CONTINUE):
            if self._循环深度 <= 0:
                raise 语法错误("「继续下一轮」只能在循环内使用", 位置)
            return 继续(位置=位置)
        elif self._匹配(K_IMPORT):
            if self._当前().token_type == IDENTIFIER and self._当前().值 == "周道源文件":
                return self._解析本地模块引入(位置)
            elif self._当前().token_type == IDENTIFIER and self._当前().值.startswith("Python"):
                return self._解析Python模块引入(位置)
            return self._解析引入含别名(位置)
        elif self._匹配(K_DELETE):
            return self._解析删除(位置)
        elif self._匹配(K_PASS):
            return 空操作(位置=位置)
        elif self._匹配(K_RERAISE):
            return 原样报出(位置=位置)
        elif self._匹配(K_RAISE):
            return self._解析报错(位置)
        elif self._匹配(K_YIELD):
            if not self._在定义内:
                raise 语法错误("「依次给出」只能在定义内使用", 位置)
            return self._解析依次给出(位置)
        elif self._匹配(K_AWAIT):
            if not self._在定义内:
                raise 语法错误("「等待」只能在定义内使用", 位置)
            return self._解析等待(位置)
        elif self._匹配(K_SCOPE_DECL):
            return self._解析作用域声明(位置)
        elif self._匹配(K_MATCH):
            return self._解析分情形(位置)
        elif self._匹配(K_INTERFACE):
            return self._解析公开声明(位置)
        elif self._匹配(K_ENTRY):
            return self._解析程序入口(位置)
        elif self._当前().token_type == IDENTIFIER and self._看(1).token_type in (K_MUST, K_MUST_NOT):
            名称令牌 = self._吃()
            return self._解析断言(变量(名称令牌.值), 位置)
        elif self._当前().token_type == IDENTIFIER and self._看(1).token_type == PAREN_OPEN:
            # 函数调用作为语句
            名称 = self._吃().值
            调用节点 = self._解析后缀链(变量(名称, 位置=位置))
            return 表达式语句(动作列表=[调用节点])
        elif self._当前().token_type == IDENTIFIER and self._看(1).token_type == K_DE:
            # 成员访问作为语句（如 用户的问候（））
            名称 = self._吃().值
            expr = self._解析后缀链(变量(名称, 位置=位置))
            return 表达式语句(动作列表=[expr])
        elif self._匹配(K_WITH):
            if not self._在定义内:
                raise 语法错误("「以」只能在定义内使用", 位置)
            return self._解析所得(位置)
        elif self._匹配(PAREN_OPEN):
            动作列表 = self._解析动作直到(在括号内=True)
            self._期望(PAREN_CLOSE, 错误消息="括号分组缺少 ）")
            return 表达式语句(动作列表=动作列表, 位置=位置)
        elif self._匹配(K_AND_THEN):
            return self._解析顶层语句()
        else:
            raise 语法错误(f"意外的标记：{self._当前().token_type}({self._当前().值!r})", 位置)

    # ==================== 设定 / 使 / 打印 ====================

    def _解析设定(self, 位置: 源码位置):
        if self._当前().token_type in (OP_ADD, OP_SUB, OP_MOD):
            名称 = self._吃().值
            while self._当前().token_type in (IDENTIFIER, OP_ADD, OP_SUB):
                名称 += self._吃().值
        else:
            名称令牌 = self._期望(IDENTIFIER, 错误消息="设 后缺少名称")
            名称 = 名称令牌.值
        if self._匹配(K_AS):
            return 绑定(名称=名称, 值=self._解析表达式(), 位置=位置)
        elif self._匹配(K_NONE):
            return 空值绑定(名称=名称, 位置=位置)
        elif self._匹配(K_TRUE_STATE):
            return 命题绑定(名称=名称, 值=True, 位置=位置)
        elif self._匹配(K_FALSE_STATE):
            return 命题绑定(名称=名称, 值=False, 位置=位置)
        elif self._当前().token_type == PAREN_OPEN:
            return self._解析函数定义(名称, 位置)
        else:
            raise 语法错误(f"设 {名称} 后缺少「为」「没有值」「成立/不成立」或「（」", self._当前().位置)

    def _解析使(self, 位置: 源码位置):
        名称令牌 = self._期望(IDENTIFIER, 错误消息="使 后缺少名称")
        # 解析左值后缀链（成员访问、下标）
        左值 = self._解析后缀链(变量(名称令牌.值, 位置=位置))
        if self._匹配(K_BECOME):
            return 变更(目标=左值, 值=self._解析表达式(), 位置=位置)
        elif self._匹配(K_TRUE_STATE):
            return 命题变更(目标=左值, 值=True, 位置=位置)
        elif self._匹配(K_FALSE_STATE):
            return 命题变更(目标=左值, 值=False, 位置=位置)
        elif self._当前().token_type in (OP_ADD, OP_SUB, OP_MUL, OP_DIV):
            算符令牌 = self._吃()
            映射 = {OP_ADD: "+=", OP_SUB: "-=", OP_MUL: "*=", OP_DIV: "/="}
            return 算术变更(目标=左值, 算符=映射[算符令牌.token_type], 值=self._解析表达式(), 位置=位置)
        elif self._当前().token_type in (SYM_ADD, SYM_SUB, SYM_MUL, SYM_DIV,
                                         SYM_POW, SYM_FLOOR_DIV, SYM_MOD,
                                         OP_FLOOR_DIV, OP_MOD):
            raise 语法错误(
                "「使」后需要变化动作：加、减、乘、除 或 变为。"
                "不接受符号运算符。",
                self._当前().位置)
        else:
            raise 语法错误(f"使 {左值} 后缺少「变为」或变化动作", self._当前().位置)

    def _解析打印(self, 位置: 源码位置):
        return 打印(值=self._解析表达式(), 位置=位置)

    # ==================== 如果 / 不然链 ====================

    def _解析如果链(self, 位置: 源码位置):
        条件 = self._解析条件()
        self._跳过逗号()
        self._期望(K_THEN, 错误消息="如果条件后缺少「就」")
        则体 = self._解析动作直到()
        否则如果列表: list = []
        否则体: list = []
        while self._当前().token_type in (COMMA, SEMICOLON):
            self._吃()
            if self._当前().token_type == K_ELSE:
                self._吃()
                if self._当前().token_type == COMMA:
                    self._吃()
                    if self._当前().token_type == K_IF:
                        self._吃()
                        否则条件 = self._解析条件()
                        self._跳过逗号()
                        self._期望(K_THEN, 错误消息="不然如果条件后缺少「就」")
                        否则体2 = self._解析动作直到()
                        否则如果列表.append((否则条件, 否则体2))
                        continue
                    else:
                        否则体 = self._解析动作直到()
                        break
                elif self._当前().token_type == K_THEN:
                    self._吃()
                    否则体 = self._解析动作直到()
                    break
                else:
                    否则体 = self._解析动作直到()
                    break
            else:
                self._回归(1)
                break
        return 如果(条件=条件, 则=则体, 否则如果=否则如果列表, 否则=否则体, 位置=位置)

    def _解析动作直到(self, 在定义体: bool = False, 在括号内: bool = False) -> list:
        """解析动作链。在定义体=True时，不因K_SET/K_MAKE等语句关键字中断。"""
        动作列表: list = []
        while self._当前().token_type not in (PERIOD, PAREN_CLOSE, MODULE_CLOSE, COLON, EOF):
            if self._当前().token_type == COMMA:
                next_type = self._看(1).token_type
                if 在定义体:
                    # 定义体内：逗号只是动作分隔符，继续解析
                    if next_type in (K_ELSE, K_EXCEPT, K_FINALLY, K_CASE, K_DEFAULT):
                        break  # 控制结构结束，返回给调用者
                    self._吃()
                    continue
                if 在括号内:
                    # 括号分组内：逗号只是动作分隔符，不因语句关键字中断
                    if next_type in (K_ELSE, K_EXCEPT, K_FINALLY, K_CASE, K_DEFAULT):
                        break
                    self._吃()
                    continue
                if next_type in (K_ELSE, K_EXCEPT, K_IF, K_SET, K_MAKE, K_PRINT, K_WHILE, K_FROM, K_TRY, K_BREAK, K_CONTINUE, K_IMPORT, K_DEFINE, K_SETUP, K_DELETE, K_PASS, K_RAISE, K_YIELD, K_AWAIT, K_SCOPE_DECL, K_MATCH, K_MUST, K_MUST_NOT, K_FINALLY, K_CASE, K_DEFAULT):
                    break
                self._吃()
                continue
            # 分号：只作为结构内部分隔符，不是通用语句终止符
            if self._当前().token_type == SEMICOLON:
                next_type = self._看(1).token_type
                # 如果后跟控制结构关键词，退出让调用者处理
                if next_type in (K_ELSE, K_EXCEPT, K_FINALLY, K_CASE, K_DEFAULT, K_IF):
                    break
                # 否则作为动作分隔符消费并继续
                self._吃()
                continue
            if self._当前().token_type == K_AND_THEN:
                self._吃()
            动作 = self._解析顶层语句()
            if 动作 is not None:
                动作列表.append(动作)
        return 动作列表

    # ==================== 当循环 ====================

    def _剥去末尾时(self, 条件):
        """递归遍历条件表达式，剥离末尾变量名中的「时」字。"""
        from .ast_nodes import 变量, 二元运算, 一元运算
        if isinstance(条件, 变量) and 条件.名称.endswith("时") and 条件.名称 != "时":
            条件.名称 = 条件.名称[:-1]
        elif isinstance(条件, 二元运算):
            self._剥去末尾时(条件.右)
        elif isinstance(条件, 一元运算):
            self._剥去末尾时(条件.操作数)

    def _解析当(self, 位置: 源码位置):
        条件 = self._解析条件()
        # 处理"时"与前一标识符合并的情况（如"上限时"）
        if not self._匹配(K_WHEN):
            tok = self._当前()
            if tok.token_type == IDENTIFIER and tok.值 == "时":
                self._吃()
            elif tok.token_type == IDENTIFIER and tok.值.endswith("时"):
                # 标识符末尾有时（如"上限时"），剥离时字
                self._剥去末尾时(条件)
                # "时"已作为末尾剥离，不需要额外消费
            elif tok.token_type == COMMA:
                # 时已被合并到标识符末尾（如"上限时"），需要剥离
                self._剥去末尾时(条件)
            else:
                raise 语法错误("当条件后缺少「时」", self._当前().位置)
        self._期望(COMMA, 错误消息="「时」后缺少逗号")
        self._期望(K_ALWAYS, 错误消息="「时」后缺少「一直」")
        self._循环深度 += 1
        体 = self._解析动作直到()
        self._循环深度 -= 1
        return 当循环(条件=条件, 体=体, 位置=位置)

    # ==================== 遍历 ====================

    def _解析遍历(self, 位置: 源码位置):
        集合 = self._解析表达式()
        self._期望(K_IN, 错误消息="遍历源后缺少「中」")
        self._期望(COMMA, 错误消息="「中」后缺少逗号")
        if self._匹配(K_AWAIT_EACH):
            元素令牌 = self._期望(IDENTIFIER, 错误消息="「每等到一项记作」后缺少元素名")
            self._期望(COMMA, 错误消息="元素名后缺少逗号")
            self._期望(K_THEN, 错误消息="缺少「就」")
            self._循环深度 += 1
            体 = self._解析动作直到()
            self._循环深度 -= 1
            return 异步遍历(元素=元素令牌.值, 集合=集合, 体=体, 位置=位置)
        self._期望(K_EACH_AS, 错误消息="缺少「每取一项记作」")
        元素令牌 = self._期望(IDENTIFIER, 错误消息="「每取一项记作」后缺少元素名")
        self._期望(COMMA, 错误消息="元素名后缺少逗号")
        self._期望(K_THEN, 错误消息="缺少「就」")
        self._循环深度 += 1
        体 = self._解析动作直到()
        self._循环深度 -= 1
        return 遍历(元素=元素令牌.值, 集合=集合, 体=体, 位置=位置)

    # ==================== 尝试 ====================

    def _解析尝试(self, 位置: 源码位置):
        体 = self._解析动作直到()
        异常体: list = []
        异常名: str | None = None
        错误类型处理: list[tuple[str, list]] = []
        有泛化处理: bool = False
        最终体: list = []
        self._匹配(SEMICOLON, COMMA)

        # v0.0.9: 检测 如果错误类型是<类型>，就…
        while self._当前().token_type == K_IF:
            self._吃()  # 如果
            错误类型 = None
            tok = self._当前()
            if tok.token_type == IDENTIFIER and tok.值 == "错误类型":
                self._吃()
                if self._当前().token_type == IDENTIFIER and self._当前().值 == "是":
                    self._吃()
                    类型令牌 = self._期望(IDENTIFIER, 错误消息="错误类型后缺少类型名")
                    错误类型 = 类型令牌.值
            elif tok.token_type == IDENTIFIER and tok.值.startswith("错误类型"):
                merged = self._吃().值
                rest = merged[4:]
                if rest.startswith("是"):
                    rest = rest[1:]
                if rest:
                    错误类型 = rest
            if 错误类型 is None:
                break
            self._跳过逗号()
            self._期望(K_THEN, 错误消息="错误类型处理缺少「就」")
            旧上下文 = self._在异常内
            self._在异常内 = True
            分支体 = self._解析动作直到()
            self._在异常内 = 旧上下文
            错误类型处理.append((错误类型, 分支体))
            self._匹配(SEMICOLON, COMMA)

        # 检测 如果出错（泛化捕获）
        if self._匹配(K_EXCEPT):
            有泛化处理 = True
            if self._匹配(K_AS):
                异常名令牌 = self._期望(IDENTIFIER, 错误消息="「如果出错为」后缺少异常名")
                异常名 = 异常名令牌.值
            self._跳过逗号()
            self._期望(K_THEN, 错误消息="「如果出错」后缺少「就」")
            旧上下文 = self._在异常内
            self._在异常内 = True
            异常体 = self._解析动作直到()
            self._在异常内 = 旧上下文
            self._匹配(SEMICOLON, COMMA)

        if self._匹配(K_FINALLY):
            self._跳过逗号()
            self._期望(K_FINALLY_DO, 错误消息="「无论是否出错」后缺少「最后」")
            最终体 = self._解析动作直到()

        return 尝试(体=体, 异常体=异常体, 异常名=异常名,
                   错误类型处理=错误类型处理, 有泛化处理=有泛化处理,
                   最终体=最终体, 位置=位置)

    # ==================== 所得 ====================

    def _解析所得(self, 位置: 源码位置):
        值 = self._解析表达式()
        ok = self._匹配(K_AS_RESULT, K_RESULT)
        if not ok:
            raise 语法错误("「以」后缺少「所得」或「为所得」", self._当前().位置)
        return 以所得(值=值, 位置=位置)

    # ==================== 函数定义 ====================

    def _解析参数列表(self) -> tuple[list[str], list["表达式 | None"]]:
        """v0.0.8: 解析函数参数列表，支持 名称默认为表达式。"""
        参数: list[str] = []
        参数默认值: list["表达式 | None"] = []
        if self._当前().token_type != PAREN_CLOSE:
            name_tok = self._期望(IDENTIFIER, 错误消息="函数参数需为名称")
            参数.append(name_tok.值)
            if self._匹配(K_DEFAULT_AS):
                参数默认值.append(self._解析表达式())
            else:
                参数默认值.append(None)
            while self._匹配(COMMA, DUN_HAO):
                if self._当前().token_type == PAREN_CLOSE:
                    break
                name_tok = self._期望(IDENTIFIER, 错误消息="函数参数需为名称")
                参数.append(name_tok.值)
                if self._匹配(K_DEFAULT_AS):
                    参数默认值.append(self._解析表达式())
                else:
                    参数默认值.append(None)
        return 参数, 参数默认值

    def _解析函数定义(self, 名称: str, 位置: 源码位置):
        self._期望(PAREN_OPEN, 错误消息="函数名后缺少（")
        参数, 参数默认值 = self._解析参数列表()
        self._期望(PAREN_CLOSE, 错误消息="函数参数后缺少）")
        if self._匹配(K_AS):
            expr = self._解析表达式()
            return 函数定义(名称=名称, 参数=参数, 参数默认值=参数默认值, 体=[以所得(值=expr)], 单表达式=True, 位置=位置)
        self._期望(COMMA, 错误消息="函数头后缺少「为」或「，」")
        # 可选地消费 如下：（设甲（数），如下：动作。形式）
        if self._当前().token_type == IDENTIFIER and self._当前().值 == "如下":
            self._吃()
            self._期望(COLON, 错误消息="「如下」后缺少：")
        旧上下文 = self._在定义内
        self._在定义内 = True
        体 = self._解析动作直到(在定义体=True)
        self._在定义内 = 旧上下文
        return 函数定义(名称=名称, 参数=参数, 体=体, 参数默认值=参数默认值, 单表达式=False, 位置=位置)

    # ==================== 模块 ====================

    def _解析引入(self, 位置: 源码位置):
        self._期望(MODULE_OPEN, 错误消息="「引入」后缺少《")
        模块令牌 = self._期望(IDENTIFIER, 错误消息="《》内缺少模块名")
        模块 = 模块令牌.值
        self._期望(MODULE_CLOSE, 错误消息="模块名后缺少》")
        return 引入(模块=模块, 位置=位置)

    def _解析引入含别名(self, 位置: 源码位置):
        self._期望(MODULE_OPEN, 错误消息="「引入」后缺少《")
        模块令牌 = self._期望(IDENTIFIER, 错误消息="《》内缺少模块名")
        模块 = 模块令牌.值
        self._期望(MODULE_CLOSE, 错误消息="模块名后缺少》")
        if self._匹配(COMMA):
            if self._匹配(K_AS_ALIAS):
                别名令牌 = self._期望(IDENTIFIER, 错误消息="「下文简称」后缺少别名")
                return 导入别名(模块=模块, 别名=别名令牌.值, 位置=位置)
            else:
                self._回归(1)
        return 引入(模块=模块, 位置=位置)

    def _解析Python模块引入(self, 位置: 源码位置):
        """v0.0.9: 解析 引入Python模块《os》。"""
        val = self._吃().值
        if val == "Python":
            self._期望(IDENTIFIER, 错误消息="「Python」后缺少「模块」")
        self._期望(MODULE_OPEN, 错误消息="「模块」后缺少《")
        模块令牌 = self._期望(IDENTIFIER, 错误消息="《》内缺少模块名")
        模块名 = 模块令牌.值
        self._期望(MODULE_CLOSE, 错误消息="模块名后缺少》")
        if self._匹配(COMMA):
            if self._匹配(K_AS_ALIAS):
                别名令牌 = self._期望(IDENTIFIER, 错误消息="「下文简称」后缺少别名")
                return 导入别名(模块=模块名, 别名=别名令牌.值, 位置=位置)
        return 引入(模块=模块名, 位置=位置)

    def _解析从Python模块引入(self, 位置: 源码位置):
        """v0.0.9: 解析 从Python模块《os》中引入 path。"""
        val = self._吃().值
        if val == "Python":
            self._期望(IDENTIFIER, 错误消息="「Python」后缺少「模块」")
            self._吃()  # 模块
        self._期望(MODULE_OPEN, 错误消息="「模块」后缺少《")
        模块令牌 = self._期望(IDENTIFIER, 错误消息="《》内缺少模块名")
        模块 = 模块令牌.值
        self._期望(MODULE_CLOSE, 错误消息="模块名后缺少》")
        self._期望(K_IN, 错误消息="模块名后缺少「中」")
        self._期望(K_IMPORT, 错误消息="「中」后缺少「引入」")
        名称: list[str] = []
        名称令牌 = self._期望(IDENTIFIER, 错误消息="缺少要引入的名称")
        名称.append(名称令牌.值)
        while self._匹配(DUN_HAO, COMMA):
            if self._当前().token_type == IDENTIFIER:
                名称令牌 = self._吃()
                名称.append(名称令牌.值)
            else:
                break
        return 从中引入(模块=模块, 名称=名称, 位置=位置)

    def _解析从中引入(self, 位置: 源码位置):
        self._期望(MODULE_OPEN, 错误消息="「从」后缺少《")
        模块令牌 = self._期望(IDENTIFIER, 错误消息="《》内缺少模块名")
        模块 = 模块令牌.值
        self._期望(MODULE_CLOSE, 错误消息="模块名后缺少》")
        self._期望(K_IN, 错误消息="模块名后缺少「中」")
        self._期望(K_IMPORT, 错误消息="「中」后缺少「引入」")
        名称: list[str] = []
        名称令牌 = self._期望(IDENTIFIER, 错误消息="缺少要引入的名称")
        名称.append(名称令牌.值)
        while self._匹配(DUN_HAO, COMMA):
            if self._当前().token_type == IDENTIFIER:
                名称令牌 = self._吃()
                名称.append(名称令牌.值)
            else:
                break
        return 从中引入(模块=模块, 名称=名称, 位置=位置)

    def _解析本地模块引入(self, 位置: 源码位置):
        """v0.0.8: 解析 引入周道文《工具》 或 引入周道文《工具》，下文简称工具箱。"""
        self._吃()  # 吃掉「周道文」
        self._期望(MODULE_OPEN, 错误消息="「引入周道文」后缺少《")
        模块令牌 = self._期望(IDENTIFIER, 错误消息="《》内缺少周道模块名")
        模块名 = 模块令牌.值
        self._期望(MODULE_CLOSE, 错误消息="模块名后缺少》")
        别名 = None
        if self._匹配(COMMA):
            if self._匹配(K_AS_ALIAS):
                别名令牌 = self._期望(IDENTIFIER, 错误消息="「下文简称」后缺少别名")
                别名 = 别名令牌.值
            else:
                self._回归(1)
        return 本地模块引入(模块名=模块名, 别名=别名, 位置=位置)

    def _解析从本地模块引入(self, 位置: 源码位置):
        """v0.0.8: 解析 从周道源文件《工具》中引入 整理、统计。"""
        self._吃()  # 吃掉「周道源文件」
        self._期望(MODULE_OPEN, 错误消息="「从周道源文件」后缺少《")
        模块令牌 = self._期望(IDENTIFIER, 错误消息="《》内缺少周道模块名")
        模块名 = 模块令牌.值
        self._期望(MODULE_CLOSE, 错误消息="模块名后缺少》")
        self._期望(K_IN, 错误消息="模块名后缺少「中」")
        self._期望(K_IMPORT, 错误消息="「中」后缺少「引入」")
        名称: list[str] = []
        while self._当前().token_type in (IDENTIFIER, OP_ADD, OP_SUB):
            if self._当前().token_type in (OP_ADD, OP_SUB):
                n = self._吃().值
                while self._当前().token_type == IDENTIFIER:
                    n += self._吃().值
                名称.append(n)
            else:
                名称.append(self._吃().值)
            self._匹配(DUN_HAO, COMMA)
        return 从本地模块引入(模块名=模块名, 名称=名称, 位置=位置)

    def _解析公开声明(self, 位置: 源码位置):
        """v0.0.8: 解析 规定模块接口：名称。"""
        名称列表: list[str] = []
        if self._当前().token_type == COLON:
            self._吃()
        while self._当前().token_type not in (PERIOD, EOF):
            if self._当前().token_type == IDENTIFIER:
                名称列表.append(self._吃().值)
            elif self._当前().token_type in (OP_ADD, OP_SUB):
                # 以运算符开头的名称（如 加倍 → 加+倍）
                名称 = self._吃().值
                while self._当前().token_type == IDENTIFIER:
                    名称 += self._吃().值
                名称列表.append(名称)
            elif self._当前().token_type in (COMMA, DUN_HAO):
                self._吃()
            else:
                break
        if not 名称列表:
            raise 语法错误("模块接口名称列表不能为空", 位置)
        return 公开声明(名称=名称列表, 位置=位置)

    def _解析程序入口(self, 位置: 源码位置):
        """v0.0.8: 解析 运行如下：动作；动作。"""
        self._期望(COLON, 错误消息="「运行如下」后缺少：")
        体: list = []
        while self._当前().token_type not in (PERIOD, EOF):
            语句 = self._解析顶层语句()
            if 语句 is not None:
                体.append(语句)
            if self._当前().token_type == COMMA:
                self._吃()
            elif self._当前().token_type == SEMICOLON:
                self._吃()
        if self._当前().token_type == PERIOD:
            self._吃()
        return 运行入口(体=体, 位置=位置)

    # ==================== 第二批：定义 / 设置 / 类别 ====================

    def _解析新定义(self, 位置: 源码位置):
        if self._当前().token_type in (OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD):
            名称 = self._吃().值
            while self._当前().token_type in (IDENTIFIER, OP_ADD, OP_SUB):
                名称 += self._吃().值
        else:
            名称令牌 = self._期望(IDENTIFIER, 错误消息="「定义」后缺少名称")
            名称 = 名称令牌.值
        # v0.0.9: 检测 定义甲类别的乙 模式
        if self._当前().token_type == K_CATEGORY:
            self._吃()
            return self._解析类别方法定义(名称, 位置)
        self._期望(PAREN_OPEN, 错误消息="定义名后缺少（")
        参数, 参数默认值 = self._解析参数列表()
        self._期望(PAREN_CLOSE, 错误消息="定义参数后缺少）")
        if not (self._当前().token_type == IDENTIFIER and self._当前().值 == "如下"):
            raise 语法错误("定义参数后缺少「如下」", self._当前().位置)
        self._吃()
        self._期望(COLON, 错误消息="「如下」后缺少：")
        旧上下文 = self._在定义内
        self._在定义内 = True
        # 定义体：收集多句体（当不是嵌套定义时，句号作为体分隔符不断消费）
        体: list = []
        while True:
            部分体 = self._解析动作直到(在定义体=True)
            if 部分体:
                体.extend(部分体)
            # 句号是体分句边界：消费句号并继续收集
            # 仅当从顶层调用且后续语句是有效体语句时继续
            if self._当前().token_type == PERIOD:
                if not 旧上下文:
                    self._吃()  # 消费句号，继续
                    # 检查是否遇到新的顶层语句（入口、接口、定义等）
                    if self._当前().token_type in (K_ENTRY, K_INTERFACE, K_DEFINE, K_SETUP, K_SET, K_IMPORT, K_FROM):
                        break
                    continue
                break  # 嵌套定义：句号终止体
            break
        self._在定义内 = 旧上下文
        return 函数定义(名称=名称, 参数=参数, 体=体, 参数默认值=参数默认值, 单表达式=False, 位置=位置)

    def _解析类别方法定义(self, 类别名: str, 位置: 源码位置) -> 类别方法定义:
        """v0.0.9: 解析 定义甲类别的乙（参数）如下：。"""
        self._期望(K_DE, 错误消息="类别名后缺少「的」")
        # 读取方法名（允许以关键词开头，如 显示状态、设置名称）
        方法名 = ""
        if self._当前().token_type in (IDENTIFIER, OP_ADD, OP_SUB, K_PRINT, K_SET, K_SETUP):
            方法名 = self._吃().值
        else:
            self._期望(IDENTIFIER, 错误消息="「的」后缺少方法名")
        while self._当前().token_type in (IDENTIFIER, OP_ADD, OP_SUB, OP_MOD):
            方法名 += self._吃().值
        self._期望(PAREN_OPEN, 错误消息="方法名后缺少（")
        参数, 参数默认值 = self._解析参数列表()
        self._期望(PAREN_CLOSE, 错误消息="方法参数后缺少）")
        if not (self._当前().token_type == IDENTIFIER and self._当前().值 == "如下"):
            raise 语法错误("方法参数后缺少「如下」", self._当前().位置)
        self._吃()
        self._期望(COLON, 错误消息="「如下」后缺少：")
        旧上下文 = self._在定义内
        self._在定义内 = True
        体: list = []
        while True:
            部分体 = self._解析动作直到(在定义体=True)
            if 部分体:
                体.extend(部分体)
            if self._当前().token_type == PERIOD:
                if not 旧上下文:
                    self._吃()
                    if self._当前().token_type in (K_DEFINE, K_SETUP, K_SET, K_ENTRY, K_INTERFACE):
                        break
                    continue
                break
            break
        self._在定义内 = 旧上下文
        return 类别方法定义(类别名=类别名, 名称=方法名, 参数=参数, 参数默认值=参数默认值, 体=体, 位置=位置)

    def _解析设置(self, 位置: 源码位置):
        名称令牌 = self._期望(IDENTIFIER, 错误消息="「设置」后缺少名称")
        名称 = 名称令牌.值
        if self._匹配(K_CATEGORY):
            return self._解析类别声明(名称, 位置)
        elif self._匹配(K_AS):
            return 绑定(名称=名称, 值=self._解析表达式(), 位置=位置)
        else:
            raise 语法错误("「设置」后缺少「类别」或「为」", self._当前().位置)

    def _解析类别声明(self, 名称: str, 位置: 源码位置):
        self._跳过逗号()
        if self._匹配(K_INCLUDE_LONG):
            self._期望(COLON, 错误消息="「包括以下内容」后缺少：")
        elif self._匹配(K_INCLUDE):
            if self._当前().token_type == IDENTIFIER and self._当前().值 == "以下内容":
                self._吃()
                self._期望(COLON, 错误消息="「包括以下内容」后缺少：")
        else:
            raise 语法错误("类别声明后缺少「包括」", self._当前().位置)
        字段列表: list = []
        while self._当前().token_type not in (PERIOD, EOF):
            if self._当前().token_type in (COMMA, DUN_HAO, SEMICOLON):
                self._吃()
                continue
            字段 = self._解析类别字段()
            if 字段:
                字段列表.append(字段)
        # 语义检查：拒绝重复字段名
        字段名集合 = set()
        for f in 字段列表:
            if f.名称 in 字段名集合:
                raise 语法错误(f"类别「{名称}」包含重复字段「{f.名称}」")
            字段名集合.add(f.名称)
        return 类别声明(名称=名称, 字段列表=字段列表, 位置=位置)

    def _解析类别字段(self) -> 类别字段 | None:
        if self._当前().token_type == IDENTIFIER:
            名称令牌 = self._吃()
            名称 = 名称令牌.值
            字段位置 = 名称令牌.位置
            类型 = None
            默认值 = None
            可空 = False
            不得为负 = False
            # 约束循环：处理分隔符（逗号、顿号、且）和约束关键字
            while True:
                if self._当前().token_type in (PERIOD, SEMICOLON, COLON):
                    break
                if self._当前().token_type == OP_AND:
                    self._吃()  # 且
                    continue
                if self._匹配(COMMA, DUN_HAO):
                    continue
                # 如果不是约束关键字，退出
                if self._当前().token_type not in (K_MUST, K_MUST_NOT, K_CAN, K_SET, K_WITH, K_DEFAULT_AS) and not (
                    self._当前().token_type == IDENTIFIER and self._当前().值 in ("默认", "可以")):
                    break
                # 约束：须为文本/整数
                if self._匹配(K_MUST):
                    if self._匹配(K_AS):
                        if self._当前().token_type == IDENTIFIER:
                            类型名 = self._吃().值
                            if 类型名 == "文本":
                                if 类型 is not None and 类型 != "str":
                                    raise 语法错误(f"字段「{名称}」约束冲突：不能同时要求为多种类型", 字段位置)
                                类型 = "str"
                            elif 类型名 == "整数":
                                if 类型 is not None and 类型 != "int":
                                    raise 语法错误(f"字段「{名称}」约束冲突：不能同时要求为多种类型", 字段位置)
                                类型 = "int"
                    continue
                # 约束：不得为负 / 不得变为负
                if self._匹配(K_MUST_NOT):
                    if self._匹配(K_BECOME, K_AS):
                        # 不得为负 或 不得变为负
                        if self._当前().token_type == IDENTIFIER and self._当前().值 == "负":
                            self._吃()
                            不得为负 = True
                    continue
                # 约束：默认为【值】
                if self._匹配(K_DEFAULT_AS):
                    默认值 = self._解析表达式()
                    continue
                if self._当前().token_type == IDENTIFIER and self._当前().值 == "默认":
                    self._吃()
                    if self._匹配(K_AS):
                        默认值 = self._解析表达式()
                    continue
                # 约束：可以没有值（软关键词"可以" + "没有值"）
                if self._匹配(K_CAN):
                    if self._匹配(K_NONE):
                        可空 = True
                    continue
                # 未知约束，跳过
                self._吃()
            return 类别字段(名称=名称, 类型=类型, 默认值=默认值, 可空=可空, 不得为负=不得为负)
        if self._当前().token_type not in (PERIOD, EOF):
            self._吃()
        return None

    # ==================== 第二批：断言 / 删除 / 报错 ====================

    def _解析断言(self, 主体: "表达式 | None" = None, 位置: 源码位置 | None = None):
        if 主体:
            算子类型 = self._吃().token_type
            tok = self._当前()
            if tok.token_type in (OP_GT, OP_LT, OP_GE, OP_LE, OP_EQ, OP_NE):
                算符映射 = {OP_GT: ">", OP_LT: "<", OP_GE: ">=", OP_LE: "<=", OP_EQ: "==", OP_NE: "!="}
                算符名 = 算符映射.get(tok.token_type, ">")
                self._吃()
                右 = self._解析表达式()
                expr = 二元运算(主体, 算符名, 右)
            elif tok.token_type in (OP_IN, OP_NOT_IN):
                self._吃()
                右 = self._解析表达式()
                op = "in" if tok.token_type == OP_IN else "not_in"
                expr = 二元运算(主体, op, 右)
                if self._当前().token_type == K_IN: self._吃()
            elif tok.token_type == K_NONE:
                self._吃()
                expr = 二元运算(主体, "is", 空值())
            elif tok.token_type == K_AS:
                self._吃()
                if self._当前().token_type == IDENTIFIER and self._当前().值 == "负":
                    self._吃()
                    expr = 二元运算(主体, "<", 整数(0))
                else:
                    expr = 主体
            else:
                expr = 主体
            if 算子类型 == K_MUST_NOT:
                expr = 一元运算("not", expr)
        else:
            expr = self._解析条件()
        消息 = None
        if self._匹配(COMMA):
            if self._匹配(K_ELSE_ERROR):
                消息令牌 = self._期望(STRING, 错误消息="「否则报错」后缺少【说明】")
                消息 = 消息令牌.值
        return 断言(表达式=expr, 消息=消息, 位置=位置)

    def _解析删除(self, 位置: 源码位置):
        """删去 名称 | 成员 | 项目。"""
        # 解析左值：标识符 + 可选后缀链
        名称令牌 = self._期望(IDENTIFIER, 错误消息="「删去」后缺少名称")
        left = 变量(名称令牌.值, 位置=位置)
        target = self._解析后缀链(left)
        return 删除(目标=target, 位置=位置)

    def _解析报错(self, 位置: 源码位置):
        消息令牌 = self._期望(STRING, 错误消息="「报错」后缺少【说明】")
        错误类型 = None
        if self._匹配(COMMA):
            tok = self._当前()
            if tok.token_type == IDENTIFIER and tok.值 == "错误类型":
                self._吃()
                if self._当前().token_type == IDENTIFIER and self._当前().值 == "是":
                    self._吃()
                    类型令牌 = self._期望(IDENTIFIER, 错误消息="错误类型后缺少类型名")
                    错误类型 = 类型令牌.值
                    return 报错(消息=消息令牌.值, 错误类型=错误类型, 位置=位置)
            elif tok.token_type == IDENTIFIER and tok.值.startswith("错误类型"):
                # 处理"错误类型是值出错"合并为单个ID的情况
                merged = self._吃().值
                # 提取"错误类型"之后的部分
                rest = merged[4:]  # 去掉"错误类型"
                if rest.startswith("是"):
                    rest = rest[1:]  # 去掉"是"
                if rest:
                    错误类型 = rest
                return 报错(消息=消息令牌.值, 错误类型=错误类型, 位置=位置)
        return 报错(消息=消息令牌.值, 位置=位置)

    def _解析依次给出(self, 位置: 源码位置):
        值 = self._解析表达式()
        return 依次给出(值=值, 位置=位置)

    def _解析等待(self, 位置: 源码位置):
        if self._看().token_type == IDENTIFIER and self._看(1).token_type == PAREN_OPEN:
            函数名 = self._吃().值
            调用节点 = self._解析后缀链(变量(函数名, 位置=位置))
            if self._匹配(K_DONE) or (self._当前().token_type == IDENTIFIER and self._当前().值 == "完成"):
                if self._当前().token_type == IDENTIFIER: self._吃()
                if self._匹配(COMMA):
                    if self._当前().token_type == IDENTIFIER and self._当前().值 == "记作":
                        self._吃()
                        name_tok = self._期望(IDENTIFIER, 错误消息="「记作」后缺少名称")
                        return 等待语句(调用=调用节点, 记作名=name_tok.值, 位置=位置)
                return 等待语句(调用=调用节点, 位置=位置)
            elif self._匹配(K_OF_RESULT):
                return 等待表达式(调用=调用节点, 位置=位置)
            else:
                raise 语法错误("「等待」后缺少「完成」或「的所得」", self._当前().位置)
        else:
            raise 语法错误("「等待」后缺少函数调用", self._当前().位置)

    def _解析作用域声明(self, 位置: 源码位置):
        名称列表: list = []
        if self._当前().token_type == IDENTIFIER:
            名称列表.append(self._吃().值)
            while self._匹配(COMMA, DUN_HAO):
                if self._当前().token_type == IDENTIFIER:
                    名称列表.append(self._吃().值)
                else:
                    break
        self._跳过逗号()
        if self._匹配(K_GLOBAL):
            if self._当前().token_type == IDENTIFIER: self._吃()
            return 全局声明(名称=名称列表, 位置=位置)
        elif self._匹配(K_NONLOCAL):
            if self._当前().token_type == IDENTIFIER: self._吃()
            if not self._在定义内:
                raise 语法错误("「指本定义外层的」只能在定义内使用", 位置)
            return 外层声明(名称=名称列表, 位置=位置)
        else:
            raise 语法错误("作用域声明后缺少「均指全局的」或「指本定义外层的」", self._当前().位置)

    def _解析分情形(self, 位置: 源码位置):
        expr = self._解析表达式()
        self._期望(K_MATCH_CASES, 错误消息="「依」后缺少「分情形」")
        self._期望(COLON, 错误消息="「分情形」后缺少：")
        分支列表: list[tuple[str | None, list]] = []
        已见其余 = False
        已见字面量: set[str] = set()
        while self._当前().token_type not in (PERIOD, EOF):
            if self._当前().token_type == SEMICOLON: self._吃(); continue
            if self._当前().token_type == COMMA: self._吃(); continue
            if self._匹配(K_CASE):
                if 已见其余:
                    raise 语法错误("「其余」分支之后不能再出现「若为」分支", self._当前().位置)
                值节点 = self._解析原子()
                # 拒绝重复字面量
                值key = self._值键(值节点)
                if 值key in 已见字面量:
                    raise 语法错误(f"分情形中包含重复的字面量：{值key}", 值节点.位置)
                已见字面量.add(值key)
                self._期望(COMMA, 错误消息="分支值后缺少逗号")
                self._期望(K_THEN, 错误消息="分支缺少「就」")
                动作 = self._解析动作直到()
                分支列表.append((值节点, 动作))
            elif self._匹配(K_DEFAULT):
                已见其余 = True
                if self._当前().token_type == COMMA:
                    self._吃()
                if self._匹配(K_THEN): pass
                动作 = self._解析动作直到()
                分支列表.append((None, 动作))
            else:
                break
        return 分情形(对象=expr, 分支列表=分支列表, 位置=位置)

    @staticmethod
    def _值键(节点) -> str:
        """为分情形字面量生成唯一可哈希键。"""
        from .ast_nodes import 整数, 小数, 文本, 布尔, 空值
        if isinstance(节点, 整数):
            return f"int:{节点.值}"
        elif isinstance(节点, 小数):
            return f"float:{节点.值}"
        elif isinstance(节点, 文本):
            return f"str:{节点.值}"
        elif isinstance(节点, 布尔):
            return f"bool:{节点.值}"
        elif isinstance(节点, 空值):
            return "none"
        return str(节点)

    # ==================== 条件与表达式 ====================

    def _解析条件(self):
        return self._解析或表达式()

    def _解析或表达式(self):
        left = self._解析且表达式()
        while self._当前().token_type == OP_OR:
            self._吃()
            right = self._解析且表达式()
            left = 二元运算(left, "or", right)
        return left

    def _解析且表达式(self):
        left = self._解析非表达式()
        while self._当前().token_type == OP_AND:
            self._吃()
            right = self._解析非表达式()
            left = 二元运算(left, "and", right)
        return left

    def _解析非表达式(self):
        if self._当前().token_type == OP_NOT:
            位置 = self._吃().位置
            self._期望(PAREN_OPEN, 错误消息="「并非」后缺少（")
            inner = self._解析条件()
            self._期望(PAREN_CLOSE, 错误消息="「并非」括号缺少 ）")
            return 一元运算("not", inner, 位置=位置)
        return self._解析比较表达式()

    _二元映射 = {
        OP_EQ: ("==", 30), OP_NE: ("!=", 30),
        OP_GT: (">", 30), OP_LT: ("<", 30),
        OP_GE: (">=", 30), OP_LE: ("<=", 30),
        SYM_EQ: ("==", 30), SYM_NE: ("!=", 30),
        SYM_GT: (">", 30), SYM_LT: ("<", 30),
        SYM_GE: (">=", 30), SYM_LE: ("<=", 30),
        OP_ADD: ("+", 40), OP_SUB: ("-", 40),
        SYM_ADD: ("+", 40), SYM_SUB: ("-", 40),
        OP_MUL: ("*", 50), OP_DIV: ("/", 50),
        OP_FLOOR_DIV: ("//", 50), OP_MOD: ("%", 50),
        SYM_MUL: ("*", 50), SYM_DIV: ("/", 50),
        SYM_FLOOR_DIV: ("//", 50), SYM_MOD: ("%", 50),
        OP_IN: ("in", 30), OP_NOT_IN: ("not_in", 30),
    }

    def _解析表达式(self):
        return self._解析比较表达式()

    def _解析比较表达式(self):
        left = self._解析成员表达式()
        if self._当前().token_type in self._二元映射:
            算符名, _ = self._二元映射[self._当前().token_type]
            op_tok = self._吃()
            right = self._解析成员表达式()
            left = 二元运算(left, 算符名, right, 表层算符=op_tok.原文)
            if op_tok.token_type in (OP_IN, OP_NOT_IN) and self._当前().token_type == K_IN:
                self._吃()
        if self._当前().token_type == K_IS:
            self._吃()
            right = self._解析成员表达式()
            left = 身份判断(left, right, 肯定=True)
        elif self._当前().token_type == K_IS_NOT:
            self._吃()
            right = self._解析成员表达式()
            if self._当前().token_type == K_SELF: self._吃()
            left = 身份判断(left, right, 肯定=False)
        if self._当前().token_type == K_NONE:
            self._吃()
            left = 二元运算(left, "is", 空值())
        if self._当前().token_type == K_TRUE_STATE:
            self._吃()
        elif self._当前().token_type == K_FALSE_STATE:
            self._吃()
            left = 一元运算("not", left)
        return left

    def _解析成员表达式(self):
        left = self._解析加性表达式()
        if self._当前().token_type in (OP_IN, OP_NOT_IN):
            op_tok = self._吃()
            right = self._解析加性表达式()
            op = "in" if op_tok.token_type == OP_IN else "not_in"
            left = 二元运算(left, op, right)
            if self._当前().token_type == K_IN: self._吃()
        return left

    def _解析加性表达式(self):
        left = self._解析乘性表达式()
        while self._当前().token_type in (OP_ADD, SYM_ADD, OP_SUB, SYM_SUB):
            当前 = self._吃()
            算符名, _ = self._二元映射[当前.token_type]
            right = self._解析乘性表达式()
            left = 二元运算(left, 算符名, right, 表层算符=当前.原文)
        return left

    def _解析乘性表达式(self):
        left = self._解析前缀表达式()
        while self._当前().token_type in (OP_MUL, SYM_MUL, OP_DIV, SYM_DIV,
                                          OP_FLOOR_DIV, SYM_FLOOR_DIV, OP_MOD, SYM_MOD):
            当前 = self._吃()
            算符名, _ = self._二元映射[当前.token_type]
            right = self._解析前缀表达式()
            left = 二元运算(left, 算符名, right, 表层算符=当前.原文)
        return left

    def _解析前缀表达式(self):
        token = self._当前()
        if token.token_type == SYM_SUB:
            # 符号一元负号
            self._吃()
            right = self._解析幂表达式()  # -2**2 → -(2**2)
            return 一元运算("-", right, 表层算符="-")
        elif token.token_type == WORD_NEG:
            # 汉语一元负号（负紧邻数字）
            self._吃()
            right = self._解析幂表达式()  # 负2**2 → -(2**2)
            return 一元运算("-", right, 表层算符="负")
        return self._解析幂表达式()

    def _解析幂表达式(self):
        """幂运算（**），右结合，独立于普通二元映射。"""
        left = self._解析后缀起始()
        if self._当前().token_type == SYM_POW:
            self._吃()
            # 右操作数走前缀表达式：2 ** -2 → 2**(-2)，右结合：a**b**c → a**(b**c)
            right = self._解析前缀表达式()
            return 二元运算(left, "**", right, 表层算符="**")
        return left

    def _解析后缀起始(self):
        """解析原子 + 后缀操作链。"""
        if self._当前().token_type == K_ITS:
            return self._解析上下文物件()
        left = self._解析原子()
        return self._解析后缀链(left)

    def _解析上下文物件(self):
        """解析其姓名、其地址的城市等结构焦点访问。"""
        位置 = self._吃().位置  # 消费 其
        首成员 = self._期望(IDENTIFIER, 错误消息="「其」后缺少成员名称").值
        后续 = []
        while self._当前().token_type == K_DE:
            self._吃()
            if self._当前().token_type == IDENTIFIER:
                后续.append(self._吃().值)
            else:
                raise 语法错误("「其」的成员链「的」后缺少成员名", self._当前().位置)
        return 上下文成员访问(上下文种类="ITEM_FOCUS", 首成员=首成员,
                               后续访问=后续, 位置=位置)

    def _解析后缀链(self, left):
        """解析后缀操作链（成员访问、下标、函数调用）并应用到 left。"""
        while True:
            tok = self._当前()
            if tok.token_type == K_DE:
                # 的 → 成员访问（最高优先级）
                self._吃()
                # 收集成员名（允许以关键词开头）
                成员名 = ""
                if self._当前().token_type == IDENTIFIER:
                    成员名 = self._吃().值
                elif self._当前().token_type in (OP_ADD, OP_SUB, OP_MOD, K_PRINT, K_SET, K_SETUP, K_DEFINE):
                    成员名 = self._吃().值
                    # 仅当以关键词开头时才继续收集（如 显示+状态 → 显示状态）
                    while self._当前().token_type in (IDENTIFIER, OP_ADD, OP_SUB):
                        成员名 += self._吃().值
                else:
                    self._期望(IDENTIFIER, 错误消息="「的」后缺少成员名")
                # 处理被关键字边界拆分的复合成员名（仅当成员名为单字时，如 增 + 加 → 增加）
                if len(成员名) == 1 and ord(成员名) >= 0x4e00:
                    while self._当前().token_type in (OP_ADD, OP_SUB):
                        后半 = self._吃().值
                        成员名 += 后半
                left = 成员访问(对象=left, 成员=成员名, 位置=left.位置)
            elif tok.token_type == STRING:
                # 【内容】在表达式之后 → 字符串键下标
                key = self._吃().值
                left = 字符串下标(对象=left, 键=key, 位置=left.位置)
            elif tok.token_type == LIST_OPEN:
                # ［表达式］ → 表达式下标
                left = self._解析表达式下标(left)
            elif tok.token_type == PAREN_OPEN:
                # （参数）→ 函数调用
                left = self._解析调用后缀(left)
            else:
                break
        return left

    def _解析调用后缀(self, 函数表达式):
        """解析函数调用后缀：（参数）。v0.0.8: 支持制定参数。"""
        位置 = self._当前().位置
        self._吃()  # 消耗（
        参数: list = []
        制定参数: list[tuple[str, "表达式"]] = []
        if self._当前().token_type != PAREN_CLOSE:
            # 检测是否为制定参数（IDENTIFIER K_AS）
            if (self._当前().token_type == IDENTIFIER
                    and self._看(1).token_type == K_AS):
                name_tok = self._吃()  # 名称
                self._吃()  # 消耗 K_AS
                制定参数.append((name_tok.值, self._解析表达式()))
            else:
                参数.append(self._解析表达式())
            while self._匹配(COMMA, DUN_HAO):
                if self._当前().token_type == PAREN_CLOSE:
                    break
                if (self._当前().token_type == IDENTIFIER
                        and self._看(1).token_type == K_AS):
                    name_tok = self._吃()  # 名称
                    self._吃()  # 消耗 K_AS
                    制定参数.append((name_tok.值, self._解析表达式()))
                else:
                    参数.append(self._解析表达式())
        self._期望(PAREN_CLOSE, 错误消息="函数调用缺少 ）")
        return 调用(函数=函数表达式, 参数=参数, 制定参数=制定参数, 位置=位置)

    def _解析表达式下标(self, 对象表达式):
        """解析下标后缀：［索引］ 或 ［开始：结束］"""
        位置 = self._当前().位置
        self._吃()  # 消耗［
        # 检测切片模式
        开始 = None
        if self._当前().token_type != COLON and self._当前().token_type != LIST_CLOSE:
            开始 = self._解析表达式()
        if self._当前().token_type == COLON:
            self._吃()  # 消耗：
            结束 = None
            if self._当前().token_type != LIST_CLOSE:
                结束 = self._解析表达式()
            self._期望(LIST_CLOSE, 错误消息="切片下标缺少 ］")
            return 切片下标(对象=对象表达式, 开始=开始, 结束=结束, 位置=位置)
        索引 = 开始
        self._期望(LIST_CLOSE, 错误消息="下标缺少 ］")
        return 表达式下标(对象=对象表达式, 索引=索引, 位置=位置)

    def _解析原子(self):
        位置 = self._当前().位置
        if self._当前().token_type == NUMBER:
            值 = self._吃().值
            return 小数(float(值)) if "." in 值 else 整数(int(值), 位置=位置)
        elif self._当前().token_type == STRING:
            return 文本(self._吃().值, 位置=位置)
        elif self._当前().token_type == LIST_OPEN:
            # 探测映射字面量：［【键】为【值】］（字符串键 + 为）
            if self._看(1).token_type == STRING and self._看(2).token_type == K_AS:
                return self._解析映射(位置)
            return self._解析列表(位置)
        elif self._匹配(LIT_TRUE):
            return 布尔(True, 位置=位置)
        elif self._匹配(LIT_FALSE):
            return 布尔(False, 位置=位置)
        elif self._匹配(K_NONE):
            return 空值(位置=位置)
        elif self._当前().token_type == IDENTIFIER:
            tok = self._吃()  # 获取完整 Token
            名称 = tok.值
            # 精确名称（来自花括号）
            是精确 = tok.是否精确
            if 是精确:
                return 变量(名称, 位置=位置, 名称来源="EXACT")
            if 名称 == "映射" and self._当前().token_type == LIST_OPEN:
                return self._解析映射(位置)
            if 名称 == "固定序列" and self._当前().token_type == LIST_OPEN:
                self._吃(); elts = []
                if self._当前().token_type != LIST_CLOSE:
                    elts.append(self._解析表达式())
                    while self._匹配(DUN_HAO, COMMA):
                        if self._当前().token_type == LIST_CLOSE: break
                        elts.append(self._解析表达式())
                self._期望(LIST_CLOSE)
                return 元组字面量(元素=elts, 位置=位置)
            if 名称 == "集合" and self._当前().token_type == LIST_OPEN:
                self._吃(); elts = []
                if self._当前().token_type != LIST_CLOSE:
                    elts.append(self._解析表达式())
                    while self._匹配(DUN_HAO, COMMA):
                        if self._当前().token_type == LIST_CLOSE: break
                        elts.append(self._解析表达式())
                self._期望(LIST_CLOSE)
                return 集合字面量(元素=elts, 位置=位置)
            if 名称 == "错误" and self._在异常内:
                return 当前错误(位置=位置)
            if 名称 == "错误内容" and self._在异常内:
                return 错误文本(位置=位置)
            if 名称 in ("错误", "错误内容") and not self._在异常内:
                raise 语法错误(f"「{名称}」只能在如果出错的范围内使用", 位置)
            return 变量(名称, 位置=位置, 名称来源="ORDINARY")
        elif self._当前().token_type in (OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD):
            # 运算符字符作为标识符使用（如函数名"加倍"）
            tok = self._吃()
            名称 = tok.值
            while self._当前().token_type in (IDENTIFIER, OP_ADD, OP_SUB):
                名称 += self._吃().值
            return 变量(名称, 位置=位置, 名称来源="ORDINARY")
        elif self._当前().token_type == K_AWAIT:
            if not self._在定义内:
                raise 语法错误("「等待」表达式只能在定义内使用", 位置)
            self._吃()
            名称令牌 = self._期望(IDENTIFIER, 错误消息="「等待」后缺少函数名")
            调用节点 = self._解析后缀链(变量(名称令牌.值, 位置=位置))
            if self._匹配(K_OF_RESULT):
                return 等待表达式(调用=调用节点, 位置=位置)
            raise 语法错误("「等待」表达式需要「的所得」在末尾", 位置)
        elif self._当前().token_type == PAREN_OPEN:
            self._吃()
            expr = self._解析表达式()
            self._期望(PAREN_CLOSE, 错误消息="表达式括号缺少 ）")
            return expr
        else:
            raise 语法错误(f"期望表达式，实际得到 {self._当前().token_type}({self._当前().值!r})", 位置)

    def _解析列表(self, 位置: 源码位置):
        self._吃()
        元素: list = []
        if self._当前().token_type != LIST_CLOSE:
            元素.append(self._解析表达式())
            while self._匹配(DUN_HAO, COMMA):
                if self._当前().token_type == LIST_CLOSE: break
                元素.append(self._解析表达式())
        self._期望(LIST_CLOSE, 错误消息="列表缺少］")
        return 列表字面量(元素=元素, 位置=位置)

    def _解析映射(self, 位置: 源码位置):
        """解析映射字面量：［【键】为【值】、…］"""
        self._吃()  # 消耗［
        条目: list[tuple] = []
        while self._当前().token_type != LIST_CLOSE:
            键 = self._解析表达式()
            self._期望(K_AS, 错误消息="映射项缺少「为」")
            值 = self._解析表达式()
            条目.append((键, 值))
            self._匹配(COMMA, DUN_HAO)
        self._期望(LIST_CLOSE, 错误消息="映射缺少］")
        return 映射字面量(条目=条目, 位置=位置)

    def _解析调用(self, 函数名: str, 位置: 源码位置):
        self._吃()
        参数: list = []
        if self._当前().token_type != PAREN_CLOSE:
            参数.append(self._解析表达式())
            while self._匹配(COMMA, DUN_HAO):
                if self._当前().token_type == PAREN_CLOSE: break
                参数.append(self._解析表达式())
        self._期望(PAREN_CLOSE, 错误消息="函数调用缺少 ）")
        return 调用(函数=变量(函数名), 参数=参数, 位置=位置)
