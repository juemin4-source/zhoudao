"""周道：词法分析器（Lexer / Scanner）。

使用字符级扫描 + 最长关键字优先匹配。
不依赖正则替换，正确处理关键字与标识符的边界。
"""

from .errors import 源码位置, 词法错误
from .tokens import Token, KW_MAP, KW_SORTED, SourceSpan
from .tokens import NUMBER, STRING, IDENTIFIER, COMMENT
from .tokens import LIST_OPEN, LIST_CLOSE, MODULE_OPEN, MODULE_CLOSE
from .tokens import PAREN_OPEN, PAREN_CLOSE, COMMA, DUN_HAO, PERIOD, COLON, SEMICOLON, EOF
from .tokens import (
    OP_SUB, OP_ADD, OP_MUL, OP_DIV,
    SYM_ADD, SYM_SUB, SYM_MUL, SYM_DIV, SYM_POW,
    SYM_FLOOR_DIV, SYM_MOD,
    SYM_EQ, SYM_NE, SYM_GT, SYM_LT, SYM_GE, SYM_LE,
    WORD_NEG,
)


# 单字标点映射
_标点 = {
    "【": STRING,
    "［": LIST_OPEN, "］": LIST_CLOSE,
    "《": MODULE_OPEN, "》": MODULE_CLOSE,
    "（": PAREN_OPEN, "）": PAREN_CLOSE,
    "，": COMMA, "、": DUN_HAO, "。": PERIOD,
    "：": COLON, "；": SEMICOLON,
    ",": COMMA, ".": PERIOD, ";": SEMICOLON, ":": COLON,
    "(": PAREN_OPEN, ")": PAREN_CLOSE,
    "[": LIST_OPEN, "]": LIST_CLOSE,
}


def 扫描(源码: str) -> list[Token]:
    """将周道源码扫描为 Token 列表。"""
    tokens: list[Token] = []
    长度 = len(源码)
    i = 0
    行 = 1
    列 = 1
    _有空白 = False  # 前导空白标记：当前 Token 前是否有空白

    def _添加(token_type, 值="", 位置=None, **kw):
        """添加 Token 并传递前导空白标记。"""
        nonlocal _有空白
        tokens.append(Token(token_type=token_type, 值=值, 位置=位置,
                            前导空白=_有空白, **kw))
        _有空白 = False

    while i < 长度:
        ch = 源码[i]
        位置 = 源码位置(行=行, 列=列, 索引=i)

        # 跳过空白
        if ch.isspace():
            _有空白 = True
            if ch == "\n":
                行 += 1
                列 = 1
            else:
                列 += 1
            i += 1
            continue

        # 数字
        if ch.isdigit():
            start = i
            i += 1
            while i < 长度 and 源码[i].isdigit():
                i += 1
            if i < 长度 and 源码[i] == "." and i + 1 < 长度 and 源码[i + 1].isdigit():
                i += 1  # 跳过 .
                while i < 长度 and 源码[i].isdigit():
                    i += 1
            文本 = 源码[start:i]
            _添加(token_type=NUMBER, 值=文本, 位置=位置)
            列 += (i - start)
            continue

        # 文本字面量 【…】支持 】】 转义为字面 】  \n 转义为换行
        if ch == "【":
            开始 = i
            i += 1
            片段: list[str] = []
            while i < 长度:
                if 源码[i] == "】":
                    if i + 1 < 长度 and 源码[i + 1] == "】":
                        片段.append("】")
                        i += 2
                    else:
                        i += 1  # 跳过结束 】
                        break
                elif 源码[i] == "\\" and i + 1 < 长度:
                    if 源码[i + 1] == "n":
                        片段.append("\n")
                        i += 2
                    elif 源码[i + 1] == "\\":
                        片段.append("\\")
                        i += 2
                    else:
                        片段.append(源码[i])
                        i += 1
                else:
                    if 源码[i] == "\n":
                        行 += 1
                    片段.append(源码[i])
                    i += 1
            else:
                i = 开始 + 1  # 未闭合，回到起始
            文本 = "".join(片段)
            _添加(token_type=STRING, 值=文本, 位置=位置)
            列 += (i - 开始)
            continue

        # 精确名称 {name} / ｛name｝ — 内部整体形成单一标识符
        if ch in ("{", "｛"):
            开始 = i
            close_char = "}" if ch == "{" else "｝"
            i += 1
            # 拒绝空名称
            if i < 长度 and 源码[i] == close_char:
                raise 词法错误("精确名称不能为空", 位置)
            while i < 长度 and 源码[i] != close_char:
                if 源码[i] == "\n":
                    raise 词法错误("精确名称不能跨行", 位置)
                if 源码[i] in ("{", "}", "｛", "｝"):
                    raise 词法错误("精确名称内不允许嵌套花括号", 位置)
                i += 1
            if i >= 长度:
                raise 词法错误("精确名称缺少闭合花括号", 位置)
            i += 1  # 跳过闭合花括号
            文本 = 源码[开始 + 1:i - 1]
            _添加(token_type=IDENTIFIER, 值=文本, 位置=位置, 是否精确=True)
            列 += (i - 开始)
            continue

        # 多字关键字（最长匹配优先）
        matched_keyword = None
        for kw in KW_SORTED:
            if 源码[i:i + len(kw)] == kw:
                matched_keyword = kw
                break

        if matched_keyword:
            token_type = KW_MAP[matched_keyword]
            _添加(token_type=token_type, 值=matched_keyword, 位置=位置)
            i += len(matched_keyword)
            列 += len(matched_keyword)
            continue

        # 注释：注：从当前位置到行末（仅在有效边界处触发）
        if ch == "注" and 源码[i:i+2] == "注：":
            # 跳过前置空白后检查是否为注释边界
            pos = i
            while pos > 0 and 源码[pos-1] in " 	":
                pos -= 1
            if pos == 0 or 源码[pos-1] in "\n。；：，,":
                start = i
                while i < 长度 and 源码[i] != "\n":
                    i += 1
                文本 = 源码[start:i]
                _添加(token_type=COMMENT, 值=文本, 位置=位置)
                列 += len(文本)
                continue

        # 单字标点
        if ch in _标点:
            token_type = _标点[ch]
            _添加(token_type=token_type, 值=ch, 位置=位置)
            i += 1
            列 += 1
            if ch == "\n":
                行 += 1
                列 = 1
            continue

        # ===== ASCII 符号运算符 =====
        # 多字符优先（按长度降序）
        _多字符符号 = {
            "**": SYM_POW,
            "//": SYM_FLOOR_DIV,
            "!=": SYM_NE,
            "<=": SYM_LE,
            ">=": SYM_GE,
        }
        # == 单独处理 → 专用诊断（不是兼容语法）
        if ch == "=" and i + 1 < 长度 and 源码[i + 1] == "=":
            raise 词法错误("周道使用「=」或「等于」判断相等。", 位置)
        if i + 1 < 长度:
            two_ch = 源码[i:i+2]
            if two_ch in _多字符符号:
                tok_type = _多字符符号[two_ch]
                _添加(token_type=tok_type, 原文=two_ch, 语义值=two_ch,
                      跨度=SourceSpan(行, 列, 2))
                i += 2; 列 += 2
                continue

        # 单字符符号
        _单字符符号 = {
            '+': SYM_ADD, '-': SYM_SUB, '*': SYM_MUL, '/': SYM_DIV,
            '%': SYM_MOD, '=': SYM_EQ,
            '<': SYM_LT, '>': SYM_GT,
        }
        if ch in _单字符符号:
            tok_type = _单字符符号[ch]
            _添加(token_type=tok_type, 原文=ch, 语义值=ch,
                  跨度=SourceSpan(行, 列, 1))
            i += 1; 列 += 1
            continue

        # 汉语一元负号：负 紧邻数字 → WORD_NEG（不是 OP_SUB）
        if ch == "负" and i + 1 < 长度 and 源码[i + 1].isdigit():
            _添加(token_type=WORD_NEG, 原文="负", 语义值="-",
                  跨度=SourceSpan(行, 列, 1))
            i += 1
            列 += 1
            continue

        # 标识符（逐字扫描，遇到关键字边界自动断开）
        if (ord(ch) >= 0x4e00 and ch.isalpha()) or (ch.isascii() and (ch.isalpha() or ch == "_")):
            start = i
            buffer_start = i
            i += 1
            while i < 长度:
                c = 源码[i]
                # 先检查当前位置是否开始关键字
                kw_match = None
                for kw in KW_SORTED:
                    if 源码[i:i + len(kw)] == kw:
                        kw_match = kw
                        break
                if kw_match:
                    break  # 关键字边界，标识符结束
                # 继续向下兼容：中文或英文数字
                if (ord(c) >= 0x4e00 and c.isalpha()) or (c.isascii() and (c.isalnum() or c == "_")):
                    i += 1
                else:
                    break
            文本 = 源码[buffer_start:i]
            _添加(token_type=IDENTIFIER, 值=文本, 位置=位置)
            列 += (i - buffer_start)
            continue

        # 无法识别
        raise 词法错误(f"无法识别的字符：{ch!r}", 位置)

    _添加(token_type=EOF, 值="", 位置=源码位置(行=行, 列=列, 索引=长度))
    return tokens
