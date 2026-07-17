"""周道：词法分析器（Lexer / Scanner）。

使用字符级扫描 + 最长关键字优先匹配。
不依赖正则替换，正确处理关键字与标识符的边界。
"""

from .errors import 源码位置, 词法错误
from .tokens import Token, KW_MAP, KW_SORTED
from .tokens import NUMBER, STRING, IDENTIFIER, COMMENT
from .tokens import LIST_OPEN, LIST_CLOSE, MODULE_OPEN, MODULE_CLOSE
from .tokens import PAREN_OPEN, PAREN_CLOSE, COMMA, DUN_HAO, PERIOD, COLON, SEMICOLON, EOF


# 单字标点映射
_标点 = {
    "【": STRING,
    "［": LIST_OPEN, "］": LIST_CLOSE,
    "《": MODULE_OPEN, "》": MODULE_CLOSE,
    "（": PAREN_OPEN, "）": PAREN_CLOSE,
    "，": COMMA, "、": DUN_HAO, "。": PERIOD,
    "：": COLON, "；": SEMICOLON,
}


def 扫描(源码: str) -> list[Token]:
    """将周道源码扫描为 Token 列表。"""
    tokens: list[Token] = []
    长度 = len(源码)
    i = 0
    行 = 1
    列 = 1

    while i < 长度:
        ch = 源码[i]
        位置 = 源码位置(行=行, 列=列, 索引=i)

        # 跳过空白
        if ch.isspace():
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
            tokens.append(Token(token_type=NUMBER, 值=文本, 位置=位置))
            列 += (i - start)
            continue

        # 文本字面量 【…】
        if ch == "【":
            开始 = i
            i += 1
            while i < 长度 and 源码[i] != "】":
                if 源码[i] == "\n":
                    行 += 1
                i += 1
            if i < 长度:
                i += 1  # 跳过 】
            文本 = 源码[开始 + 1:i - 1]  # 去掉【】
            tokens.append(Token(token_type=STRING, 值=文本, 位置=位置))
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
            tokens.append(Token(token_type=IDENTIFIER, 值=文本, 位置=位置, 是否精确=True))
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
            tokens.append(Token(token_type=token_type, 值=matched_keyword, 位置=位置))
            i += len(matched_keyword)
            列 += len(matched_keyword)
            continue

        # 注释：注：从当前位置到行末（仅在有效边界处触发）
        if ch == "注" and 源码[i:i+2] == "注：":
            # 跳过前置空白后检查是否为注释边界
            pos = i
            while pos > 0 and 源码[pos-1] in " 	":
                pos -= 1
            if pos == 0 or 源码[pos-1] in "\n。；：":
                start = i
                while i < 长度 and 源码[i] != "\n":
                    i += 1
                文本 = 源码[start:i]
                tokens.append(Token(token_type=COMMENT, 值=文本, 位置=位置))
                列 += len(文本)
                continue

        # 单字标点
        if ch in _标点:
            if ch == "【":
                # 已在上面的文本字面量处理
                pass
            token_type = _标点[ch]
            # 如果是 【，表示文本开始但未闭合
            # 这里已经预先处理了，不会到达这里
            tokens.append(Token(token_type=token_type, 值=ch, 位置=位置))
            i += 1
            列 += 1
            if ch == "\n":
                行 += 1
                列 = 1
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
            tokens.append(Token(token_type=IDENTIFIER, 值=文本, 位置=位置))
            列 += (i - buffer_start)
            continue

        # 无法识别
        raise 词法错误(f"无法识别的字符：{ch!r}", 位置)

    tokens.append(Token(token_type=EOF, 值="", 位置=源码位置(行=行, 列=列, 索引=长度)))
    return tokens
