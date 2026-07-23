"""013 阶段 B：模块主链专项测试。

WP1: 递归目录
WP2: 选择引入名称注入
WP3: 整体引入模块绑定
WP4: 接口与入口隔离、重复初始化保护
WP5: 自循环、双循环、间接循环
"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from 周道.module_loader import ModuleLoader
from 周道.module_registry import 循环引入错误
from 周道.errors import 周道错误


def _setup(modules: dict[str, str]) -> str:
    """创建临时测试目录并写入模块文件。返回 tmpdir 路径。"""
    tmpdir = tempfile.mkdtemp()
    for relpath, content in modules.items():
        full = os.path.join(tmpdir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    return tmpdir


# ═══════════════════════════════════════════════════════════════
# WP1：递归模块目录
# ═══════════════════════════════════════════════════════════════

class TestRecursiveDirectory:
    """被引入模块以自身目录为解析基准加载依赖。"""

    def test_sub_module_imports_own_dir(self):
        """B.zd 在 sub/ 中，B 引入 sub/C.zd 应以 sub/ 解析。"""
        tmpdir = _setup({
            "sub/C.zd": "定义双倍（x）如下：以x乘2为所得。\n规定模块接口：双倍。\n",
            "sub/B.zd": "从周道源文件《C》中引入双倍。\n定义处理（x）如下：以双倍（x）为所得。\n规定模块接口：处理。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("B", os.path.join(tmpdir, "sub"))
        assert "处理" in members
        assert members["处理"](5) == 10

    def test_deep_recursive_chain(self):
        """B.zd 引入 C.zd（同目录），C 的递归以 B 自身目录解析。"""
        tmpdir = _setup({
            "sub/C.zd": "定义值（x）如下：以x加1为所得。\n规定模块接口：值。\n",
            "sub/B.zd": "从周道源文件《C》中引入值。\n定义处理（x）如下：以值（x）乘2为所得。\n规定模块接口：处理。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("B", os.path.join(tmpdir, "sub"))
        assert "处理" in members
        assert members["处理"](3) == 8  # (3+1)*2


# ═══════════════════════════════════════════════════════════════
# WP2：选择引入名称注入
# ═══════════════════════════════════════════════════════════════

class TestSelectionImport:
    """从周道源文件...中引入 将名称注入当前命名空间。"""

    def test_selection_import_injects_names(self):
        """选择引入的名称可直接使用。"""
        tmpdir = _setup({
            "tools.zd": "定义甲（x）如下：以x加1为所得。\n定义乙（x）如下：以x乘2为所得。\n规定模块接口：甲、乙。\n",
            "main.zd": "从周道源文件《tools》中引入甲。\n运行如下：显示甲（3）。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("main", tmpdir)
        assert "甲" in members
        assert members["甲"](3) == 4
        # 乙 未被选择引入，不应存在
        assert "乙" not in members

    def test_selection_does_not_create_module_binding(self):
        """选择引入不额外建立模块绑定。"""
        tmpdir = _setup({
            "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
            "main.zd": "从周道源文件《tools》中引入甲。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("main", tmpdir)
        assert "甲" in members
        assert "tools" not in members  # 不应建立模块绑定

    def test_import_name_not_in_interface_fails(self):
        """引入接口外名称应报错。"""
        tmpdir = _setup({
            "tools.zd": "定义甲（x）如下：以x加1为所得。\n定义内部（x）如下：以x乘2为所得。\n规定模块接口：甲。\n",
            "main.zd": "从周道源文件《tools》中引入内部。\n",
        })
        loader = ModuleLoader([])
        with pytest.raises(周道错误, match="没有公开成员"):
            loader.load_module("main", tmpdir)


# ═══════════════════════════════════════════════════════════════
# WP3：整体引入模块绑定
# ═══════════════════════════════════════════════════════════════

class TestWholeModuleImport:
    """引入周道源文件... 建立模块绑定，不平铺名称。"""

    def test_whole_import_creates_module_binding(self):
        """整体引入建立模块绑定。"""
        tmpdir = _setup({
            "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
            "main.zd": "引入周道源文件《tools》。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("main", tmpdir)
        assert "tools" in members
        # 模块对象应具有成员访问能力
        tools = members["tools"]
        assert tools.甲(3) == 4

    def test_whole_import_does_not_flatten_names(self):
        """整体引入不平铺注入公开成员。"""
        tmpdir = _setup({
            "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
            "main.zd": "引入周道源文件《tools》。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("main", tmpdir)
        assert "tools" in members
        assert "甲" not in members  # 不平铺

    def test_aliased_import_uses_alias(self):
        """带别名整体引入使用别名。"""
        tmpdir = _setup({
            "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
            "main.zd": "引入周道源文件《tools》，下文简称器。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("main", tmpdir)
        assert "器" in members
        assert "tools" not in members
        assert members["器"].甲(3) == 4


# ═══════════════════════════════════════════════════════════════
# WP4：接口与入口隔离、初始化一次
# ═══════════════════════════════════════════════════════════════

class TestModuleInterface:
    """模块接口限制可访问的公开成员。"""

    def test_interface_restricts_public_members(self):
        """接口外的顶层名称不暴露。"""
        tmpdir = _setup({
            "tools.zd": "设计数为1。\n定义公开（x）如下：以计数乘x为所得。\n定义内部（x）如下：以x乘2为所得。\n规定模块接口：公开。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("tools", tmpdir)
        assert "公开" in members
        assert "内部" not in members  # 接口限制
        assert "计数" not in members  # 接口限制

    def test_entry_not_executed_when_imported(self):
        """被引入时不执行 运行如下。"""
        tmpdir = _setup({
            "tools.zd": "设计数为0。\n运行如下：使计数加1。\n规定模块接口：计数。\n",
        })
        loader = ModuleLoader([])
        members = loader.load_module("tools", tmpdir)
        # 如果运行如下被执行了，计数会是 1
        assert members["计数"] == 0  # 没执行则保持 0


class TestInitOnce:
    """同一成功模块在一个运行上下文中只初始化一次。"""

    def test_repeated_import_returns_same_object(self):
        """重复引入返回同一模块对象。"""
        tmpdir = _setup({
            "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
        })
        loader = ModuleLoader([])
        m1 = loader.load_module("tools", tmpdir)
        m2 = loader.load_module("tools", tmpdir)
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════
# WP5：循环检测
# ═══════════════════════════════════════════════════════════════

class TestCycleDetection:
    """直接和间接循环都在正确链上失败。"""

    def test_self_cycle(self):
        """A → A"""
        tmpdir = _setup({"self.zd": "引入周道源文件《self》。\n"})
        with pytest.raises(循环引入错误, match="循环"):
            ModuleLoader([]).load_module("self", tmpdir)

    def test_direct_cycle(self):
        """A → B → A"""
        tmpdir = _setup({
            "a.zd": "引入周道源文件《b》。\n",
            "b.zd": "引入周道源文件《a》。\n",
        })
        with pytest.raises(循环引入错误, match="循环"):
            ModuleLoader([]).load_module("a", tmpdir)

    def test_indirect_cycle(self):
        """X → Y → Z → X"""
        tmpdir = _setup({
            "x.zd": "引入周道源文件《y》。\n",
            "y.zd": "引入周道源文件《z》。\n",
            "z.zd": "引入周道源文件《x》。\n",
        })
        with pytest.raises(循环引入错误, match="循环"):
            ModuleLoader([]).load_module("x", tmpdir)
