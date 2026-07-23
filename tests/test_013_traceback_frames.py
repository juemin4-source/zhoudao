"""013 阶段 D0：运行时帧识别专项测试。

验证 runtime_traceback.提取周道帧 能正确识别周道帧。
"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from 周道.runtime_traceback import 提取周道帧
from 周道.errors import 源码位置


def _模拟帧(co_filename: str, lineno: int = 1, func_name: str = "<module>"):
    """创建一个模拟的 frame-like 对象用于测试。"""
    class FakeCode:
        def __init__(self):
            self.co_filename = co_filename
            self.co_name = func_name

    class FakeTB:
        def __init__(self):
            self.tb_frame = type('obj', (object,), {'f_code': FakeCode()})()
            self.tb_lineno = lineno
            self.tb_next = None

    return FakeTB()


class TestSingleFile:
    """<周道> 单文件帧识别。"""

    def test_single_file_recognized(self):
        """<周道> 帧被正确识别。"""
        tb = _模拟帧('<周道>')
        frames = 提取周道帧(tb, {})
        assert len(frames) == 1
        assert frames[0][0] == '<周道>'

    def test_single_file_order(self):
        """多帧顺序与调用顺序一致（外层→内层）。"""
        tb1 = _模拟帧('<周道>', 1, 'outer')
        tb2 = _模拟帧('<周道>', 5, 'inner')
        tb1.tb_next = tb2
        frames = 提取周道帧(tb1, {})
        assert len(frames) == 2
        assert frames[0][2] == 'outer'
        assert frames[1][2] == 'inner'


class TestZdFiles:
    """.zd 文件帧识别。"""

    def test_zd_file_recognized(self):
        """.zd 路径被识别为周道帧。"""
        tb = _模拟帧('/project/module.zd')
        frames = 提取周道帧(tb, None, 模块路径集={'/project/module.zd'})
        assert len(frames) == 1

    def test_zd_in_path_set(self):
        """在模块路径集中的文件被识别。"""
        tb = _模拟帧('/project/module.py')
        frames = 提取周道帧(tb, None, 模块路径集={'/project/module.py'})
        assert len(frames) == 1

    def test_unrelated_py_not_recognized(self):
        """不相关的 .py 文件不被识别。"""
        tb = _模拟帧('/usr/lib/python/os.py')
        frames = 提取周道帧(tb, None)
        assert len(frames) == 0

    def test_python_lib_not_recognized(self):
        """Python 标准库帧不被识别。"""
        tb = _模拟帧('/usr/lib/python3.12/abc.py')
        frames = 提取周道帧(tb, None)
        assert len(frames) == 0


class TestMultiModule:
    """多模块帧顺序。"""

    def test_mixed_frame_order(self):
        """<周道> 和 .zd 帧混合时顺序正确。"""
        tb1 = _模拟帧('<周道>', 1, 'main')
        tb2 = _模拟帧('/proj/helper.zd', 3, 'helper_func')
        tb3 = _模拟帧('/usr/lib/python/os.py', 10, 'os_func')
        tb1.tb_next = tb2; tb2.tb_next = tb3
        frames = 提取周道帧(tb1, None, 模块路径集={'/proj/helper.zd'})
        assert len(frames) == 2
        assert frames[0][2] == 'main'
        assert frames[1][2] == 'helper_func'


class TestEmptyArgs:
    """空参数时保持原有行为。"""

    def test_no_args_returns_empty(self):
        """无参数时返回空列表。"""
        tb = _模拟帧('/usr/bin/python')
        frames = 提取周道帧(tb)
        assert len(frames) == 0

    def test_empty_mapping(self):
        """空行映射时 <周道> 帧仍可识别。"""
        tb = _模拟帧('<周道>')
        frames = 提取周道帧(tb, {})
        assert len(frames) == 1
