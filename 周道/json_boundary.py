"""周道 JSON 数据边界 — 严格解析与生成。

标准 JSON 负责外部交换；周道值负责内部计算。
转换严格、确定、可诊断。
"""

import json as _json
import math
from typing import Any

from .core_ir import (
    列表字面量IR, 元组字面量IR, 集合字面量IR,
    映射字面量IR, 文本常量IR,
)
from .errors import 周道错误


# ── 错误类型 ─────────────────────────────────────────────

class JSON解析错误(周道错误):
    """JSON 解析阶段错误。"""
    def __init__(self, 消息: str, 路径: str = "$", 行: int | None = None,
                 列: int | None = None, 附近: str = ""):
        self.路径 = 路径
        self.行 = 行
        self.列 = 列
        定位 = f"第{行}行第{列}列" if 行 and 列 else 路径
        附近文本 = f"\n  附近：{附近}" if 附近 else ""
        super().__init__(f"JSON解析错误：{消息}\n  位置：{定位}{附近文本}")


class JSON生成错误(周道错误):
    """JSON 生成阶段错误。"""
    def __init__(self, 消息: str, 路径: str = "$"):
        self.路径 = 路径
        super().__init__(f"无法生成JSON：{消息}\n  路径：{路径}")


# ── 安全整数范围 ─────────────────────────────────────────

_JS_SAFE_MAX = 9007199254740991
_JS_SAFE_MIN = -9007199254740991


def _是安全整数(值: int) -> bool:
    return _JS_SAFE_MIN <= 值 <= _JS_SAFE_MAX


# ── 非有限数检查 ─────────────────────────────────────────

def _是有限数(值: Any) -> bool:
    """检查是否为 Python 有限数值。"""
    if isinstance(值, float):
        return math.isfinite(值)
    return True


# ── 路径格式化 ───────────────────────────────────────────

def _转路径(片段: list) -> str:
    """将路径片段列表转为 JSONPath 字符串。"""
    path = "$"
    for seg in 片段:
        if isinstance(seg, int):
            path += f"[{seg}]"
        elif isinstance(seg, str):
            if seg.isidentifier() and not seg.startswith('"'):
                path += f".{seg}"
            else:
                path += f'["{seg}"]'
    return path


# ── 解析JSON ─────────────────────────────────────────────

class _严格解析器:
    """严格的 JSON 解析器，封装标准库并增强约束。"""

    def __init__(self, 文本: str):
        self.文本 = 文本
        self._检查重复键(文本)

    def _检查重复键(self, 文本: str):
        """检查顶层和嵌套对象中的重复键。"""
        # 使用 标准 json 的 object_pairs_hook 检测重复
        self._重复键错误 = None

        def _检测重复(pairs):
            seen = {}
            for k, v in pairs:
                if k in seen:
                    # 找到第二次出现的位置
                    pos = 文本.find(f'"{k}"', seen[k] + 1)
                    line = 文本[:pos].count("\n") + 1
                    col = pos - 文本[:pos].rfind("\n")
                    self._重复键错误 = (
                        f'JSON对象中重复出现键"{k}"。',
                        line, col
                    )
                seen[k] = 文本.find(f'"{k}"')
            return dict(pairs)

        try:
            _json.loads(文本, object_pairs_hook=_检测重复)
        except _json.JSONDecodeError as e:
            # 标准语法错误先抛出
            raise JSON解析错误(
                str(e), 行=e.lineno, 列=e.colno,
                附近=文本[max(0, e.pos-20):e.pos+10]
            ) from e

        if self._重复键错误:
            msg, line, col = self._重复键错误
            raise JSON解析错误(msg, 行=line, 列=col)

    def 解析(self) -> Any:
        """解析 JSON 文本为周道运行值。"""
        try:
            raw = _json.loads(self.文本)
        except _json.JSONDecodeError as e:
            raise JSON解析错误(
                str(e), 行=e.lineno, 列=e.colno,
                附近=self.文本[max(0, e.pos-20):e.pos+10]
            ) from e
        return self._转换(raw, [])

    def _转换(self, 值: Any, 路径: list) -> Any:
        """递归转换 Python 值为周道运行值（Python 原生类型）。"""
        if 值 is None:
            return None
        elif isinstance(值, bool):
            return 值
        elif isinstance(值, int):
            return 值
        elif isinstance(值, float):
            if not math.isfinite(值):
                raise JSON解析错误(
                    f"JSON值 {值} 不是有限数。",
                    路径=_转路径(路径)
                )
            if 值 == int(值):
                return int(值)
            return 值
        elif isinstance(值, str):
            return 值
        elif isinstance(值, list):
            return [self._转换(item, 路径 + [i]) for i, item in enumerate(值)]
        elif isinstance(值, dict):
            result = {}
            for k, v in 值.items():
                if not isinstance(k, str):
                    raise JSON解析错误(
                        f"JSON对象键不是文本：{k!r}",
                        路径=_转路径(路径)
                    )
                result[k] = self._转换(v, 路径 + [k])
            return result
        else:
            raise JSON解析错误(
                f"不支持的 JSON 值类型：{type(值).__name__}",
                路径=_转路径(路径)
            )


def 解析JSON(文本: str, *, 严格: bool = True) -> Any:
    """将 JSON 字符串解析为周道运行值。

    Args:
        文本: UTF-8 编码的 JSON 字符串
        严格: 为 True 时拒绝重复键、NaN 等

    Returns:
        周道运行值

    Raises:
        JSON解析错误: 解析失败时
    """
    parser = _严格解析器(文本)
    return parser.解析()


# ── 生成JSON ─────────────────────────────────────────────

def _生成值(值: Any, 路径: list, 缩进: int | None, 安全整数: bool) -> Any:
    """递归转换周道运行值为可 JSON 序列化的 Python 值。"""
    from .core_ir import (
        映射字面量IR, 列表字面量IR, 元组字面量IR, 集合字面量IR,
        文本常量IR, 整数常量IR, 小数常量IR, 布尔常量IR, 空值IR,
    )

    if 值 is None:
        return None
    elif isinstance(值, bool):
        return 值
    elif isinstance(值, int):
        if 安全整数 and not _是安全整数(值):
            raise JSON生成错误(
                f"值 {值} 超出 JavaScript 安全整数范围。"
                "建议将该值显式转换为文本。",
                路径=_转路径(路径)
            )
        return 值
    elif isinstance(值, float):
        if not math.isfinite(值):
            raise JSON生成错误(
                f"值 {值} 不是有限数。",
                路径=_转路径(路径)
            )
        return 值
    elif isinstance(值, str):
        return 值
    elif isinstance(值, (list, tuple)):
        if isinstance(值, tuple):
            raise JSON生成错误(
                "固定序列不允许直接生成 JSON。JSON 无法保留「固定」信息。"
                "请显式转换为列表。",
                路径=_转路径(路径)
            )
        return [_生成值(e, 路径 + [i], 缩进, 安全整数)
                for i, e in enumerate(值)]
    elif isinstance(值, dict):
        result = {}
        for k, v in 值.items():
            if not isinstance(k, str):
                raise JSON生成错误(
                    f"映射键不是文本：{k!r}",
                    路径=_转路径(路径)
                )
            result[k] = _生成值(v, 路径 + [k], 缩进, 安全整数)
        return result
    elif isinstance(值, set):
        raise JSON生成错误(
            "集合不允许直接生成 JSON。JSON 无法保留「唯一」约束。"
            "请显式排序或转换为列表。",
            路径=_转路径(路径)
        )
    # IR 类型回退（直接构造场景）
    elif isinstance(值, 列表字面量IR):
        return [_生成值(e, 路径 + [i], 缩进, 安全整数)
                for i, e in enumerate(值.元素)]
    elif isinstance(值, 映射字面量IR):
        result = {}
        for k, v in 值.条目:
            if not isinstance(k, 文本常量IR):
                raise JSON生成错误(
                    f"映射键不是文本：{k}",
                    路径=_转路径(路径)
                )
            result[k.值] = _生成值(v, 路径 + [k.值], 缩进, 安全整数)
        return result
    elif isinstance(值, (元组字面量IR, 集合字面量IR)):
        raise JSON生成错误(
            f"IR 类型不允许直接生成 JSON。请显式转换。",
            路径=_转路径(路径)
        )
    else:
        type_name = type(值).__name__
        raise JSON生成错误(
            f"「{type_name}」不允许直接生成 JSON。",
            路径=_转路径(路径)
        )


def 生成JSON(值: Any, *, 缩进: int | None = None,
              整数范围: str = "标准") -> str:
    """将周道运行值生成为 JSON 字符串。

    Args:
        值: 周道运行值
        缩进: 缩进空格数（None=紧凑输出）
        整数范围: "标准"（不限制）或 "JavaScript安全"

    Returns:
        JSON 字符串

    Raises:
        JSON生成错误: 遇到不可序列化的类型时
    """
    if 整数范围 not in ("标准", "JavaScript安全"):
        raise JSON生成错误(
            f"整数范围参数非法：{整数范围!r}，应为「标准」或「JavaScript安全」。"
        )

    安全整数 = 整数范围 == "JavaScript安全"
    py_value = _生成值(值, [], 缩进, 安全整数)

    return _json.dumps(
        py_value,
        ensure_ascii=False,
        indent=缩进,
        separators=(",", ":") if 缩进 is None else None,
    )


# ── 模块接口 ─────────────────────────────────────────────

__all__ = [
    "解析JSON", "生成JSON",
    "JSON解析错误", "JSON生成错误",
]
