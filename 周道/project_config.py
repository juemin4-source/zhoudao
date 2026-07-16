"""周道 v0.0.10: 项目配置 (zhoudao.toml)。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class ProjectConfig:
    """周道项目配置。"""
    # 项目
    name: str = ""
    version: str = "0.1.0"
    source_roots: list[str] = field(default_factory=lambda: ["src"])
    entry: str = ""

    # Python 环境
    interpreter: str = "python3"
    extra_paths: list[str] = field(default_factory=list)

    # 格式
    line_width: int = 100

    # 诊断
    deprecation: str = "warning"  # "off" | "warning" | "error"

    # LSP
    python_metadata: str = "stubs_only"  # "off" | "stubs_only" | "stubs_then_safe_inspect"

    # 状态
    config_path: str = ""
    已加载: bool = False


def 加载项目配置(项目目录: str) -> ProjectConfig | None:
    """从项目目录加载 zhoudao.toml。

    Args:
        项目目录: 项目根目录

    Returns:
        ProjectConfig 或 None（未找到配置文件时返回单文件默认配置）
    """
    配置路径 = os.path.join(项目目录, "zhoudao.toml")
    if not os.path.isfile(配置路径):
        return None

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    with open(配置路径, "rb") as f:
        数据 = tomllib.load(f)

    项目数据 = 数据.get("project", {})
    python数据 = 数据.get("python", {})
    格式数据 = 数据.get("format", {})
    诊断数据 = 数据.get("diagnostics", {})
    lsp数据 = 数据.get("lsp", {})

    # 解析 source_roots（相对于配置文件目录）
    source_roots_raw = 项目数据.get("source_roots", ["src"])
    source_roots = [
        os.path.normpath(os.path.join(项目目录, p))
        for p in source_roots_raw
    ]

    # 解析 entry
    entry_raw = 项目数据.get("entry", "")
    entry = os.path.normpath(os.path.join(项目目录, entry_raw)) if entry_raw else ""

    # 解析 extra_paths
    extra_paths_raw = python数据.get("extra_paths", [])
    extra_paths = [
        os.path.normpath(os.path.join(项目目录, p))
        for p in extra_paths_raw
    ]

    return ProjectConfig(
        name=项目数据.get("name", ""),
        version=项目数据.get("version", "0.1.0"),
        source_roots=source_roots,
        entry=entry,
        interpreter=python数据.get("interpreter", "python3"),
        extra_paths=extra_paths,
        line_width=格式数据.get("line_width", 100),
        deprecation=诊断数据.get("deprecation", "warning"),
        python_metadata=lsp数据.get("python_metadata", "stubs_only"),
        config_path=配置路径,
        已加载=True,
    )


def 生成环境报告(配置: ProjectConfig, python版本: str, 解释器路径: str,
                  搜索路径: list[str]) -> str:
    """生成环境报告。"""
    行 = [
        f"周道版本: 0.0.10",
        f"Python 版本: {python版本}",
        f"Python 解释器: {解释器路径}",
        f"项目根目录: {os.path.dirname(配置.config_path) if 配置.已加载 else '(单文件模式)'}",
        f"周道源根目录: {', '.join(配置.source_roots) if 配置.已加载 else '(当前目录)'}",
    ]
    行.append("Python 搜索路径:")
    for p in 搜索路径:
        行.append(f"  - {p}")
    行.append(f"弃用检查级别: {配置.deprecation}")
    行.append(f"Python 元数据模式: {配置.python_metadata}")
    return "\n".join(行)
