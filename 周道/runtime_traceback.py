"""周道运行时回溯：Python 异常 → 周道源码位置全栈映射 v0.0.7。

将 Python 执行时的未处理异常回溯到原始周道源码的行/列/片段。
支持多层调用栈的逐帧映射，提供源码行上下文与列指示器。

用法：
    from .runtime_traceback import 包装运行时异常
    try:
        exec(code, env)
    except Exception:
        raise 包装运行时异常(
            sys.exc_info()[1], sys.exc_info()[2],
            self.行映射, 源码,
        )
"""

from __future__ import annotations

import sys
from typing import Optional

from .errors import 源码位置, 运行时错误


def 提取周道帧(
    回溯对象,
    行映射: dict[int, 源码位置],
) -> list[tuple[str, int, str]]:
    """从回溯对象中提取所有属于 <周道> 的帧。

    Returns:
        [(co_filename, py_lineno, func_name), ...] 从外层到最内层
    """
    frames: list[tuple[str, int, str]] = []
    tb = 回溯对象
    while tb:
        f_code = tb.tb_frame.f_code
        if f_code.co_filename == '<周道>':
            frames.append((f_code.co_filename, tb.tb_lineno, f_code.co_name))
        tb = tb.tb_next
    return frames


def 映射行号(
    py_line: int,
    行映射: dict[int, 源码位置],
    源码行列表: list[str] | None,
) -> tuple[源码位置 | None, str | None]:
    """将 Python 生成行号映射回周道源码位置和源码行内容。

    Args:
        py_line: Python 生成代码中的行号（1-based）
        行映射: 生成行号 → 周道源码位置
        源码行列表: 周道源码按行分割的列表（0-based），可选

    Returns:
        (源码位置, 源码行内容) 元组。无法映射时返回 (None, None)
    """
    zd_pos = 行映射.get(py_line)
    source_line = None
    if zd_pos is not None and 源码行列表 is not None:
        line_idx = zd_pos.行 - 1  # 源码行列表是 0-based
        if 0 <= line_idx < len(源码行列表):
            source_line = 源码行列表[line_idx].rstrip('\n').rstrip('\r')
    return zd_pos, source_line


def 格式化回溯(
    原始异常: BaseException,
    回溯对象,
    行映射: dict[int, 源码位置],
    源码: str | None = None,
    额外说明: str = "",
) -> str:
    """将 Python 异常格式化为带完整周道源码映射的错误信息。

    Args:
        原始异常: 捕获的 Python 异常
        回溯对象: sys.exc_info()[2] 返回的回溯对象
        行映射: 生成行号 → 周道源码位置 的映射字典
        源码: 原始周道源码字符串（可选，提供后可显示源码片段与列指示器）
        额外说明: 附加说明文本

    Returns:
        格式化的多行错误消息字符串
    """
    源码行列表 = 源码.split('\n') if 源码 else None
    frames = 提取周道帧(回溯对象, 行映射)

    lines: list[str] = []
    lines.append("═══ 周道运行时错误 ═══")
    if 额外说明:
        lines.append(额外说明)
    lines.append(f"异常类型: {type(原始异常).__name__}")
    lines.append(f"异常消息: {str(原始异常)}")

    if frames:
        lines.append("")
        lines.append("--- 回溯（已映射到周道源码）---")
        for i, (fname, py_line, func_name) in enumerate(frames):
            zd_pos, src_line = 映射行号(py_line, 行映射, 源码行列表)
            if zd_pos is not None:
                loc_str = f"第{zd_pos.行}行第{zd_pos.列}列"
                if func_name and func_name != '<module>':
                    lines.append(f"  [{i}] {func_name} 位于 {loc_str} (Python 行 {py_line})")
                else:
                    lines.append(f"  [{i}] 顶层 位于 {loc_str} (Python 行 {py_line})")
                if src_line is not None:
                    lines.append(f"       ╰ 周道原码: {src_line}")
                    # 生成列指示器（^），定位到错误表达式起始位置
                    col = max(0, zd_pos.列 - 1)
                    col = min(col, len(src_line))
                    lines.append(f"          {' ' * col}^")
            else:
                if func_name and func_name != '<module>':
                    lines.append(f"  [{i}] {func_name} 位于 Python 内部行 {py_line}（无周道映射）")
                else:
                    lines.append(f"  [{i}] Python 内部行 {py_line}（无周道映射）")

    lines.append("")
    lines.append("═══════════════════════")
    return '\n'.join(lines)


def 包装运行时异常(
    原始异常: BaseException,
    回溯对象,
    行映射: dict[int, 源码位置],
    源码: str | None = None,
    额外说明: str = "",
) -> 运行时错误:
    """将 Python 异常包装为周道运行时错误，携带周道源码位置映射。

    自动提取最后一个可映射帧的周道源码位置作为错误定位信息。

    Args:
        原始异常: 捕获的 Python 异常
        回溯对象: sys.exc_info()[2] 返回的回溯对象
        行映射: 生成行号 → 周道源码位置 的映射字典
        源码: 原始周道源码字符串（可选）
        额外说明: 附加说明文本

    Returns:
        携带完整回溯文本的 运行时错误 实例
    """
    frames = 提取周道帧(回溯对象, 行映射)

    # 找到最后一个（最内层）可映射帧的周道源码位置
    最后位置: 源码位置 | None = None
    for _, py_line, _ in reversed(frames):
        pos = 行映射.get(py_line)
        if pos is not None:
            最后位置 = pos
            break

    回溯文本 = 格式化回溯(原始异常, 回溯对象, 行映射, 源码, 额外说明)
    return 运行时错误(回溯文本, 位置=最后位置)
