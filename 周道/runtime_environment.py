"""周道运行时环境 — 运行时助手单一事实源。

本模块是运行时助手名称与对象的唯一注册表。
所有执行入口（Backend、ModuleLoader、Runner、CLI）必须从此处获取助手，
不得各自维护独立列表。

模块公开成员过滤也使用此处导出的名称集合。
"""

from __future__ import annotations


# ── 运行时助手注册表（唯一事实源） ──────────────────────────
# 新增加助手时只在此处添加，所有消费者自动生效

def _构建注册表() -> dict[str, object]:
    """延迟构建注册表，避免模块加载时产生循环导入。"""
    from .json_boundary import 解析JSON, 生成JSON
    from .method_aliases import 调用成员 as _zd_调用成员
    from .stdlib import 全部标准函数
    注册表 = {
        "_zd_调用成员": _zd_调用成员,
        "解析JSON": 解析JSON,
        "生成JSON": 生成JSON,
    }
    注册表.update(全部标准函数)
    return 注册表


_注册表缓存: dict[str, object] | None = None


def 获取注册表() -> dict[str, object]:
    """返回运行时助手注册表（惰性初始化）。"""
    global _注册表缓存
    if _注册表缓存 is None:
        _注册表缓存 = _构建注册表()
    return _注册表缓存


_内部助手前缀 = frozenset({
    "_zd_", "解析JSON", "生成JSON",

    "写入文本", "读取文本", "追加文本",
    "判断存在", "建立目录", "列出目录",
    "路径连接", "文件名", "扩展名",
    "删除文件", "复制文件", "移动文件",
    "CSV读取", "CSV写入",
    "正则查找", "正则查找全部", "正则替换", "正则匹配",
    "此刻时间", "今日日期", "格式时间", "休眠",
    "随机整数", "随机小数", "随机选择", "随机打乱",
    "命令行参数", "环境变量", "目前目录", "退出", "执行命令",
    "断言相等", "断言为真", "断言抛出错误",
})


def 获取助手名称集合() -> frozenset[str]:
    """返回内部运行时助手名称集合（不包含标准库函数）。"""
    return _内部助手前缀


def 注入运行时助手(环境: dict) -> None:
    """向执行环境注入全部运行时助手。"""
    环境.update(获取注册表())
    # 重写 str() 使 print(str(True)) 显示"真"而非"True"
    import builtins
    class _周道str:
        def __call__(self, val):
            if val is True: return "真"
            if val is False: return "假"
            if val is None: return "没有值"
            return builtins.str(val)
    环境["str"] = _周道str()
