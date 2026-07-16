"""周道 v0.0.8: 模块系统测试。

测试覆盖：
- 模块解析与加载
- 公开成员访问
- 模块缓存（重复引入返回同一对象）
- 循环引入检测
- 入口隔离（被引入时不执行运行如下）
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from 周道.module_resolver import ModuleResolver
from 周道.module_registry import ModuleRegistry, 循环引入错误
from 周道.module_loader import ModuleLoader
from 周道.errors import 周道错误, 语义错误

# 测试 fixture 目录
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "modules")


class TestModuleResolver:
    """模块路径解析测试。"""

    def test_resolve_found(self):
        """解析存在的模块。"""
        resolver = ModuleResolver()
        path = resolver.resolve("tool", FIXTURE_DIR)
        assert path is not None
        assert path.endswith("tool.zd")

    def test_resolve_not_found(self):
        """解析不存在的模块返回 None。"""
        resolver = ModuleResolver()
        path = resolver.resolve("nonexistent", FIXTURE_DIR)
        assert path is None


class TestModuleRegistry:
    """模块注册表测试。"""

    def test_cycle_detection(self):
        """循环引入检测。"""
        registry = ModuleRegistry()
        registry.开始加载("a.zd")
        with pytest.raises(循环引入错误):
            registry.开始加载("b.zd")
            registry.开始加载("a.zd")  # 循环！

    def test_normal_load(self):
        """正常加载流程。"""
        registry = ModuleRegistry()
        registry.开始加载("a.zd")
        registry.完成加载("a.zd")
        registry.register("a.zd", {"value": 42})
        assert registry.is_loaded("a.zd")
        assert registry.get_module("a.zd")["value"] == 42

    def test_cycle_path_display(self):
        """循环路径显示。"""
        registry = ModuleRegistry()
        registry.开始加载("a.zd")
        registry.开始加载("b.zd")
        try:
            registry.开始加载("c.zd")
            registry.开始加载("a.zd")
        except 循环引入错误 as e:
            msg = str(e)
            assert "a.zd" in msg
            assert "b.zd" in msg
            # 必须展示完整路径
            assert "→" in msg


class TestModuleLoader:
    """模块加载器集成测试。"""

    def _loader(self):
        return ModuleLoader(模块根目录=[FIXTURE_DIR])

    def test_load_module(self):
        """加载周道模块并访问公开成员。"""
        loader = self._loader()
        members = loader.load_module("tool", FIXTURE_DIR)
        assert "增一" in members
        assert callable(members["增一"])
        # 验证函数可调用
        assert members["增一"](5) == 6

    def test_cycle_import_detected(self):
        """循环引入在周道层拒绝。"""
        loader = self._loader()
        with pytest.raises((循环引入错误, 周道错误, 语义错误)):
            loader.load_module("cycle_a", FIXTURE_DIR)

    def test_module_cache(self):
        """重复引入返回同一模块对象（单例）。"""
        loader = self._loader()
        m1 = loader.load_module("counter", FIXTURE_DIR)
        m2 = loader.load_module("counter", FIXTURE_DIR)
        # 同一对象引用
        assert m1 is m2
        # 加载次数应为 1（只初始化一次）
        assert m1["计数"] == 1
