"""周道内建方法别名注册表 — 统一事实源。

本文件是中文方法别名的唯一权威来源。
Parser、Backend、Runtime、Formatter 和测试不得分别维护重复表。

别名只在成员位置生效（对象。方法名（参数）），
不污染普通名称（分割（文本） 不会映射到 str.split）。

成员解析优先级：
  1. 对象真实存在的中文成员
  2. 内建方法别名（适用类型匹配时）
  3. 成员不存在 / 别名不适用错误

创建于 TASK-ZHOUDAO-SEED-012。
"""

from __future__ import annotations
import sys
from enum import Enum, auto


class 副作用类别(Enum):
    """方法副作用分类，用于文档和错误诊断。"""
    返回新值 = auto()
    原地修改 = auto()
    修改并返回 = auto()
    查询 = auto()
    视图 = auto()


# ── 别名注册表 — 唯一事实源 ──────────────────────────────
# 结构： { Python类型: { 中文别名: (Python成员名, 副作用类别) } }

文本别名: dict[str, tuple[str, 副作用类别]] = {
    "分割":     ("split",  副作用类别.返回新值),
    "连接":     ("join",   副作用类别.返回新值),
    "替换":     ("replace", 副作用类别.返回新值),
    "去除两端": ("strip",  副作用类别.返回新值),
    "从左去除": ("lstrip", 副作用类别.返回新值),
    "从右去除": ("rstrip", 副作用类别.返回新值),
    "开头是":   ("startswith", 副作用类别.查询),
    "结尾是":   ("endswith",   副作用类别.查询),
    "查找":     ("find",   副作用类别.查询),
    "计数":     ("count",  副作用类别.查询),
    "转为大写": ("upper",  副作用类别.返回新值),
    "转为小写": ("lower",  副作用类别.返回新值),
}

列表别名: dict[str, tuple[str, 副作用类别]] = {
    "追加":   ("append",  副作用类别.原地修改),
    "扩展":   ("extend",  副作用类别.原地修改),
    "插入":   ("insert",  副作用类别.原地修改),
    "移除":   ("remove",  副作用类别.原地修改),
    "弹出":   ("pop",     副作用类别.修改并返回),
    "排序":   ("sort",    副作用类别.原地修改),
    "反转":   ("reverse", 副作用类别.原地修改),
    "复制":   ("copy",    副作用类别.返回新值),
    "清空":   ("clear",   副作用类别.原地修改),
}

字典别名: dict[str, tuple[str, 副作用类别]] = {
    "取得":   ("get",        副作用类别.查询),
    "各键":   ("keys",       副作用类别.视图),
    "各值":   ("values",     副作用类别.视图),
    "各项":   ("items",      副作用类别.视图),
    "更新":   ("update",     副作用类别.原地修改),
    "弹出":   ("pop",        副作用类别.修改并返回),
    "设默认值": ("setdefault", 副作用类别.修改并返回),
    "复制":   ("copy",        副作用类别.返回新值),
    "清空":   ("clear",       副作用类别.原地修改),
}

集合别名: dict[str, tuple[str, 副作用类别]] = {
    "加入":   ("add",        副作用类别.原地修改),
    "移除":   ("remove",     副作用类别.原地修改),
    "丢弃":   ("discard",    副作用类别.原地修改),
    "联合":   ("union",      副作用类别.返回新值),
    "相交":   ("intersection", 副作用类别.返回新值),
    "复制":   ("copy",       副作用类别.返回新值),
    "清空":   ("clear",      副作用类别.原地修改),
}


# ── 统一查询接口 ──────────────────────────────────────────

# 类型 → 别名映射（运行时完整注册表）
_别名注册表: dict[type, dict[str, tuple[str, 副作用类别]]] = {
    str:  文本别名,
    list: 列表别名,
    dict: 字典别名,
    set:  集合别名,
}


def 取别名(obj: object, 中文名: str) -> str | None:
    """查询对象类型的中文方法别名对应的 Python 成员名。

    仅在对象真实不存在该中文成员时使用。
    返回 None 表示没有匹配别名。
    """
    映射 = _别名注册表.get(type(obj))
    if 映射 is None:
        return None
    条目 = 映射.get(中文名)
    if 条目 is None:
        return None
    return 条目[0]


def 取别名信息(中文名: str) -> list[tuple[type, str, 副作用类别]]:
    """反向查询：中文名可能对应哪些类型的哪些 Python 方法。

    用于诊断信息：当别名不适用于某类型时，可列出适用类型。
    """
    result = []
    for typ, 映射 in _别名注册表.items():
        条目 = 映射.get(中文名)
        if 条目:
            result.append((typ, 条目[0], 条目[1]))
    return result


def 是否已知别名(中文名: str) -> bool:
    """检查中文名是否在任意类型的别名表中。"""
    for 映射 in _别名注册表.values():
        if 中文名 in 映射:
            return True
    return False


# ── 运行时成员解析 ──────────────────────────────────────
# 统一的运行时入口：被 ast_backend 注入执行环境

_ERROR_TYPE_MAP = {
    "成员不存在": "AttributeError",
    "别名不适用": "TypeError",
    "成员不可调用": "TypeError",
    "参数错误": "TypeError",
}


class 成员解析错误(Exception):
    """周道成员解析运行时错误。携带中文诊断信息。"""
    def __init__(self, 消息: str, 错误类别: str = "成员不存在"):
        self.消息 = 消息
        self.错误类别 = 错误类别
        super().__init__(消息)


def 解析成员(obj: object, 名称: str) -> object:
    """统一运行时成员解析。

    顺序：
      1. 对象真实存在的成员
      2. 内建方法别名
      3. 成员不存在错误

    Args:
        obj: 目标对象
        名称: 周道成员名（可能是中文别名）

    Returns:
        解析到的属性值

    Raises:
        成员解析错误: 成员不存在且无匹配别名
    """
    # 1. 真实成员优先
    if hasattr(obj, 名称):
        return getattr(obj, 名称)

    # 2. 内建方法别名后备
    映射 = _别名注册表.get(type(obj))
    if 映射:
        条目 = 映射.get(名称)
        if 条目:
            py_name = 条目[0]
            return getattr(obj, py_name)

    # 3. 错误
    适用类型 = _适用类型提示(名称)
    提示 = f" 适用类型：{适用类型}" if 适用类型 else ""
    raise 成员解析错误(
        f"对象不存在成员「{名称}」{提示}",
        "成员不存在",
    )


def 调用成员(obj: object, 名称: str, 参数: tuple = (), 制定参数: dict | None = None) -> object:
    """统一运行时成员调用。

    解析成员后验证可调用性，再执行调用。
    """
    attr = 解析成员(obj, 名称)
    if not callable(attr):
        raise 成员解析错误(
            f"成员「{名称}」存在但不可调用",
            "成员不可调用",
        )
    kwargs = 制定参数 or {}
    return attr(*参数, **kwargs)


def _适用类型提示(中文名: str) -> str:
    """生成别名适用类型的诊断提示。"""
    types = []
    for typ, 映射 in _别名注册表.items():
        if 中文名 in 映射:
            types.append(typ.__name__)
    return "、".join(types) if types else ""


def 所有别名() -> dict[str, list[str]]:
    """返回 中文名 → [适用类型名] 映射，用于诊断和报告。"""
    result: dict[str, list[str]] = {}
    for typ, 映射 in _别名注册表.items():
        for 中文, (py_name, _) in 映射.items():
            if 中文 not in result:
                result[中文] = []
            result[中文].append(f"{typ.__name__} → {py_name}")
    return result
