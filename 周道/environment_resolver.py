"""周道 v0.0.10: Python 环境解析器。

环境解析必须确定、可解释、可复现。
失败时明确报错，不退避到当前进程。
"""

from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass, field

from .project_config import ProjectConfig


class 环境解析错误(Exception):
    """环境解析失败。"""
    pass


@dataclass
class 环境信息:
    """Python 环境解析结果。"""
    解释器路径: str = ""
    python版本: str = ""
    搜索路径: list[str] = field(default_factory=list)


def 解析环境(配置: ProjectConfig) -> 环境信息:
    """解析 Python 环境。

    Args:
        配置: 项目配置

    Returns:
        环境信息

    Raises:
        环境解析错误: 解释器不可执行或无法获取 sys.path
    """
    interpreter = 配置.interpreter

    # 确定解释器路径
    if os.path.isabs(interpreter):
        解释器路径 = interpreter
    elif 配置.config_path:
        项目根 = os.path.dirname(配置.config_path)
        候选 = os.path.join(项目根, interpreter)
        if os.path.isfile(候选) and os.access(候选, os.X_OK):
            解释器路径 = 候选
        else:
            解释器路径 = interpreter
    else:
        解释器路径 = interpreter

    # 验证解释器可执行
    if not os.path.isfile(解释器路径) or not os.access(解释器路径, os.X_OK):
        raise 环境解析错误(
            f"Python 解释器不可执行：{解释器路径}\n"
            f"请在 zhoudao.toml 的 [python] 中设置正确的 interpreter 路径。"
        )

    # 获取 sys.path
    搜索路径 = _获取系统路径(解释器路径, 配置.extra_paths)

    # 获取版本
    python版本 = _获取版本(解释器路径)

    return 环境信息(
        解释器路径=解释器路径,
        python版本=python版本,
        搜索路径=搜索路径,
    )


def _获取系统路径(解释器路径: str, extra_paths: list[str]) -> list[str]:
    """通过目标解释器获取 sys.path。

    Raises:
        环境解析错误: 无法获取 sys.path
    """
    try:
        result = subprocess.run(
            [解释器路径, "-c", "import sys; print('\\n'.join(sys.path))"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            路径列表 = [p.strip() for p in result.stdout.split("\n") if p.strip()]
            路径列表.extend(extra_paths)
            return 路径列表
        raise 环境解析错误(
            f"无法获取 {解释器路径} 的 sys.path：{result.stderr.strip()}"
        )
    except FileNotFoundError:
        raise 环境解析错误(f"解释器未找到：{解释器路径}")
    except subprocess.TimeoutExpired:
        raise 环境解析错误(f"获取 sys.path 超时：{解释器路径}")
    except PermissionError:
        raise 环境解析错误(f"解释器无执行权限：{解释器路径}")


def _获取版本(解释器路径: str) -> str:
    """获取 Python 版本。"""
    try:
        result = subprocess.run(
            [解释器路径, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or result.stderr.strip()
        raise 环境解析错误(
            f"无法获取 {解释器路径} 版本：{result.stderr.strip()}"
        )
    except FileNotFoundError:
        raise 环境解析错误(f"解释器未找到：{解释器路径}")
    except subprocess.TimeoutExpired:
        raise 环境解析错误(f"获取版本超时：{解释器路径}")
