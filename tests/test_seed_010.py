"""周道 v0.0.10: 工具链验收测试。"""
import sys, os, io, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from 周道.runner import 转译, 运行, 转译_仅语法
from 周道.formatter import 格式化, 检查格式差异, 迁移弃用句式
from 周道.project_config import ProjectConfig, 加载项目配置, 生成环境报告
from 周道.environment_resolver import 解析环境, 环境解析错误
from 周道.lsp_server import 周道LSP


# ═══════════════════════════════════════════════════════════
# 项目配置
# ═══════════════════════════════════════════════════════════

class Test项目配置:
    def test_默认配置(self):
        """单文件模式默认配置。"""
        cfg = 加载项目配置(".")
        assert cfg is None  # 没有 zhoudao.toml 时返回 None

    def test_环境报告字段(self):
        """环境报告包含必需字段。"""
        cfg = ProjectConfig(name="test", interpreter=sys.executable)
        report = 生成环境报告(cfg, "3.12", sys.executable, ["/usr/lib/python3.12"])
        assert "周道版本" in report
        assert "Python 版本" in report
        assert "Python 解释器" in report


# ═══════════════════════════════════════════════════════════
# 环境解析
# ═══════════════════════════════════════════════════════════

class Test环境解析:
    def test_当前解释器(self):
        """使用当前 Python 解释器解析环境。"""
        cfg = ProjectConfig(name="test", interpreter=sys.executable)
        环境 = 解析环境(cfg)
        assert 环境.解释器路径 == sys.executable
        assert "3.12" in 环境.python版本
        assert len(环境.搜索路径) > 0

    def test_解释器不可执行(self):
        """不可执行的解释器路径应报错。"""
        cfg = ProjectConfig(name="test", interpreter="/nonexistent/python")
        with pytest.raises(环境解析错误):
            解析环境(cfg)


# ═══════════════════════════════════════════════════════════
# Formatter
# ═══════════════════════════════════════════════════════════

class TestFormatter:
    def test_格式化幂等(self):
        """格式化结果再次格式化不变。"""
        src = "设甲为1。"
        r1 = 格式化(src)
        r2 = 格式化(r1)
        assert r1 == r2

    def test_格式化不改变语义(self):
        """格式化前后执行结果一致。"""
        src = "设甲为1。运行如下：显示甲。"
        格式化后 = 格式化(src)
        f1 = io.StringIO()
        from contextlib import redirect_stdout
        py1 = 转译(src)
        env1 = {"__name__": "__周道__"}
        with redirect_stdout(f1):
            exec(py1, env1)
        f2 = io.StringIO()
        py2 = 转译(格式化后)
        env2 = {"__name__": "__周道__"}
        with redirect_stdout(f2):
            exec(py2, env2)
        assert f1.getvalue() == f2.getvalue()

    def test_弃用迁移(self):
        """弃用句式迁移。"""
        结果 = 迁移弃用句式("设结果为等待取数（）的所得。")
        assert "等待" in 结果 and "记作结果" in 结果


# ═══════════════════════════════════════════════════════════
# LSP 基础协议
# ═══════════════════════════════════════════════════════════

class TestLSP:
    def test_初始化(self):
        """LSP 初始化返回能力列表。"""
        lsp = 周道LSP()
        result = lsp._初始化({"rootUri": "file:///test"})
        assert "capabilities" in result
        assert result["capabilities"].get("hoverProvider")

    def test_诊断(self):
        """LSP 诊断返回诊断列表。"""
        lsp = 周道LSP()
        uri = "file:///test.zd"
        lsp.文档[uri] = "设甲为1。运行如下：显示甲。"
        result = lsp._诊断({"textDocument": {"uri": uri}})
        assert "items" in result

    def test_语义高亮(self):
        """语义高亮返回 token 数据。"""
        lsp = 周道LSP()
        uri = "file:///test.zd"
        lsp.文档[uri] = "设甲为1。运行如下：显示甲。"
        result = lsp._语义高亮({"textDocument": {"uri": uri}})
        assert "data" in result
        assert len(result["data"]) > 0

    def test_悬停(self):
        """悬停返回 token 信息。"""
        lsp = 周道LSP()
        uri = "file:///test.zd"
        lsp.文档[uri] = "设甲为1。运行如下：显示甲。"
        result = lsp._悬停({
            "textDocument": {"uri": uri},
            "position": {"line": 0, "character": 2},
        })
        assert result is not None
        assert "甲" in result["contents"]["value"]

    def test_补全(self):
        """补全返回名称列表。"""
        lsp = 周道LSP()
        uri = "file:///test.zd"
        lsp.文档[uri] = "设甲为1。设乙为2。运行如下：显示甲。"
        result = lsp._补全({"textDocument": {"uri": uri}})
        assert "items" in result

    def test_格式化(self):
        """LSP 格式化返回格式化文本。"""
        lsp = 周道LSP()
        uri = "file:///test.zd"
        lsp.文档[uri] = "设甲为1。"
        result = lsp._格式化({
            "textDocument": {"uri": uri},
            "options": {"tabSize": 4},
        })
        assert len(result) > 0
        assert "设" in result[0]["newText"]


# ═══════════════════════════════════════════════════════════
# CLI 契约（通过 runner 测试）
# ═══════════════════════════════════════════════════════════

class TestCLI:
    def test_转译_仅语法(self):
        """语法转换正常输出。"""
        r = 转译_仅语法("设甲为1。")
        assert "1" in r

    def test_运行程序(self):
        """程序运行正常。"""
        f = io.StringIO()
        from contextlib import redirect_stdout
        py = 转译("运行如下：显示【CLI测试】。")
        env = {"__name__": "__周道__"}
        with redirect_stdout(f):
            exec(py, env)
        assert "CLI测试" in f.getvalue()
