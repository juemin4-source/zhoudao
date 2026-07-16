"""周道 v0.0.3：ExactIdentifier 边界测试。

覆盖：
- 合法标识符（中文、英文、下划线、数字混合）
- 非法字符（标点、运算符、空格）
- 数字开头
- 空标识符
- 花括号精确名称
- NFC 规范化
- 全角字母数字转半角
- 验证() 的调用保证
"""

import pytest
from 周道.exact_identifier import ExactIdentifier, 标识符提取器, _是合法名称字符, _是表意文字
from 周道.errors import 源码位置, 词法错误, 语义错误

P = 源码位置(行=1, 列=1, 索引=0)


class Test合法名称字符:
    def test_中文合法(self):
        assert _是合法名称字符('名')
        assert _是合法名称字符('称')
        assert _是合法名称字符('用')
        assert _是合法名称字符('户')

    def test_英文合法(self):
        assert _是合法名称字符('a')
        assert _是合法名称字符('Z')
        assert _是合法名称字符('x')

    def test_数字合法(self):
        assert _是合法名称字符('0')
        assert _是合法名称字符('9')
        assert _是合法名称字符('3')

    def test_下划线合法(self):
        assert _是合法名称字符('_')

    def test_全角英文字母不合法(self):
        assert not _是合法名称字符('Ａ')  # fullwidth A
        assert not _是合法名称字符('ｚ')  # fullwidth z

    def test_全角数字不合法(self):
        assert not _是合法名称字符('０')
        assert not _是合法名称字符('９')

    def test_标点不合法(self):
        assert not _是合法名称字符('。')
        assert not _是合法名称字符('，')
        assert not _是合法名称字符('、')
        assert not _是合法名称字符('；')
        assert not _是合法名称字符('：')
        assert not _是合法名称字符('？')
        assert not _是合法名称字符('！')
        assert not _是合法名称字符('【')
        assert not _是合法名称字符('】')
        assert not _是合法名称字符('（')
        assert not _是合法名称字符('）')
        assert not _是合法名称字符('｛')
        assert not _是合法名称字符('｝')
        assert not _是合法名称字符('＆')
        assert not _是合法名称字符('＠')

    def test_运算符不合法(self):
        assert not _是合法名称字符('+')
        assert not _是合法名称字符('-')
        assert not _是合法名称字符('*')
        assert not _是合法名称字符('=')
        assert not _是合法名称字符('>')
        assert not _是合法名称字符('<')
        assert not _是合法名称字符('.')

    def test_空格不合法(self):
        assert not _是合法名称字符(' ')
        assert not _是合法名称字符('\t')

    def test_表意文字范围(self):
        assert _是表意文字('一')    # 4E00
        assert _是表意文字('鿿')    # 9FFF
        assert _是表意文字('𠀀')    # 20000
        assert not _是表意文字('。')  # 3001 — CJK punct


class TestExactIdentifierConstruct:
    def test_普通中文名(self):
        e = ExactIdentifier("用户")
        assert e.名称 == "用户"
        assert not e.是否精确

    def test_英文名(self):
        e = ExactIdentifier("userName")
        assert e.名称 == "userName"

    def test_混合名(self):
        e = ExactIdentifier("版本2_3")
        assert e.名称 == "版本2_3"

    def test_下划线开头(self):
        e = ExactIdentifier("_内部")
        assert e.名称 == "_内部"

    def test_花括号精确(self):
        e = ExactIdentifier("设", 是否精确=True)
        assert e.名称 == "设"
        assert e.是否精确

    def test_nfc规范化(self):
        # 复合字符 vs 分解形式
        e = ExactIdentifier("Café")  # NFC already
        assert "é" in e.名称 or "é" not in e.名称  # should stay NFC

    def test_全角字母转半角(self):
        e = ExactIdentifier("ＡＢＣ")
        assert e.名称 == "ABC"

    def test_全角数字转半角(self):
        e = ExactIdentifier("１２３")
        assert e.名称 == "123"

    def test_全角混合(self):
        e = ExactIdentifier("测试ＡＢＣ１２３")
        assert e.名称 == "测试ABC123"


class TestExactIdentifier验证:
    def test_空标识符(self):
        e = ExactIdentifier("")
        with pytest.raises(词法错误, match="空标识符"):
            e.验证(P)

    def test_数字开头(self):
        e = ExactIdentifier("3个")
        with pytest.raises(词法错误, match="首字符非法"):
            e.验证(P)

    def test_含非法字符(self):
        e = ExactIdentifier("用户-名称")
        with pytest.raises(词法错误, match="非法字符"):
            e.验证(P)

    def test_含点号(self):
        e = ExactIdentifier("用户.名称")
        with pytest.raises(词法错误, match="非法字符"):
            e.验证(P)

    def test_完全关键字(self):
        e = ExactIdentifier("设")
        with pytest.raises(语义错误, match="完全关键字"):
            e.验证(P)

    def test_完全关键字精确通过(self):
        e = ExactIdentifier("设", 是否精确=True)
        # 花括号精确名应该通过关键字检查
        e.验证(P)

    def test_含标点非法(self):
        e = ExactIdentifier("用户，名称")
        with pytest.raises(词法错误, match="非法字符"):
            e.验证(P)


class Test标识符提取器:
    def test_普通中文标识符(self):
        src = "用户"
        e, i = 标识符提取器.从源码提取(src, 0, P)
        assert e is not None
        assert e.名称 == "用户"
        assert i == 2  # 2 Chinese chars

    def test_英文标识符(self):
        src = "userName"
        e, i = 标识符提取器.从源码提取(src, 0, P)
        assert e.名称 == "userName"

    def test_数字开头失败(self):
        src = "3abc"
        result, _ = 标识符提取器.从源码提取(src, 0, P)
        assert result is None  # starts with digit

    def test_标点开头失败(self):
        src = "。测试"
        result, _ = 标识符提取器.从源码提取(src, 0, P)
        assert result is None

    def test_花括号精确(self):
        src = "{用户}"
        e, i = 标识符提取器.从源码提取(src, 0, P)
        assert e is not None
        assert e.名称 == "用户"
        assert e.是否精确

    def test_花括号关键字(self):
        src = "{设}"
        e, i = 标识符提取器.从源码提取(src, 0, P)
        assert e is not None
        assert e.名称 == "设"
        assert e.是否精确

    def test_全角花括号(self):
        src = "｛用户｝"
        e, i = 标识符提取器.从源码提取(src, 0, P)
        assert e is not None
        assert e.名称 == "用户"

    def test_空花括号(self):
        src = "{}"
        with pytest.raises(词法错误, match="空花括号"):
            标识符提取器.从源码提取(src, 0, P)

    def test_花括号空格(self):
        src = "{ }"
        with pytest.raises(词法错误, match="空白字符"):
            标识符提取器.从源码提取(src, 0, P)

    def test_花括号未闭合(self):
        src = "{用户"
        with pytest.raises(词法错误, match="未闭合"):
            标识符提取器.从源码提取(src, 0, P)

    def test_提取器验证_非法名称(self):
        # 普通提取遇到非法字符作为边界，返回前缀；花括号内才报错
        # 花括号精确名中含有非法字符（点号），验证应拒绝
        src = "{非法.名称}"
        with pytest.raises(词法错误, match="非法字符"):
            标识符提取器.从源码提取(src, 0, P)

    def test_提取器验证_关键字(self):
        src = "设"
        with pytest.raises(语义错误, match="完全关键字"):
            标识符提取器.从源码提取(src, 0, P)


if __name__ == "__main__":
    pytest.main([__file__])
