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
    行映射: dict[int, 源码位置] | None = None,
    *,
    模块行映射: dict[str, dict[int, 源码位置]] | None = None,
    模块路径集: set[str] | None = None,
) -> list[tuple[str, int, str]]:
    """从回溯对象中提取所有周道帧。

    识别标准（任一即可）：
    1. co_filename == '<周道>'（单文件运行）
    2. co_filename 以 .zd 结尾（模块运行）
    3. co_filename 在模块路径集中

    Returns:
        [(co_filename, py_lineno, func_name), ...] 从外层到最内层
    """
    if 模块路径集 is None:
        模块路径集 = set()
    frames: list[tuple[str, int, str]] = []
    tb = 回溯对象
    while tb:
        f_code = tb.tb_frame.f_code
        co = f_code.co_filename
        if co == '<周道>' or co.endswith('.zd') or co in 模块路径集:
            frames.append((co, tb.tb_lineno, f_code.co_name))
        elif 模块行映射 and co in 模块行映射:
            frames.append((co, tb.tb_lineno, f_code.co_name))
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


def _分类TypeError(原始异常, 帧列表) -> str:
    """尝试区分调用边界 TypeError 和函数内部 TypeError。

    Returns:
        "call_boundary" — 错误发生在调用绑定阶段
        "internal" — 错误发生在函数体内部
        "unclear" — 无法可靠判断
    """
    if not isinstance(原始异常, TypeError):
        return "unclear"
    if len(帧列表) < 1:
        return "unclear"
    # 如果只有一帧，且该帧是调用帧：可能是参数错误
    # 如果有多帧，最深帧不同于调用帧：已进入函数体
    if len(帧列表) >= 2:
        return "internal"
    return "unclear"


def 包装运行时异常(
    原始异常: BaseException,
    回溯对象,
    行映射: dict[int, 源码位置] | None = None,
    源码: str | None = None,
    额外说明: str = "",
    *,
    模块行映射: dict[str, dict[int, 源码位置]] | None = None,
    模块路径集: set[str] | None = None,
) -> 运行时错误:
    """将 Python 异常包装为周道运行时错误，携带周道源码位置映射。"""
    frames = 提取周道帧(回溯对象, 行映射, 模块行映射=模块行映射, 模块路径集=模块路径集)

    # TypeError 分类
    _分类 = _分类TypeError(原始异常, frames)
    _分类标签 = ""
    if _分类 == "call_boundary":
        _分类标签 = " [调用参数错误]"
    elif _分类 == "internal":
        _分类标签 = " [函数内部异常]"

    # 框架帧过滤（保留用户可见帧列表的全量副本用于调试）
    内部前缀 = ("runner.py", "ast_backend.py", "module_loader.py",
                 "runtime_traceback.py", "method_aliases.py", "<frozen")
    用户帧 = [f for f in frames if not any(p in f[0] for p in 内部前缀)]

    # 找到最后一个可映射帧的周道源码位置
    最后位置: 源码位置 | None = None
    for co_name, py_line, _ in reversed(用户帧 or frames):
        pos = None
        if 行映射 and (co_name == '<周道>' or co_name in (模块行映射 or {})):
            pos = 行映射.get(py_line) if co_name == '<周道>' else None
        if pos is None and 模块行映射:
            for fpath, mapping in 模块行映射.items():
                if co_name == fpath or co_name.endswith(fpath.split('/')[-1]):
                    pos = mapping.get(py_line)
                    if pos:
                        break
        if pos is not None:
            最后位置 = pos
            break

    # 构建诊断消息（含分类、用户帧、原始异常信息）
    消息 = f"═══ 周道运行时错误 ═══{_分类标签}\n"
    消息 += f"异常类型: {type(原始异常).__name__}\n"
    消息 += f"异常消息: {原始异常}"
    if _分类 == "call_boundary":
        消息 += "\n诊断: 调用参数无法绑定（参数数量或签名不匹配）"
    elif _分类 == "internal":
        消息 += "\n诊断: 函数内部异常（已进入函数体后发生）"
    if 用户帧:
        消息 += "\n--- 周道调用链 ---"
        for i, (co_name, py_line, fn) in enumerate(用户帧):
            pos_str = f" ({最后位置.格式化()})" if 最后位置 and i == len(用户帧)-1 else ""
            消息 += f"\n  [{i}] {fn} @ {co_name}:{py_line}{pos_str}"
    # 添加源码上下文和列指示器（兼容既有测试）
    if 最后位置 and 源码:
        行列表 = 源码.split('\n')
        if 最后位置.行 <= len(行列表):
            src_line = 行列表[最后位置.行 - 1].rstrip()
            消息 += f"\n    周道原码: {src_line}"
            col = max(0, 最后位置.列 - 1)
            消息 += f"\n    {' ' * col}^"
    if len(frames) > len(用户帧):
        消息 += f"\n（已过滤 {len(frames)-len(用户帧)} 个内部框架帧）"

    return 运行时错误(消息, 位置=最后位置)
