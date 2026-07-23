"""012 方法别名集成测试。"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contextlib import redirect_stdout
from 周道 import 转译
from 周道.method_aliases import 调用成员 as _zd_调用成员


def check(code, expected_substr, label):
    try:
        py = 转译(code)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(py, {"__name__": "__周道__", "_zd_调用成员": _zd_调用成员})
        output = buf.getvalue().strip()
        assert expected_substr in output, f"{label}: expected {expected_substr!r} in {output!r}"
        print(f"  OK {label}: {output}")
    except Exception as e:
        print(f"  FAIL {label}: {e}")


def test_text_aliases():
    print("=== 文本别名 ===")
    check('设文本为【a,b,c】；显示文本的分割（【,】）。', "['a', 'b', 'c']", "分割")
    check('设文本为【  abc  】；显示文本的去除两端（）。', "abc", "去除两端")
    check('设文本为【Hello】；显示文本的转为小写（）。', "hello", "转为小写")
    check('设文本为【Hello】；显示文本的转为大写（）。', "HELLO", "转为大写")
    check('设文本为【abc】；显示文本的开头是（【a】）。', "True", "开头是")
    check('设文本为【abc】；显示文本的结尾是（【c】）。', "True", "结尾是")
    check('设文本为【abc,def】；显示文本的替换（【,】,【 】）。', "abc def", "替换")
    check('设文本为【a,b,c】；显示文本的查找（【b】）。', "1", "查找")
    check('设文本为【banana】；显示文本的计数（【a】）。', "3", "计数")
    check('设文本为【a,b,c】；显示文本的split（【,】）。', "['a', 'b', 'c']", "Python原名split")
    check('设文本为【a,b,c】；显示文本的upper（）。', "A,B,C", "Python原名upper")


def test_list_aliases():
    print("\n=== 列表别名 ===")
    check('设列表为［3、1、2］；列表的排序（）；显示列表。', "[1, 2, 3]", "排序")
    check('设列表为［1、2、3］；列表的追加（4）；显示列表。', "[1, 2, 3, 4]", "追加")
    check('设列表为［1、2、3］；列表的反转（）；显示列表。', "[3, 2, 1]", "反转")
    check('设列表为［1、2、3］；设c为列表的复制（）；列表的清空（）；显示c。', "[1, 2, 3]", "复制+清空")
    check('设列表为［1、2］；列表的扩展（［3、4］）；显示列表。', "[1, 2, 3, 4]", "扩展")
    check('设列表为［1、2、3］；列表的移除（2）；显示列表。', "[1, 3]", "移除")
    check('设列表为［1、2、3］；显示列表的弹出（）。', "3", "弹出")


def test_dict_aliases():
    print("\n=== 字典别名 ===")
    check('设映射为［【a】为1、【b】为2］；显示映射的取得（【a】）。', "1", "取得")
    check('设映射为［【a】为1、【b】为2］；显示映射的各键（）。', "dict_keys", "各键")
    check('设映射为［【a】为1、【b】为2］；显示映射的各项（）。', "dict_items", "各项")


def test_set_aliases():
    print("\n=== 集合别名 ===")
    check('设集合为集合［1、2、3］；集合的加入（4）；集合的加入（4）；显示集合。', "{1, 2, 3, 4}", "加入")
    check('设集合为集合［1、2、3］；集合的丢弃（2）；显示集合。', "{1, 3}", "丢弃")


def test_native_names():
    print("\n=== Python原名直通 ===")
    check('设列表为［1、2、3］；列表的append（4）；显示列表。', "[1, 2, 3, 4]", "append")
    check('设映射为［【a】为1］；显示映射的get（【a】）。', "1", "get")


def test_user_member_priority():
    """用户自定义成员优先于内建别名。"""
    print("\n=== 用户成员优先 ===")
    code = """设置容器类别，包括值，默认为0。
定义容器类别的分割（数量）如下：使自己的值加数量。
运行如下：设c为容器（）；c的分割（5）；显示c的值。"""
    try:
        py = 转译(code)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(py, {"__name__": "__周道__", "_zd_调用成员": _zd_调用成员})
        output = buf.getvalue().strip()
        assert "5" in output, f"用户成员优先: expected 5, got {output}"
        print(f"  OK 用户成员优先: {output}")
    except Exception as e:
        print(f"  FAIL 用户成员优先: {e}")


def test_ordinary_name_isolated():
    """普通名称不触发别名。"""
    print("\n=== 普通名称隔离 ===")
    code = "定义分割（数）如下：以数加1为所得。设x为分割（3）。显示x。"
    try:
        py = 转译(code)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(py, {"__name__": "__周道__", "_zd_调用成员": _zd_调用成员})
        output = buf.getvalue().strip()
        assert "4" in output, f"普通名称隔离: expected 4, got {output}"
        print(f"  OK 普通名称隔离: 分割(3) = {output}")
    except Exception as e:
        print(f"  FAIL 普通名称隔离: {e}")


def test_type_not_applicable():
    """类型不适用时产生错误。"""
    print("\n=== 类型不适用 ===")
    code = "设数字为3；显示数字的分割（【,】）。"
    try:
        py = 转译(code)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(py, {"__name__": "__周道__", "_zd_调用成员": _zd_调用成员})
        output = buf.getvalue().strip()
        print(f"  预期错误但成功: {output}")
    except Exception as e:
        msg = str(e)
        if "不存在" in msg or "适配" in msg:
            print(f"  OK 类型不适用错误: {msg[:80]}")
        else:
            print(f"  其他错误: {msg[:80]}")


def test_formatter_roundtrip():
    """Formatter 往返不改变成员调用语义。"""
    print("\n=== Formatter 往返 ===")
    from 周道.formatter import 格式化
    codes = [
        '设文本为【a,b,c】。显示文本的分割（【,】）。',
        '设列表为［1、2、3］。列表的追加（4）。',
        '设映射为［【a】为1］。显示映射的取得（【a】）。',
    ]
    for code in codes:
        try:
            formatted = 格式化(code)
            # Re-parse and re-translate: should produce same result
            py1 = 转译(code)
            py2 = 转译(formatted)
            assert py1 == py2, f"格式化前后语义不一致\n原: {py1}\n格式化后: {py2}"
            print(f"  OK 格式化往返: {code[:40]}")
        except Exception as e:
            print(f"  FAIL 格式化往返: {e}")


if __name__ == "__main__":
    test_text_aliases()
    test_list_aliases()
    test_dict_aliases()
    test_set_aliases()
    test_native_names()
    test_user_member_priority()
    test_ordinary_name_isolated()
    test_type_not_applicable()
    test_formatter_roundtrip()
    print("\n所有测试完成。")
