"""013-R1 红灯测试：修实现前先在当前代码上确认失败。

R1-1: 选择引入必须在模块顶层可用
R1-2: 带别名整体引入在语义和运行层都绑定别名
R1-3: 模块运行环境包含运行时助手
"""
import sys, os, tempfile, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from contextlib import redirect_stdout


def _setup(modules: dict[str, str]) -> str:
    tmpdir = tempfile.mkdtemp()
    for relpath, content in modules.items():
        full = os.path.join(tmpdir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    return tmpdir


# ═══════════════════════════════════════════════════════════════
# R1-1: 顶层选择引入立即消费
# ═══════════════════════════════════════════════════════════════

def test_R1_1_selection_import_in_top_level():
    """R1-1: 选择引入的名称在模块顶层可直接使用。"""
    tmpdir = _setup({
        "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
        "main.zd": "从周道源文件《tools》中引入甲。\n设结果为甲（3）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    assert members.get("结果") == 4, f"Expected 4, got {members.get('结果')}"


def test_R1_1_selection_import_immediate_use():
    """R1-1: 函数定义前直接使用选择引入名称。"""
    tmpdir = _setup({
        "tools.zd": "定义双倍（x）如下：以x乘2为所得。\n规定模块接口：双倍。\n",
        "main.zd": "从周道源文件《tools》中引入双倍。\n设结果为双倍（3）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    assert members.get("结果") == 6


# ═══════════════════════════════════════════════════════════════
# R1-2: 带别名整体引入
# ═══════════════════════════════════════════════════════════════

def test_R1_2_aliased_import_semantic():
    """带别名引入后，别名能通过语义分析。"""
    from 周道.lexer import 扫描
    from 周道.parser import 解析器
    from 周道.lowering import 降低
    from 周道.semantic_analyzer import 分析 as 语义分析

    code = "引入周道源文件《tools》，下文简称器。\n定义处理（x）如下：以器的甲（x）为所得。\n"
    tokens = 扫描(code)
    parser = 解析器(tokens)
    ast = parser.解析()
    result = 降低(ast)
    sem = 语义分析(result.ir, result.位置映射)
    # 语义分析不应认为「器」是未定义名称
    assert not sem.有错误, f"别名「器」未通过语义分析: {sem.格式化诊断()}"


def test_R1_2_aliased_import_runtime():
    """带别名引入后，别名可真实调用成员。"""
    tmpdir = _setup({
        "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
        "main.zd": "引入周道源文件《tools》，下文简称器。\n设结果为器的甲（3）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    assert members.get("结果") == 4


def test_R1_2_aliased_import_original_name_not_bound():
    """带别名引入后，原模块名不在当前作用域。"""
    from 周道.lexer import 扫描
    from 周道.parser import 解析器
    from 周道.lowering import 降低
    from 周道.semantic_analyzer import 分析 as 语义分析

    code = "引入周道源文件《tools》，下文简称器。\n显示tools。\n"
    tokens = 扫描(code)
    parser = 解析器(tokens)
    ast = parser.解析()
    result = 降低(ast)
    sem = 语义分析(result.ir, result.位置映射)
    # 语义分析应将 tools 视为未定义名称（别名时不额外绑定原模块名）
    assert sem.有错误, "原模块名 tools 应被视为未定义"
    诊断 = sem.格式化诊断()
    assert "tools" in 诊断, f"诊断应提及 tools，实际: {诊断}"


# ═══════════════════════════════════════════════════════════════
# R1-3: 模块环境包含运行时助手
# ═══════════════════════════════════════════════════════════════

def test_R1_3_method_alias_in_module():
    """模块内的函数使用中文方法别名。"""
    tmpdir = _setup({
        "tools.zd": "定义处理（文本）如下：以文本的分割（【,】）为所得。\n规定模块接口：处理。\n",
        "main.zd": "从周道源文件《tools》中引入处理。\n设结果为处理（【a,b,c】）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    assert members.get("结果") == ["a", "b", "c"]


def test_R1_3_json_parse_in_module():
    """模块内使用解析JSON。"""
    tmpdir = _setup({
        "tools.zd": "定义解析（文本）如下：设数据为解析JSON（文本）。\n以数据为所得。\n规定模块接口：解析。\n",
        "main.zd": "从周道源文件《tools》中引入解析。\n设结果为解析（【{\"a\":1}】）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    assert members.get("结果") == {"a": 1}


def test_R1_3_json_generate_in_module():
    """模块内使用生成JSON。"""
    import json
    tmpdir = _setup({
        "tools.zd": "定义生成（数据）如下：以生成JSON（数据）为所得。\n规定模块接口：生成。\n",
        "main.zd": "从周道源文件《tools》中引入生成。\n设结果为生成（映射［【a】为1］）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    result = members.get("结果")
    parsed = json.loads(result)
    assert parsed == {"a": 1}


def test_R1_1_whole_module_immediate_use():
    """顶层整体模块绑定立即消费。"""
    tmpdir = _setup({
        "tools.zd": "定义甲（x）如下：以x加1为所得。\n规定模块接口：甲。\n",
        "main.zd": "引入周道源文件《tools》。\n设结果为tools的甲（3）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    assert members.get("结果") == 4


def test_R1_3_top_level_method_alias_in_module():
    """模块顶层直接使用中文方法别名。"""
    tmpdir = _setup({
        "main.zd": "设文本为【a,b,c】。\n设结果为文本的分割（【,】）。\n规定模块接口：结果。\n",
    })
    from 周道.module_loader import ModuleLoader
    loader = ModuleLoader([])
    members = loader.load_module("main", tmpdir)
    assert members.get("结果") == ["a", "b", "c"]


# ═══════════════════════════════════════════════════════════════
# 回归保护
# ═══════════════════════════════════════════════════════════════

def test_R1_regression_selection_not_in_interface():
    """选择引入接口外名称应报错（回归 B 原有测试）。"""
    tmpdir = _setup({
        "tools.zd": "定义公开（x）如下：以x为所得。\n定义内部（y）如下：以y乘2为所得。\n规定模块接口：公开。\n",
        "main.zd": "从周道源文件《tools》中引入内部。\n",
    })
    from 周道.module_loader import ModuleLoader
    from 周道.errors import 周道错误
    loader = ModuleLoader([])
    with pytest.raises(周道错误, match="没有公开成员"):
        loader.load_module("main", tmpdir)
