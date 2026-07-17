#!/usr/bin/env python3
"""周道表层语法总索引 — 自动重新提取。"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from 周道.tokens import KW_MAP, KW_SORTED
from 周道 import ast_nodes as AST

keywords = [(kw, KW_MAP[kw]) for kw in KW_SORTED]

stmt_types = []
expr_types = []
for name in dir(AST):
    cls = getattr(AST, name)
    if not isinstance(cls, type):
        continue
    if cls in (AST.节点, AST.语句, AST.表达式):
        continue
    if issubclass(cls, AST.语句):
        stmt_types.append(name)
    elif issubclass(cls, AST.表达式):
        expr_types.append(name)

lines = []
lines.append("# 周道表层语法总索引")
lines.append("")
lines.append("> 版本：0.0.10.5")
lines.append(f"> 关键词总数：{len(keywords)}")
lines.append("> 生成方式：自动提取（010.5 终态）")
lines.append("")
lines.append("---")
lines.append("")

cats = [
    ("结构声明（18）", ["设","使","为","变为","成立","不成立","没有值","定义","设置","类别","包括","包括以下内容","规定模块接口","运行如下","下文所用","均指全局的","指本定义外层的"]),
    ("控制流（12）", ["如果","就","不然","当","一直","从","中","每取一项记作","跳出循环","继续下一轮","依","分情形","若为","其余"]),
    ("错误处理（5）", ["尝试","如果出错","无论是否出错","最后","原样报出当前错误"]),
    ("函数与生成（5）", ["以","所得","为所得","依次给出"]),
    ("等待与异步（4）", ["等待","完成","的所得","每等到一项记作"]),
    ("模块（4）", ["引入","下文简称","默认为"]),
    ("运算符（18）", ["加","减","乘","除","整除","余","等于","不等于","大于","小于","不少于","不多于","大于等于","小于等于","且","或","并非","在","不在","的"]),
    ("字面量（4）", ["真","假","就是","不是","本身"]),
    ("其他（8）", ["显示","须","不得","否则报错","删去","可以","不作处理","报错","并","其"]),
]

kw_map = {kw: tok for kw, tok in keywords}
for title, words in cats:
    lines.append(f"### {title}")
    lines.append("")
    lines.append("| 关键词 | Token | 首次版本 |")
    lines.append("|--------|-------|---------|")
    items = [(w, kw_map[w]) for w in words if w in kw_map]
    for w, tok in sorted(items, key=lambda x: (-len(x[0]), x[0])):
        lines.append(f"| `{w}` | {tok} | 010 |")
    lines.append("")

# Symbol operators
lines.append("## 二、符号运算符")
lines.append("")
lines.append("| 符号 | Token | 语义 | 版本 |")
lines.append("|------|-------|------|------|")
for sym, tok, desc, ver in [
    ("+", "SYM_ADD", "加法", "010.5"),
    ("-", "SYM_SUB", "减法/一元负号", "010.5"),
    ("*", "SYM_MUL", "乘法", "010.5"),
    ("/", "SYM_DIV", "除法", "010.5"),
    ("**", "SYM_POW", "幂（右结合）", "010.5"),
    ("//", "SYM_FLOOR_DIV", "向下取整除法", "010.5"),
    ("%", "SYM_MOD", "模运算", "010.5"),
    ("=", "SYM_EQ", "相等", "010.5"),
    ("!=", "SYM_NE", "不等", "010.5"),
    (">", "SYM_GT", "大于", "010.5"),
    ("<", "SYM_LT", "小于", "010.5"),
    (">=", "SYM_GE", "大于等于", "010.5"),
    ("<=", "SYM_LE", "小于等于", "010.5"),
]:
    lines.append(f"| `{sym}` | {tok} | {desc} | {tok[4:]}.{tok[-1]} |")
lines.append("")

# Contextual keywords
lines.append("## 三、上下文关键字")
lines.append("")
lines.append("| 关键字 | 上下文 | 含义 |")
lines.append("|--------|--------|------|")
for kw, ctx, meaning in [
    ("固定序列", "后跟 `[`", "固定序列字面量引导"),
    ("集合", "后跟 `[`", "集合字面量引导"),
    ("映射", "后跟 `[`", "映射字面量引导"),
    ("错误", "异常处理分支中", "当前异常对象"),
    ("错误内容", "异常处理分支中", "当前异常消息"),
    ("自己", "类别实例方法中", "当前实例引用"),
    ("如下", "函数/方法定义后", "定义体引导"),
    ("周道源文件", "引入语句中", "周道模块来源"),
    ("Python", "引入语句中", "Python 模块来源"),
]:
    lines.append(f"| `{kw}` | {ctx} | {meaning} |")
lines.append("")

# Punctuation
lines.append("## 四、标点")
lines.append("")
lines.append("| 符号 | 名称 | 用途 |")
lines.append("|------|------|------|")
for sym, name, usage in [
    ("，", "逗号", "语句/参数分隔"),
    ("。", "句号", "句子结束"),
    ("：", "冒号", "定义体/接口引导"),
    ("；", "分号", "句内语句分隔"),
    ("、", "顿号", "列表/参数内分隔"),
    ("（）", "括号", "参数列表/表达式分组"),
    ("【】", "方头括号", "字符串字面量"),
    ("［］", "空心方括号", "列表/下标"),
    ("《》", "书名号", "模块名"),
    ("{}", "花括号", "精确名称"),
]:
    lines.append(f"| `{sym}` | {name} | {usage} |")
lines.append("")

# Statement types
lines.append("## 五、语句类型（AST 节点）")
lines.append("")
lines.append("| AST 节点 | 描述 | 版本 |")
lines.append("|----------|------|------|")
for name in sorted(stmt_types):
    doc = (getattr(AST, name).__doc__ or "").split("。")[0].split(".")[0]
    lines.append(f"| `{name}` | {doc} | 010 |")
lines.append("")

# Expression types
lines.append("## 六、表达式类型（AST 节点）")
lines.append("")
lines.append("| AST 节点 | 描述 | 版本 |")
lines.append("|----------|------|------|")
for name in sorted(expr_types):
    doc = (getattr(AST, name).__doc__ or "").split("。")[0].split(".")[0]
    lines.append(f"| `{name}` | {doc} | 010 |")
lines.append("")

output = "\n".join(lines)
path = os.path.join(os.path.dirname(__file__), "..", "docs", "SURFACE-GRAMMAR-INDEX.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(output)
print(f"OK, written to {path}")
print(f"Keywords: {len(keywords)}, Statements: {len(stmt_types)}, Expressions: {len(expr_types)}")
