"""周道 — 中文句法式 Python 方言。

统一管线：
  完整：源码 → Lexer → Parser → Surface AST → Lowering → Core IR
        → Semantic Analysis → SemanticProgram → Emitter → Python
  仅语法：源码 → Lexer → Parser → Surface AST → Lowering → Core IR → Emitter → Python

v0.0.9: 新增 PythonAstBackend（正式执行路径）与运行时异常回溯机制。
"""

from .lexer import 扫描
from .parser import 解析器
from .lowering import 降低, 降低器, 降低_仅语法, 降低结果
from .emitter import 发射器
from .ast_backend import PythonAstBackend
from .runner import 转译, 转译_仅语法, 运行, 运行文件
from .core_ir import (
    程序IR,
    语句IR, 赋值IR, 算术赋值IR, 打印IR,
    如果IR, 当循环IR, 遍历IR, 尝试IR,
    跳出IR, 继续IR, 以所得IR, 函数定义IR,
    引入IR, 从中引入IR, 导入别名IR,
    断言IR, 类别声明IR, 类别字段IR,
    删除IR, 空操作IR, 报错IR, 依次给出IR,
    等待语句IR, 全局声明IR, 外层声明IR,
    最终收束IR, 分情形IR, 表达式语句IR,
    表达式IR,
    整数常量IR, 小数常量IR, 文本常量IR,
    布尔常量IR, 空值IR,
    列表字面量IR, 映射字面量IR,
    变量引用IR, 二元运算IR, 一元运算IR, 调用IR,
    身份判断IR, 等待表达式IR, 当前错误IR, 错误文本IR,
    成员访问IR, 字符串下标IR, 表达式下标IR,
    切片下标IR,
)
from .exact_identifier import ExactIdentifier, 标识符提取器
from .nametable import NameTable, 绑定信息
from .name_lattice import NameLattice
from .context_resolver import ContextResolver, 语法位置, 上下文关键字判定
from .ambiguity import 歧义检测器, 歧义种类, 检测结果, 候选解析, 检查无歧义
from .runtime_traceback import 格式化回溯, 包装运行时异常, 提取周道帧, 映射行号
from .diagnostics import 歧义诊断, 重复定义, 未定义名称, 省略歧义
from .semantic_program import SemanticProgram, 语义诊断, 作用域快照
from .semantic_analyzer import 语义分析器, 分析 as 语义分析
from .prelude_scope import (
    全部前置名称, 是否已知名称, 是否内置函数, 是否模块名,
    内置函数, 模块名称,
)

__version__ = "0.0.9"
__all__ = [
    "扫描", "解析器", "降低", "降低器", "降低_仅语法", "降低结果",
    "发射器", "PythonAstBackend",
    "转译", "转译_仅语法", "运行", "运行文件",
    # Core IR 类型
    "程序IR",
    "语句IR", "赋值IR", "算术赋值IR", "打印IR",
    "如果IR", "当循环IR", "遍历IR", "尝试IR",
    "跳出IR", "继续IR", "以所得IR", "函数定义IR",
    "引入IR", "从中引入IR", "导入别名IR",
    "断言IR", "类别声明IR", "类别字段IR",
    "删除IR", "空操作IR", "报错IR", "依次给出IR",
    "等待语句IR", "全局声明IR", "外层声明IR",
    "最终收束IR", "分情形IR", "表达式语句IR",
    "表达式IR",
    "整数常量IR", "小数常量IR", "文本常量IR",
    "布尔常量IR", "空值IR",
    "列表字面量IR", "映射字面量IR",
    "变量引用IR", "二元运算IR", "一元运算IR", "调用IR",
    "身份判断IR", "等待表达式IR", "当前错误IR", "错误文本IR",
    "成员访问IR", "字符串下标IR", "表达式下标IR",
    "切片下标IR",
    # 003 模块
    "ExactIdentifier", "标识符提取器",
    "NameTable", "绑定信息",
    "NameLattice",
    "ContextResolver", "语法位置", "上下文关键字判定",
    "歧义检测器", "歧义种类", "检测结果", "候选解析", "检查无歧义",
    "歧义诊断", "重复定义", "未定义名称", "省略歧义",
    # 006 语义分析
    "SemanticProgram", "语义诊断", "作用域快照",
    "语义分析器", "语义分析",
    "全部前置名称", "是否已知名称", "是否内置函数", "是否模块名",
    "内置函数", "模块名称",
    # 007 运行时回溯
    "格式化回溯", "包装运行时异常", "提取周道帧", "映射行号",
]
