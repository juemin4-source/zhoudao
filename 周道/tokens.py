"""周道：词法单元（Token）类型定义。"""

from dataclasses import dataclass
from .errors import 源码位置


# ==================== Token 类型常量 ====================
# 关键字类型（第一批）
K_SET = "K_SET"
K_MAKE = "K_MAKE"
K_AS = "K_AS"
K_BECOME = "K_BECOME"
K_TRUE_STATE = "K_TRUE_STATE"
K_FALSE_STATE = "K_FALSE_STATE"
K_NONE = "K_NONE"
K_IF = "K_IF"
K_THEN = "K_THEN"
K_ELSE = "K_ELSE"
K_WHILE = "K_WHILE"
K_WHEN = "K_WHEN"
K_ALWAYS = "K_ALWAYS"
K_FROM = "K_FROM"
K_IN = "K_IN"
K_EACH_AS = "K_EACH_AS"
K_BREAK = "K_BREAK"
K_CONTINUE = "K_CONTINUE"
K_TRY = "K_TRY"
K_EXCEPT = "K_EXCEPT"
K_WITH = "K_WITH"
K_RESULT = "K_RESULT"
K_AS_RESULT = "K_AS_RESULT"
K_IMPORT = "K_IMPORT"
K_AND_THEN = "K_AND_THEN"
K_PRINT = "K_PRINT"

# 关键字类型（第二批）
K_DEFINE = "K_DEFINE"             # 定义
K_SETUP = "K_SETUP"               # 设置
K_CATEGORY = "K_CATEGORY"         # 类别
K_INCLUDE = "K_INCLUDE"           # 包括
K_INCLUDE_LONG = "K_INCLUDE_LONG" # 包括以下内容
K_MUST = "K_MUST"                 # 须
K_MUST_NOT = "K_MUST_NOT"         # 不得
K_ELSE_ERROR = "K_ELSE_ERROR"     # 否则报错
K_DELETE = "K_DELETE"             # 删去
K_IS = "K_IS"                     # 就是
K_IS_NOT = "K_IS_NOT"             # 不是
K_SELF = "K_SELF"                 # 本身
K_PASS = "K_PASS"                 # 不作处理
K_RAISE = "K_RAISE"               # 报错
K_YIELD = "K_YIELD"               # 依次给出
K_AWAIT = "K_AWAIT"               # 等待
K_DONE = "K_DONE"                 # 完成
K_OF_RESULT = "K_OF_RESULT"       # 的所得
K_CAN = "K_CAN"                   # 可以
K_FINALLY = "K_FINALLY"           # 无论是否出错
K_FINALLY_DO = "K_FINALLY_DO"     # 最后
K_MATCH = "K_MATCH"               # 依
K_MATCH_CASES = "K_MATCH_CASES"   # 分情形
K_CASE = "K_CASE"                 # 若为
K_DEFAULT = "K_DEFAULT"           # 其余
K_DEFAULT_AS = "K_DEFAULT_AS"     # 默认为（参数默认值）
K_AS_ALIAS = "K_AS_ALIAS"         # 下文简称
K_SCOPE_DECL = "K_SCOPE_DECL"     # 下文所用
K_GLOBAL = "K_GLOBAL"             # 均指全局的
K_NONLOCAL = "K_NONLOCAL"         # 指本定义外层的
K_DE = "K_DE"                     # 的（成员取得运算符）
K_INTERFACE = "K_INTERFACE"       # 规定模块接口（v0.0.8-R1）
K_ENTRY = "K_ENTRY"               # 运行如下（v0.0.8）
K_AWAIT_EACH = "K_AWAIT_EACH"     # 每等到一项记作
K_RERAISE = "K_RERAISE"           # 原样报出当前错误


# 运算符类型
OP_ADD = "OP_ADD"
OP_SUB = "OP_SUB"
OP_MUL = "OP_MUL"
OP_DIV = "OP_DIV"
OP_FLOOR_DIV = "OP_FLOOR_DIV"
OP_MOD = "OP_MOD"
OP_EQ = "OP_EQ"
OP_NE = "OP_NE"
OP_GT = "OP_GT"
OP_LT = "OP_LT"
OP_GE = "OP_GE"
OP_LE = "OP_LE"
OP_AND = "OP_AND"
OP_OR = "OP_OR"
OP_NOT = "OP_NOT"
OP_IN = "OP_IN"
OP_NOT_IN = "OP_NOT_IN"

# 字面量类型
LIT_TRUE = "LIT_TRUE"
LIT_FALSE = "LIT_FALSE"

# 非关键字 Token 类型
NUMBER = "NUMBER"
STRING = "STRING"
IDENTIFIER = "IDENTIFIER"
LIST_OPEN = "LIST_OPEN"
LIST_CLOSE = "LIST_CLOSE"
MODULE_OPEN = "MODULE_OPEN"
MODULE_CLOSE = "MODULE_CLOSE"
PAREN_OPEN = "PAREN_OPEN"
PAREN_CLOSE = "PAREN_CLOSE"
COMMA = "COMMA"
DUN_HAO = "DUN_HAO"
PERIOD = "PERIOD"
COLON = "COLON"           # ：
SEMICOLON = "SEMICOLON"   # ；
EOF = "EOF"


# ==================== 关键字 → 类型名映射表 ====================
KW_MAP = {
    "设": K_SET,
    "使": K_MAKE,
    "为": K_AS,
    "变为": K_BECOME,
    "成立": K_TRUE_STATE,
    "不成立": K_FALSE_STATE,
    "没有值": K_NONE,
    "如果": K_IF,
    "就": K_THEN,
    "不然": K_ELSE,
    "当": K_WHILE,
    "一直": K_ALWAYS,
    "从": K_FROM,
    "中": K_IN,
    "每取一项记作": K_EACH_AS,
    "跳出循环": K_BREAK,
    "继续下一轮": K_CONTINUE,
    "尝试": K_TRY,
    "如果出错": K_EXCEPT,
    "以": K_WITH,
    "所得": K_RESULT,
    "为所得": K_AS_RESULT,
    "引入": K_IMPORT,
    "加": OP_ADD,
    "减": OP_SUB,
    "乘": OP_MUL,
    "除": OP_DIV,
    "整除": OP_FLOOR_DIV,
    "余": OP_MOD,
    "等于": OP_EQ,
    "不等于": OP_NE,
    "大于": OP_GT,
    "小于": OP_LT,
    "不少于": OP_GE,
    "不多于": OP_LE,
    "且": OP_AND,
    "或": OP_OR,
    "并非": OP_NOT,
    "在": OP_IN,
    "不在": OP_NOT_IN,
    "真": LIT_TRUE,
    "假": LIT_FALSE,
    "并": K_AND_THEN,
    "显示": K_PRINT,
    "定义": K_DEFINE,
    # 第二批关键词
    "设置": K_SETUP,
    "类别": K_CATEGORY,
    "包括": K_INCLUDE,
    "包括以下内容": K_INCLUDE_LONG,
    "须": K_MUST,
    "不得": K_MUST_NOT,
    "否则报错": K_ELSE_ERROR,
    "删去": K_DELETE,
    "就是": K_IS,
    "不是": K_IS_NOT,
    "本身": K_SELF,
    "不作处理": K_PASS,
    "报错": K_RAISE,
    "依次给出": K_YIELD,
    "等待": K_AWAIT,
    "的所得": K_OF_RESULT,
    "可以": K_CAN,
    "无论是否出错": K_FINALLY,
    "最后": K_FINALLY_DO,
    "依": K_MATCH,
    "分情形": K_MATCH_CASES,
    "若为": K_CASE,
    "其余": K_DEFAULT,
    "下文简称": K_AS_ALIAS,
    "下文所用": K_SCOPE_DECL,
    "均指全局的": K_GLOBAL,
    "指本定义外层的": K_NONLOCAL,
    "规定模块接口": K_INTERFACE,
    "默认为": K_DEFAULT_AS,
    "运行如下": K_ENTRY,
    "每等到一项记作": K_AWAIT_EACH,
    "原样报出当前错误": K_RERAISE,
    "的": K_DE,
}

# 按长度降序排列的关键字列表（词法层最长匹配）
KW_SORTED = sorted(KW_MAP.keys(), key=len, reverse=True)


@dataclass
class Token:
    token_type: str
    值: str
    位置: 源码位置
    是否精确: bool = False  # IDENTIFIER 是否来自花括号精确名称

    def __repr__(self) -> str:
        后缀 = " (精确)" if self.是否精确 else ""
        return f"Token({self.token_type}, {self.值!r}{后缀}, {self.位置})"
