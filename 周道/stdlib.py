"""周道基础能力库 — Gate B。

将 Python 标准库能力包装为周道可调用的函数。
所有函数通过 PreludeScope 或显式引入可用。
"""

from __future__ import annotations
import os, json, csv, re, datetime, random, sys, subprocess, math
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# B5: 路径、文件与目录
# ═══════════════════════════════════════════════════════════════

def 读取文本(路径: str, 编码: str = "utf-8") -> str:
    with open(路径, "r", encoding=编码) as f:
        return f.read()


def 写入文本(路径: str, 内容: str, 编码: str = "utf-8") -> None:
    with open(路径, "w", encoding=编码) as f:
        f.write(内容)


def 追加文本(路径: str, 内容: str, 编码: str = "utf-8") -> None:
    with open(路径, "a", encoding=编码) as f:
        f.write(内容)


def 判断存在(路径: str) -> bool:
    return os.path.exists(路径)


def 建立目录(路径: str) -> None:
    os.makedirs(路径, exist_ok=True)


def 列出目录(路径: str = ".") -> list[str]:
    return os.listdir(路径)


def 路径连接(基: str, *部分: str) -> str:
    return os.path.join(基, *部分)


def 文件名(路径: str) -> str:
    return os.path.basename(路径)


def 扩展名(路径: str) -> str:
    return os.path.splitext(路径)[1]


def 删除文件(路径: str) -> None:
    os.remove(路径)


def 复制文件(源: str, 目标: str) -> None:
    import shutil
    shutil.copy2(源, 目标)


def 移动文件(源: str, 目标: str) -> None:
    import shutil
    shutil.move(源, 目标)


# ═══════════════════════════════════════════════════════════════
# B6: CSV
# ═══════════════════════════════════════════════════════════════

def CSV读取(路径: str, 编码: str = "utf-8") -> list[list[str]]:
    with open(路径, "r", encoding=编码, newline="") as f:
        return [row for row in csv.reader(f)]


def CSV写入(路径: str, 数据: list[list[str]], 编码: str = "utf-8") -> None:
    with open(路径, "w", encoding=编码, newline="") as f:
        writer = csv.writer(f)
        writer.writerows(数据)


# ═══════════════════════════════════════════════════════════════
# B7: 正则表达式
# ═══════════════════════════════════════════════════════════════

def 正则查找(模式: str, 文本: str) -> str | None:
    m = re.search(模式, 文本)
    return m.group(0) if m else None


def 正则查找全部(模式: str, 文本: str) -> list[str]:
    return re.findall(模式, 文本)


def 正则替换(模式: str, 替换: str, 文本: str) -> str:
    return re.sub(模式, 替换, 文本)


def 正则匹配(模式: str, 文本: str) -> bool:
    return bool(re.match(模式, 文本))


# ═══════════════════════════════════════════════════════════════
# B8: 日期与时间
# ═══════════════════════════════════════════════════════════════

def 此刻时间() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def 今日日期() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


def 格式时间(格式: str = "%Y-%m-%d %H:%M:%S") -> str:
    return datetime.datetime.now().strftime(格式)


def 休眠(秒: float) -> None:
    time.sleep(秒)


# ═══════════════════════════════════════════════════════════════
# B9: 随机
# ═══════════════════════════════════════════════════════════════

def 随机整数(最小值: int, 最大值: int) -> int:
    return random.randint(最小值, 最大值)


def 随机小数() -> float:
    return random.random()


def 随机选择(序列: list) -> object:
    return random.choice(序列)


def 随机打乱(序列: list) -> list:
    """返回打乱后的新列表，不修改原列表。"""
    result = list(序列)
    random.shuffle(result)
    return result


# ═══════════════════════════════════════════════════════════════
# B10: 系统
# ═══════════════════════════════════════════════════════════════

def 命令行参数() -> list[str]:
    return sys.argv


def 环境变量(名: str, 默认: str | None = None) -> str | None:
    return os.environ.get(名, 默认)


def 目前目录() -> str:
    return os.getcwd()


def 退出(码: int = 0) -> None:
    sys.exit(码)


def 执行命令(命令: str) -> str:
    """执行外部命令并返回 stdout。"""
    try:
        result = subprocess.run(命令, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "(超时)"


SOFTILLS_DIR = os.path.abspath(
    r"G:\AI\Soma-trinity-lab\components\soma\07-verified-softills"
)


def 调用软技能(技能名: str, 输入: dict = None) -> dict:
    """调用 MCP softill，返回解析后的 JSON 结果。

    用法（周道中）：
        设 结果 = 调用软技能「code-search」以 { 模式: "loading" }
    """
    import subprocess as _sp

    技能目录 = os.path.join(SOFTILLS_DIR, 技能名)
    handler_js = os.path.join(技能目录, "handler.js")
    handler_mjs = os.path.join(技能目录, "handler.mjs")
    handler = handler_js if os.path.exists(handler_js) else handler_mjs

    if not os.path.exists(handler):
        return {"result": "ERROR", "summary": f"未找到软技能：{技能名}", "data": {}}

    输入JSON = json.dumps(输入 or {}, ensure_ascii=False)
    try:
        result = _sp.run(
            ["node", handler, "--"],
            input=输入JSON,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
        )
        # 从 stdout 中提取 JSON
        输出 = result.stdout
        起始 = 输出.find("{")
        if 起始 < 0:
            return {"result": "ERROR", "summary": "无 JSON 输出", "data": {}}

        数据 = json.loads(输出[起始:])

        # 统一输出格式：补齐缺失的 softill/evidence/result/summary 字段
        if "softill" not in 数据:
            数据["softill"] = 技能名
        if "evidence" not in 数据:
            数据["evidence"] = []
        if "result" not in 数据:
            数据["result"] = "PASS" if result.returncode == 0 else "ERROR"
        if "summary" not in 数据:
            数据["summary"] = "ok"
        if "data" not in 数据:
            数据["data"] = {}

        return 数据
    except _sp.TimeoutExpired:
        return {"result": "ERROR", "summary": "软技能调用超时", "data": {}}
    except Exception as e:
        return {"result": "ERROR", "summary": str(e), "data": {}}


# ═══════════════════════════════════════════════════════════════
# 注册表：用于自动注入到 Prelude 环境
# ═══════════════════════════════════════════════════════════════

B5函数 = {
    "读取文本": 读取文本, "写入文本": 写入文本, "追加文本": 追加文本,
    "判断存在": 判断存在, "建立目录": 建立目录, "列出目录": 列出目录,
    "路径连接": 路径连接, "文件名": 文件名, "扩展名": 扩展名,
    "删除文件": 删除文件, "复制文件": 复制文件, "移动文件": 移动文件,
}

B6函数 = {"CSV读取": CSV读取, "CSV写入": CSV写入}

B7函数 = {
    "正则查找": 正则查找, "正则查找全部": 正则查找全部,
    "正则替换": 正则替换, "正则匹配": 正则匹配,
}

B8函数 = {
    "此刻时间": 此刻时间, "今日日期": 今日日期,
    "格式时间": 格式时间, "休眠": 休眠,
}

B9函数 = {
    "随机整数": 随机整数, "随机小数": 随机小数,
    "随机选择": 随机选择, "随机打乱": 随机打乱,
}

B10函数 = {
    "命令行参数": 命令行参数, "环境变量": 环境变量,
    "目前目录": 目前目录, "退出": 退出, "执行命令": 执行命令,
    "调用软技能": 调用软技能,
}

# ═══════════════════════════════════════════════════════════════
# D5: 测试断言
# ═══════════════════════════════════════════════════════════════

def 断言相等(实际, 期望) -> None:
    assert 实际 == 期望, f"断言相等失败: 实际={实际!r}, 期望={期望!r}"


def 断言为真(条件) -> None:
    assert 条件, "断言为真失败"


def 断言抛出错误(能力, *参数) -> None:
    """调用能力并断言抛出异常。"""
    import sys
    try:
        能力(*参数)
    except Exception:
        pass  # expected
    else:
        raise AssertionError(f"断言抛出错误失败: 未抛出异常")


D5函数 = {
    "断言相等": 断言相等, "断言为真": 断言为真, "断言抛出错误": 断言抛出错误,
}

全部标准函数: dict[str, object] = {}
全部标准函数.update(D5函数)
全部标准函数.update(B5函数)
全部标准函数.update(B6函数)
全部标准函数.update(B7函数)
全部标准函数.update(B8函数)
全部标准函数.update(B9函数)
全部标准函数.update(B10函数)

# ═══════════════════════════════════════════════════════════════
# V1: 动词优先调用 — 文本能力（纯处理，不修改原数据）
# ═══════════════════════════════════════════════════════════════

def 去除两端(文本: str) -> str:
    """返回去除两端空白的新文本。纯处理。"""
    return 文本.strip()


def 分割(文本: str, 分隔符: str | None = None) -> list[str]:
    """按分隔符分割文本为列表。纯处理。"""
    return 文本.split(分隔符) if 分隔符 else 文本.split()


def 替换(文本: str, 旧内容: str, 新内容: str) -> str:
    """替换文本中的内容。纯处理。"""
    return 文本.replace(旧内容, 新内容)


def 查找(文本: str, 目标: str) -> int:
    """查找目标位置。返回索引或 -1。纯处理。"""
    return 文本.find(目标)


def 计数(文本: str, 目标: str) -> int:
    """统计目标出现次数。纯处理。"""
    return 文本.count(目标)


def 转为大写(文本: str) -> str:
    """返回全大写新文本。纯处理。"""
    return 文本.upper()


def 转为小写(文本: str) -> str:
    """返回全小写新文本。纯处理。"""
    return 文本.lower()


def 开头是(文本: str, 内容: str) -> bool:
    """判断开头是否匹配。纯处理。"""
    return 文本.startswith(内容)


def 结尾是(文本: str, 内容: str) -> bool:
    """判断结尾是否匹配。纯处理。"""
    return 文本.endswith(内容)


def 去除空白(文本: str) -> str:
    """同去除两端。纯处理。"""
    return 文本.strip()


def 连接(列表: list, 分隔符: str = "") -> str:
    """将列表用分隔符连为文本。纯处理。"""
    return 分隔符.join(列表)


# ═══════════════════════════════════════════════════════════════
# V2: 动词优先调用 — 列表能力
# ═══════════════════════════════════════════════════════════════

def 排序(列表: list) -> list:
    """返回排序后的新列表。纯处理，不修改原列表。"""
    return sorted(列表)


def 原地排序(列表: list) -> None:
    """直接修改原列表为排序状态。修改型。"""
    列表.sort()


def 反转(列表: list) -> list:
    """返回反转后的新列表。纯处理。"""
    return list(reversed(列表))


def 原地反转(列表: list) -> None:
    """直接修改原列表为反转状态。修改型。"""
    列表.reverse()


def 追加(列表: list, 项目) -> None:
    """向列表末尾追加项目。修改型。"""
    列表.append(项目)


def 插入(列表: list, 位置: int, 项目) -> None:
    """在指定位置插入项目。修改型。"""
    列表.insert(位置, 项目)


def 移除(列表: list, 项目) -> None:
    """移除第一个匹配的项目。修改型。"""
    列表.remove(项目)


def 弹出(列表: list, 位置: int = -1):
    """弹出指定位置的项目。修改型并返回值。"""
    return 列表.pop(位置)


def 扩展(列表: list, 另一列表: list) -> None:
    """扩展列表。修改型。"""
    列表.extend(另一列表)


def 复制列表(列表: list) -> list:
    """返回列表的浅复制。纯处理。"""
    return 列表.copy()


def 清空(列表: list) -> None:
    """清空列表内容。修改型。"""
    列表.clear()


# ═══════════════════════════════════════════════════════════════
# V3: 动词优先调用 — 映射能力
# ═══════════════════════════════════════════════════════════════

def 取得(映射: dict, 键, 默认=None):
    """获取键对应的值。纯处理。"""
    return 映射.get(键, 默认)


def 设默认值(映射: dict, 键, 值):
    """键不存在时设值。修改型。"""
    return 映射.setdefault(键, 值)


def 更新(映射: dict, 另一映射: dict) -> None:
    """用另一映射更新当前映射。修改型。"""
    映射.update(另一映射)


def 弹出映射(映射: dict, 键):
    """弹出键对应的值。修改型并返回值。"""
    return 映射.pop(键)


def 各键(映射: dict) -> list:
    """返回所有键的列表。纯处理。"""
    return list(映射.keys())


def 各值(映射: dict) -> list:
    """返回所有值的列表。纯处理。"""
    return list(映射.values())


def 各项(映射: dict) -> list:
    """返回所有(键,值)对的列表。纯处理。"""
    return list(映射.items())


def 清空映射(映射: dict) -> None:
    """清空映射。修改型。"""
    映射.clear()


def 包含键(映射: dict, 键) -> bool:
    """判断是否包含键。纯处理。"""
    return 键 in 映射


# ═══════════════════════════════════════════════════════════════
# V4: 动词优先调用 — 集合能力
# ═══════════════════════════════════════════════════════════════

def 加入(集合: set, 元素) -> None:
    """向集合添加元素。修改型。"""
    集合.add(元素)


def 移除集合(集合: set, 元素) -> None:
    """从集合移除元素。修改型。"""
    集合.remove(元素)


# 动词调用注册表
V1文本函数 = {
    "去除两端": 去除两端, "分割": 分割, "替换": 替换,
    "查找": 查找, "计数": 计数,
    "转为大写": 转为大写, "转为小写": 转为小写,
    "开头是": 开头是, "结尾是": 结尾是,
    "去除空白": 去除空白, "连接": 连接,
}

V2列表函数 = {
    "排序": 排序, "原地排序": 原地排序,
    "反转": 反转, "原地反转": 原地反转,
    "追加": 追加, "插入": 插入, "移除": 移除,
    "弹出": 弹出, "扩展": 扩展,
    "复制列表": 复制列表, "清空": 清空,
}

V3映射函数 = {
    "取得": 取得, "设默认值": 设默认值, "更新": 更新,
    "弹出映射": 弹出映射,
    "各键": 各键, "各值": 各值, "各项": 各项,
    "清空映射": 清空映射, "包含键": 包含键,
}

V4集合函数 = {
    "加入": 加入, "移除集合": 移除集合,
}

全部标准函数.update(V1文本函数)
全部标准函数.update(V2列表函数)
全部标准函数.update(V3映射函数)
全部标准函数.update(V4集合函数)

