"""012 别名全量覆盖矩阵 — 每个别名至少一次正向运行验证。"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from contextlib import redirect_stdout
from 周道 import 转译
from 周道.method_aliases import 调用成员 as _zd_调用成员


def run_zd(code):
    py = 转译(code)
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(py, {"__name__": "__周道__", "_zd_调用成员": _zd_调用成员})
    return buf.getvalue().strip()


# ── 文本别名 (13) ────────────────────────────────────────────

@pytest.mark.parametrize("code,expected_substr", [
    ('设s为【a,b,c】；显示s的分割（【,】）。', "['a', 'b', 'c']"),
    ('设s为【 】；设j为【a】；显示j的连接（【b,c】）。', "ba,ac"),
    ('设s为【hello world】；显示s的替换（【hello】,【hi】）。', "hi world"),
    ('设s为【  abc  】；显示s的去除两端（）。', "abc"),
    ('设s为【  abc  】；显示s的strip（）。', "abc"),
    ('设s为【hello】；显示s的开头是（【he】）。', "True"),
    ('设s为【hello】；显示s的结尾是（【lo】）。', "True"),
    ('设s为【abcde】；显示s的查找（【cd】）。', "2"),
    ('设s为【banana】；显示s的计数（【a】）。', "3"),
    ('设s为【hello】；显示s的转为大写（）。', "HELLO"),
    ('设s为【HELLO】；显示s的转为小写（）。', "hello"),
    # Python 原名仍可用
    ('设s为【a,b】；显示s的split（【,】）。', "['a', 'b']"),
])
def test_text_alias(code, expected_substr):
    result = run_zd(code)
    assert expected_substr in result, f"expected {expected_substr!r} in {result!r}"


# ── 列表别名 (9) ─────────────────────────────────────────────

@pytest.mark.parametrize("code,expected_substr", [
    ('设l为［1、2］；l的追加（3）；显示l。', "[1, 2, 3]"),
    ('设l为［1、2］；l的扩展（［3、4］）；显示l。', "[1, 2, 3, 4]"),
    ('设l为［1、3、4］；l的插入（1、2）；显示l。', "[1, 2, 3, 4]"),
    ('设l为［1、2、3］；l的移除（2）；显示l。', "[1, 3]"),
    ('设l为［1、2、3］；显示l的弹出（）。', "3"),
    ('设l为［3、1、2］；l的排序（）；显示l。', "[1, 2, 3]"),
    ('设l为［1、2、3］；l的反转（）；显示l。', "[3, 2, 1]"),
    ('设l为［1、2］；设c为l的复制（）；l的清空（）；显示c。', "[1, 2]"),
    # Python 原名
    ('设l为［1、2］；l的append（3）；显示l。', "[1, 2, 3]"),
])
def test_list_alias(code, expected_substr):
    result = run_zd(code)
    assert expected_substr in result, f"expected {expected_substr!r} in {result!r}"


# ── 字典别名 (9) ─────────────────────────────────────────────

@pytest.mark.parametrize("code,expected_substr", [
    ('设d为［【a】为1、【b】为2］；显示d的取得（【a】）。', "1"),
    ('设d为［【a】为1］；显示d的各键（）。', "dict_keys"),
    ('设d为［【a】为1］；显示d的各值（）。', "dict_values"),
    ('设d为［【a】为1］；显示d的各项（）。', "dict_items"),
    ('设d为［【a】为1］；d的更新（映射［【b】为2］）；显示d的取得（【b】）。', "2"),
    ('设d为［【a】为1］；显示d的弹出（【a】）。', "1"),
    ('设d为映射［］；d的设默认值（【k】、0）；显示d的取得（【k】）。', "0"),
    ('设d为［【a】为1］；设c为d的复制（）；d的清空（）；显示c的取得（【a】）。', "1"),
])
def test_dict_alias(code, expected_substr):
    result = run_zd(code)
    assert expected_substr in result, f"expected {expected_substr!r} in {result!r}"


# ── 集合别名 (6) ─────────────────────────────────────────────

@pytest.mark.parametrize("code,expected_substr", [
    ('设s为集合［1、2］；s的加入（3）；显示s。', "{1, 2, 3}"),
    ('设s为集合［1、2、3］；s的移除（2）；显示s。', "{1, 3}"),
    ('设s为集合［1、2、3］；s的丢弃（2）；s的丢弃（9）；显示s。', "{1, 3}"),
    ('设a为集合［1、2］；设b为集合［3、4］；设u为a的联合（b）；显示u。', "{1, 2, 3, 4}"),
    ('设a为集合［1、2、3］；设b为集合［2、3、4］；设i为a的相交（b）；显示i。', "{2, 3}"),
])
def test_set_alias(code, expected_substr):
    result = run_zd(code)
    assert expected_substr in result, f"expected {expected_substr!r} in {result!r}"
