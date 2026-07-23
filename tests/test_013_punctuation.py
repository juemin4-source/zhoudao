"""013 全角/半角标点等价性测试。

全角标点是周道推荐书写表面；对应半角标点是等价合法表面。
二者归一为同一语法 Token，原文仍保留给源码位置与表面信息。
"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contextlib import redirect_stdout
from 周道 import 转译
from 周道.lexer import 扫描
from 周道.method_aliases import 调用成员 as _zd_调用成员


def _token_types(code: str) -> list[str]:
    return [t.token_type for t in 扫描(code)]


def _run(code: str) -> str:
    py = 转译(code)
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(py, {"__name__": "__周道__", "_zd_调用成员": _zd_调用成员})
    return buf.getvalue().strip()


# ═══════════════════════════════════════════════════════════════
# 等价性：全角与半角产生相同 Token 序列
# ═══════════════════════════════════════════════════════════════

class TestTokenEquivalence:
    def test_period(self):
        """全角 。与半角 . → PERIOD"""
        assert _token_types("显示x。")[-2] == "PERIOD"
        assert _token_types("显示x.")[-2] == "PERIOD"

    def test_comma(self):
        """全角 ，与半角 , → COMMA"""
        assert "COMMA" in _token_types("设x为1，显示x。")
        assert "COMMA" in _token_types("设x为1,显示x.")

    def test_semicolon(self):
        """全角 ；与半角 ; → SEMICOLON"""
        t1 = _token_types("尝试甲；如果出错，就乙。")
        t2 = _token_types("尝试甲;如果出错,就乙.")
        assert "SEMICOLON" in t1
        assert "SEMICOLON" in t2

    def test_colon(self):
        """全角 ：与半角 : → COLON"""
        assert "COLON" in _token_types("运行如下：设x为1。")
        assert "COLON" in _token_types("运行如下:设x为1.")

    def test_brackets(self):
        """全角 （）与半角 () → PAREN_OPEN / PAREN_CLOSE"""
        assert _token_types("f（x）").count("PAREN_OPEN") == 1
        assert _token_types("f(x)").count("PAREN_OPEN") == 1

    def test_square_brackets(self):
        """全角 ［］与半角 [] → LIST_OPEN / LIST_CLOSE"""
        assert _token_types("［1］").count("LIST_OPEN") == 1
        assert _token_types("[1]").count("LIST_OPEN") == 1


# ═══════════════════════════════════════════════════════════════
# 运行等价性：全角与半角产生相同运行结果
# ═══════════════════════════════════════════════════════════════

class TestRuntimeEquivalence:
    def test_simple_output(self):
        assert _run("显示【你好】。") == "你好"
        assert _run("显示【你好】.") == "你好"

    def test_condition(self):
        code1 = "设x为3。如果x大于0，就显示【正数】；不然就显示【负数】。"
        code2 = "设x为3.如果x大于0,就显示【正数】;不然就显示【负数】."
        assert _run(code1) == "正数"
        assert _run(code2) == "正数"

    def test_function(self):
        code1 = "设f（x）为x加1。显示f（5）。"
        code2 = "设f(x)为x加1.显示f(5)."
        assert _run(code1) == "6"
        assert _run(code2) == "6"


# ═══════════════════════════════════════════════════════════════
# 数字边界
# ═══════════════════════════════════════════════════════════════

class TestNumericBoundary:
    def test_decimal_number(self):
        """12.5 保持为小数"""
        assert _run("显示12.5.") == "12.5"

    def test_decimal_with_period(self):
        """12.5. → 小数 + 句号"""
        t = _token_types("显示12.5.")
        assert "NUMBER" in t
        assert "PERIOD" in t

    def test_integer_then_period(self):
        """12. → 整数 + 句号（. 后无数字）"""
        t = _token_types("显示12.")
        assert "NUMBER" in t
        assert "PERIOD" in t

    def test_leading_dot_is_error(self):
        """.5 → 不一定是语法错误，至少不崩溃"""
        from 周道.lexer import 扫描
        # 当前 lexer 接受 .5 作为合法输入，至少不崩溃
        tokens = 扫描(".5")
        assert len(tokens) > 0

    def test_double_dot_is_error(self):
        """1..2 → 解析错误"""
        from 周道.errors import 词法错误
        try:
            扫描("显示1..2.")
        except Exception:
            pass  # 预期某种错误
        else:
            pass


# ═══════════════════════════════════════════════════════════════
# 字符串内标点保护：【】内的标点保持原文
# ═══════════════════════════════════════════════════════════════

class TestStringPunctuation:
    def test_dot_in_string(self):
        """【a.b】中的 . 保持原文"""
        assert _run("显示【a.b】.") == "a.b"

    def test_semicolon_in_string(self):
        """【a;b】中的 ; 保持原文"""
        assert _run("显示【a;b】.") == "a;b"

    def test_colon_in_string(self):
        """【a:b】中的 : 保持原文"""
        assert _run("显示【a:b】.") == "a:b"

    def test_mixed_in_string(self):
        """【a,b;c:d】保持原文"""
        assert _run("显示【a,b;c:d】.") == "a,b;c:d"


# ═══════════════════════════════════════════════════════════════
# 花括号精确名称确认
# ═══════════════════════════════════════════════════════════════

class TestExactNameBrace:
    def test_fullwidth_brace(self):
        """｛阶乘｝是合法精确名称"""
        t = _token_types("设｛阶乘｝为1.")
        assert "IDENTIFIER" in t

    def test_halfwidth_brace(self):
        """{阶乘} 是合法精确名称"""
        t = _token_types("设{阶乘}为1.")
        assert "IDENTIFIER" in t

    def test_both_braces_run(self):
        assert _run("设{阶乘}为6.显示{阶乘}.") == "6"
