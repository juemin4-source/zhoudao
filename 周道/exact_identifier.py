"""周道 v0.0.3：ExactIdentifier — 标识符的精确表示。

本模块实现了歧义宪法 §1.6 和 IDENTIFIER-SPEC.md 中定义的 ExactIdentifier。
冻结规则：
- 名称由合法字符组成（不含 CJK 标点）
- 花括号内为精确名称（不识别关键字，非法字符仍然禁止）
- 不使用 AI/中文分词器/最长名称优先
- NFC 规范化用于去重
"""

from __future__ import annotations
import unicodedata
from dataclasses import dataclass
from .errors import 源码位置, 词法错误, 语义错误

# ── 完全关键字（始终不可作为标识符）─────────────────────────────
# 只包含句法基石和固定结构短语
完全关键字集: frozenset[str] = frozenset({
    "设", "使", "为", "变为", "就", "不然",
    "当", "一直", "从", "中", "每取一项记作",
    "尝试", "如果出错", "无论是否出错",
    "显示", "引入", "设置", "定义",
    "真", "假", "没有值",
    "跳出循环", "继续下一轮",
    "以", "为所得",
    "下文所用", "下文简称", "均指全局的", "指本定义外层的",
    "依", "分情形", "若为", "其余",
    "删去", "报错", "不作处理",
    "包括", "包括以下内容",
    "须", "不得", "否则报错",
    "就是", "不是", "本身",
    "依次给出", "等待", "完成", "的所得",
    "可以", "且", "或", "并非",
    "在", "不在",
})

# ── 以下短语是上下文关键字，不在完全关键字集中 ─────────────────
# "最后" – 仅当紧随"无论是否出错"时是关键字
# "所得" – 仅当"为所得"/"的所得"时是关键字部分
# "成立"/"不成立" – 仅当设/使/如果后时是关键字
# "类别" – 仅当"设置 标识符 类别"时是关键字
# "属于" – 自由标识符


# ── CJK 表意文字范围（不含标点）───────────────────────────────
_CJK_IDEOGRAPH = (
    (0x4E00, 0x9FFF),   # CJK 统一表意文字 基本区
    (0x3400, 0x4DBF),   # CJK 扩展 A
    (0x20000, 0x2A6DF), # CJK 扩展 B
    (0x2A700, 0x2B73F), # CJK 扩展 C
    (0x2B740, 0x2B81F), # CJK 扩展 D
    (0x2B820, 0x2CEAF), # CJK 扩展 E
    (0x30000, 0x3134F), # CJK 扩展 G
)

# CJK 标点范围（这些不是 ideographs，禁止在名称中使用）
_CJK_PUNCT = (
    (0x3000, 0x303F),   # CJK 符号和标点： 。、，．？！：；〃〄【】〖〗
    (0xFF00, 0xFFEF),   # 全角形式：！＂＃＄％＆＇（）＊＋，－．／：；＜＝＞？＠
    (0xFE30, 0xFE4F),   # CJK 兼容形式（竖排标点）
    (0xFE10, 0xFE1F),   # 竖排形式
)


def _是表意文字(ch: str) -> bool:
    """判断字符是否为 CJK 表意文字（汉字），不含标点符号。"""
    cp = ord(ch)
    for lo, hi in _CJK_IDEOGRAPH:
        if lo <= cp <= hi:
            return True
    return False


def _是合法名称字符(ch: str) -> bool:
    """判断字符是否为合法的标识符组成字符。

    允许：
    - CJK 表意文字（汉字）
    - 英文字母（a-z, A-Z）
    - 数字（0-9）
    - 下划线 (_)

    禁止：
    - CJK 标点（。，、；：？！【】｛｝（）等）
    - 全角字母/数字（必须用半角）
    - 数学符号、运算符
    - 空白、控制字符
    """
    # 优先排除全角字母数字（必须用半角）
    if 'ａ' <= ch <= 'ｚ' or 'Ａ' <= ch <= 'Ｚ':
        return False
    if '０' <= ch <= '９':
        return False
    if _是表意文字(ch):
        return True
    if 'a' <= ch <= 'z' or 'A' <= ch <= 'Z':
        return True
    if ch.isdigit():
        return True
    if ch == '_':
        return True
    return False


def _验证名称字符串(名称: str, 位置: 源码位置 | None = None) -> None:
    """检查一个字符串是否合法作为标识符名称。"""
    if not 名称:
        raise 词法错误("空标识符", 位置)

    first = 名称[0]
    if not (_是表意文字(first) or ('a' <= first <= 'z') or ('A' <= first <= 'Z') or first == '_'):
        raise 词法错误(
            f"标识符首字符非法：{first!r}",
            位置
        )

    for ch in 名称:
        if not _是合法名称字符(ch):
            raise 词法错误(
                f"标识符包含非法字符：{ch!r}",
                位置
            )


# ── NFC 规范化 ──────────────────────────────────────────────

def _nfc(s: str) -> str:
    """NFC 规范化（用于名称去重）。"""
    return unicodedata.normalize('NFC', s)


# ── ExactIdentifier ─────────────────────────────────────────

@dataclass(frozen=True)
class ExactIdentifier:
    """标识符的精确表示。

    冻结（不可变）且可哈希，可用作字典键。
    符合歧义宪法一名一指原则。

    构造参数:
        名称: 标识符文本（内部自动做 NFC 规范化）
        是否精确: True = 来自花括号提取
        源码范围: (起始索引, 结束索引) 或 None
    """

    名称: str
    是否精确: bool = False
    源码范围: tuple[int, int] | None = None

    def __post_init__(self):
        """构造后自动 NFC 规范化和全角字母纠正。"""
        # 1. NFC 规范化
        nfc = _nfc(self.名称)
        # 2. 全角字母数字 → 半角
        cleaned = []
        for ch in nfc:
            cp = ord(ch)
            if 0xFF21 <= cp <= 0xFF3A:      # 全角 A-Z
                cleaned.append(chr(cp - 0xFEE0))
            elif 0xFF41 <= cp <= 0xFF5A:    # 全角 a-z
                cleaned.append(chr(cp - 0xFEE0))
            elif 0xFF10 <= cp <= 0xFF19:    # 全角 0-9
                cleaned.append(chr(cp - 0xFEE0))
            else:
                cleaned.append(ch)
        normalized = ''.join(cleaned)
        if normalized != self.名称:
            object.__setattr__(self, '名称', normalized)
        # 强制 NFC
        final = _nfc(self.名称)
        if final != self.名称:
            object.__setattr__(self, '名称', final)

    def 验证(self, 位置: 源码位置 | None = None) -> None:
        """验证标识符合法性（字符集 + 关键字冲突）。"""
        _验证名称字符串(self.名称, 位置)

        # 关键字冲突检查（仅非精确名称）
        if not self.是否精确 and self.名称 in 完全关键字集:
            raise 语义错误(
                f"「{self.名称}」是完全关键字，不可作为标识符。"
                f"如需使用请加花括号：{{{self.名称}}}",
                位置
            )

    def __str__(self) -> str:
        描述 = "精确" if self.是否精确 else "普通"
        return f"ExactIdentifier({self.名称!r}, {描述})"

    def __repr__(self) -> str:
        return self.__str__()


# ── 标识符提取器 ────────────────────────────────────────────

class 标识符提取器:
    """从源码中提取 ExactIdentifier。

    实现歧义宪法 §1.6 和 IDENTIFIER-SPEC.md §1.2 的提取规则。
    提取后自动调用 验证()。
    """

    @staticmethod
    def 从源码提取(源码: str, 起始索引: int, 位置: 源码位置
                  ) -> tuple[ExactIdentifier | None, int]:
        if 起始索引 >= len(源码):
            return None, 起始索引

        ch = 源码[起始索引]

        # 规则 B：花括号精确标识符
        if ch in ('{', '｛'):
            return 标识符提取器._提取花括号精确名称(源码, 起始索引, 位置)

        # 规则 A：普通标识符提取
        if _是合法名称字符(ch) and not ch.isdigit():
            return 标识符提取器._提取普通标识符(源码, 起始索引, 位置)

        return None, 起始索引

    @staticmethod
    def _提取普通标识符(源码: str, 起始索引: int, 位置: 源码位置
                       ) -> tuple[ExactIdentifier, int]:
        i = 起始索引
        while i < len(源码) and _是合法名称字符(源码[i]):
            i += 1
        name = 源码[起始索引:i]
        标识 = ExactIdentifier(名称=name, 是否精确=False, 源码范围=(起始索引, i))
        标识.验证(位置)
        return 标识, i

    @staticmethod
    def _提取花括号精确名称(源码: str, 起始索引: int, 位置: 源码位置
                           ) -> tuple[ExactIdentifier, int]:
        开 = 源码[起始索引]
        闭 = '}' if 开 == '{' else '｝'

        i = 起始索引 + 1
        while i < len(源码) and 源码[i] != 闭:
            i += 1
        if i >= len(源码):
            raise 词法错误(f"花括号未闭合，缺少 {闭}", 位置)

        内文 = 源码[起始索引 + 1:i]
        i += 1  # 跳过闭括号

        # 空白检查：花括号内容前/中/后有空白 → 非法
        if 内文 != 内文.strip():
            raise 词法错误(
                f"花括号精确名称中不允许出现空白字符",
                位置
            )
        if not 内文:
            raise 词法错误("空花括号名称", 位置)

        标识 = ExactIdentifier(名称=内文, 是否精确=True, 源码范围=(起始索引, i))
        标识.验证(位置)
        return 标识, i
