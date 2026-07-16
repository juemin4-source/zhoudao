"""周道：错误类型与源码位置"""

from typing import NamedTuple


class 源码位置(NamedTuple):
    行: int
    列: int
    索引: int

    def 格式化(self) -> str:
        return f"第{self.行}行第{self.列}列"


class 周道错误(Exception):
    """所有周道错误的基类。"""

    def __init__(self, 消息: str, 位置: 源码位置 | None = None, 附近: str = ""):
        self.消息 = 消息
        self.位置 = 位置
        self.附近 = 附近
        前缀 = f"[{位置.格式化()}] " if 位置 else ""
        附近文本 = f"\n    附近：{附近}" if 附近 else ""
        super().__init__(f"{前缀}{消息}{附近文本}")


class 词法错误(周道错误):
    """词法分析阶段错误。"""
    pass


class 语法错误(周道错误):
    """语法分析阶段错误。"""
    pass


class 语义错误(周道错误):
    """语义分析阶段错误。"""
    pass


class 运行时错误(周道错误):
    """运行时错误。"""
    pass
