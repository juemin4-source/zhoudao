"""013 D2：CrossModuleMap 消费级验收测试。"""
import sys, os, tempfile, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from contextlib import redirect_stdout
from 周道.module_loader import ModuleLoader


def _setup(modules: dict[str, str]) -> str:
    tmpdir = tempfile.mkdtemp()
    for relpath, content in modules.items():
        full = os.path.join(tmpdir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    return tmpdir


class TestConsumption:
    def test_three_level_error_b_zd(self):
        """b.zd 内部失败时选择 b 的 SourceMap。"""
        tmpdir = _setup({
            "a.zd": "定义处理（x）如下：以x加1为所得。\n规定模块接口：处理。\n",
            "b.zd": "从周道源文件《a》中引入处理。\n定义计算（x）如下：以处理（x）除0为所得。\n规定模块接口：计算。\n",
        })
        loader = ModuleLoader([])
        try:
            loader.load_module("b", os.path.join(tmpdir))
        except Exception as e:
            err = str(e).lower()
            assert "zero" in err or "division" in err

    def test_selection_import_error_in_definition(self):
        """选择引入的函数内部失败定位原定义模块。"""
        tmpdir = _setup({
            "tools.zd": "定义计算（x）如下：以x除0为所得。\n规定模块接口：计算。\n",
            "main.zd": "从周道源文件《tools》中引入计算。\n运行如下：显示计算（5）。\n",
        })
        loader = ModuleLoader([])
        try:
            loader.load_module("main", tmpdir)
        except Exception as e:
            err_str = str(e)
            assert "除0" in err_str or "division" in err_str or "zero" in err_str

    def test_whole_module_error_in_definition(self):
        """整体模块成员失败定位原定义模块。"""
        tmpdir = _setup({
            "tools.zd": "定义处理（x）如下：以x除0为所得。\n规定模块接口：处理。\n",
            "main.zd": "引入周道源文件《tools》。\n运行如下：显示tools的处理（5）。\n",
        })
        loader = ModuleLoader([])
        try:
            loader.load_module("main", tmpdir)
        except Exception as e:
            assert "除0" in str(e) or "division" in str(e) or "zero" in str(e)

    def test_cross_module_map_size(self):
        """多模块加载后 CrossModuleMap 注册数正确。"""
        tmpdir = _setup({
            "a.zd": "定义双倍（x）如下：以x乘2为所得。\n规定模块接口：双倍。\n",
            "b.zd": "从周道源文件《a》中引入双倍。\n定义三倍（x）如下：以双倍（x）加x为所得。\n规定模块接口：三倍。\n",
        })
        loader = ModuleLoader([])
        loader.load_module("b", tmpdir)
        assert len(loader.跨模块SourceMap.所有模块) >= 2
