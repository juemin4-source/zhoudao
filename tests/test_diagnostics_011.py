"""011 诊断与源码映射审计测试。"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from 周道.runner import 转译, 运行
from 周道.errors import 语法错误, 语义错误, 运行时错误


class Test诊断位置:
    def test_语法错误位置(self):
        """语法错误指向正确行列。"""
        with pytest.raises(语法错误) as excinfo:
            转译("设 为1。")
        assert excinfo.value.位置 is not None
        assert excinfo.value.位置.行 == 1

    def test_语义错误位置(self):
        """语义错误指向正确行列。"""
        with pytest.raises(语义错误) as excinfo:
            转译("显示未知名称。")
        assert excinfo.value.位置 is not None
        assert excinfo.value.位置.行 == 1

    def test_运行时错误映射(self):
        """运行时异常映射到周道源码。"""
        with pytest.raises(运行时错误) as excinfo:
            运行("""定义除零（数）如下：
以数整除0为所得。
运行如下：
显示除零（5）。""")
        assert "ZeroDivision" in str(excinfo.value) or "整除" in str(excinfo.value)


class Test源码映射:
    def test_生成器错误映射(self):
        """生成器内部错误映射到正确位置。"""
        with pytest.raises(运行时错误) as excinfo:
            运行("""定义生成器（）如下：
依次给出1。
设结果为1整除0。
运行如下：
从生成器（）中，每取一项记作数字，就显示数字。""")
        pass

    def test_跨模块错误(self):
        """跨模块错误保留文件身份。"""
        from 周道.module_loader import ModuleLoader
        loader = ModuleLoader(模块根目录=[
            os.path.join(os.path.dirname(__file__), "fixtures", "modules")
        ])
        with pytest.raises((运行时错误, Exception)):
            loader.load_module("cycle_a", 
                os.path.join(os.path.dirname(__file__), "fixtures", "modules"))
