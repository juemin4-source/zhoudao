# 表层保真模型 010.5 — 修订版 R1

> 版本：0.0.10.5-R1
> 状态：PRE_IMPLEMENTATION_DESIGN
> 修订：Token 拆分原文/语义值；SourceSpan 完整化；Trivia 唯一所有权；
>       Surface AST keyword-only；Lexer/Parser 注释责任边界。

---

## 一、问题陈述

当前管线在两个地方丢失了用户原始的书写信息：

1. **运算符表层丢失**：Parser 将 `加` 和 `+` 归一为内部 `"+"`，Formatter 无法知道原来写的是汉语还是符号，只能单向输出汉语。
2. **注释丢失**：Parser 入口过滤 COMMENT Token，AST 不含任何注释信息，Formatter 完全看不到它们。

两者根源相同：**Surface 层没有保存「用户怎样写」，Core 层又不需要「用户怎样写」，但 Formatter（和 LSP）需要。**

---

## 二、分层原则

```
源码字符串
    ↓ Lexer
Token 流（原文 + 语义值 + SourceSpan + 前导 Trivia）
    ↓ Parser
Surface AST（语义 + 表层写法 + 源码位置 + 附着 Trivia）
    ↓ Lowering（有损降级）
Core IR（纯语义，无表层信息，无 Trivia）
    ↓ Emitter / AST Backend
Python AST / Python 源码
```

| 层 | 保存什么 | 不保存什么 |
|----|---------|-----------|
| Lexer Token | 原文、语义值、SourceSpan、前导 Trivia | 语义结构（尚未解析） |
| Surface AST | 归一语义 + **表层写法** + 源码位置 + 附着 Trivia | Python 执行细节 |
| Core IR | 纯语义（算符字符串、变量名等） | 源码写法、注释、位置 |
| Emitter 输出 | Python 源码 | 周道表层信息 |

**关键契约：**
- **Surface AST → Core IR**：信息有损降级。降级后无法恢复用户原始写法。
- **Formatter 输入是 Surface AST**，不是 Core IR。
- **LSP 输入包括 Token 流和 Surface AST**。
- **Core IR 与语义分析器** 不需要表层信息。

---

## 三、Token 结构（修订）

### 3.1 SourceSpan

当前 `源码位置` 只有起始位置。需要完整跨度以支持 LSP 高亮、诊断列号、多字符运算符等。

```python
@dataclass
class SourceSpan:
    行: int
    列: int      # 起始列（1-based），以 Python 字符索引为单位
    长度: int    # 字符长度（** 为 2，>= 为 2，加 为 1）
    文件: str = ""

    @property
    def 结束列(self) -> int:
        return self.列 + self.长度  # 左闭右开

    def 转LSP范围(self) -> dict:
        """LSP 输出时转换为 UTF-16 code units。

        Python 字符串索引以 Unicode 码位为单位，与 UTF-16 在 BMP 范围内一致。
        但对于包含 emoji（🍺）、扩展汉字（𠀀）等 4 字节字符的源码，
        一个 Python 字符可能对应 2 个 UTF-16 code units。
        此处做长度换算。
        """
        utf16_列 = self._码位列到UTF16(self.列)
        utf16_长度 = self._计算UTF16长度()
        return {
            "line": self.行 - 1,
            "start": utf16_列,
            "end": utf16_列 + utf16_长度,
        }
```

**跨度规则：**
- 左闭右开：`列` 到 `列 + 长度` 是实际字符范围
- `列 + 长度` 不一定是下一个 Token 的 `列`（中间可能有空白/Trivia）
- Python 字符索引单位：`len("**") == 2`，`len("加") == 1`
- LSP 输出时统一转换为 UTF-16 code units
- 多字符符号长度均为 2：`**` `//` `!=` `<=` `>=`
- 负数字面量 `负3`：第一个 Token（WORD_NEG）长度 1，第二个 Token（NUMBER）长度 1

### 3.2 Token 拆分原文和语义值

**当前设计问题**：`Token.值` 同时承担「原文」和「语义值」两个角色。`加` 时是 `"加"`，`+` 时是 `"+"`，数字 `3` 时又是 `3`。

**修订**：

```python
@dataclass
class Token:
    token_type: str         # OP_ADD / SYM_ADD / NUMBER 等
    原文: str               # 源码中的原始文本："加" / "+" / "负3" / "3"
    语义值: object          # 归一语义值："+" / "+" / -3 / 3
    跨度: SourceSpan        # 完整位置信息
    是否精确: bool = False  # 来自花括号精确名称

    @property
    def 值(self) -> str:
        """兼容旧代码：返回原文（逐步弃用）"""
        return self.原文
```

示例：

```
Token(OP_ADD,       原文="加", 语义值="+",  跨度=SourceSpan(1,4,1))
Token(SYM_ADD,      原文="+", 语义值="+",  跨度=SourceSpan(1,4,1))
Token(WORD_NEG,     原文="负", 语义值="-", 跨度=SourceSpan(1,4,1))
Token(NUMBER,       原文="3",  语义值=3,    跨度=SourceSpan(1,5,1))
Token(SYM_SUB,      原文="-", 语义值="-", 跨度=SourceSpan(1,4,1))
Token(NUMBER,       原文="3",  语义值=3,    跨度=SourceSpan(1,5,1))
Token(NUMBER,       原文="42", 语义值=42,  跨度=SourceSpan(1,4,2))
Token(OP_FLOOR_DIV, 原文="整除", 语义值="//", 跨度=SourceSpan(1,4,2))
Token(SYM_FLOOR_DIV,原文="//",  语义值="//",  跨度=SourceSpan(1,4,2))
Token(SYM_POW,      原文="**", 语义值="**", 跨度=SourceSpan(1,4,2))
```

注意：
- `负3` 是两个 Token：`WORD_NEG(原文="负")` + `NUMBER(原文="3")`
- `-3` 是两个 Token：`SYM_SUB(原文="-")` + `NUMBER(原文="3")`
- `负数` 是单个 IDENTIFIER（不是一元运算）
- `**` `//` `!=` `<=` `>=` 长度均为 2

Parser 保存表层时读取 `原文`，建立语义时读取 `语义值`。

### 3.3 Trivia 唯一所有权

**当前设计问题**：给每个 Token 同时增加 `前导空白` 和 `尾随空白`，会导致两个相邻 Token 对同一段空格主张所有权。

**修订**：Trivia 只附着于**后随 Token 的前导**，唯一所有权。

```python
class TriviaKind(Enum):
    WHITESPACE = "WHITESPACE"    # 空格、制表符
    LINE_BREAK = "LINE_BREAK"    # 换行
    COMMENT = "COMMENT"          # 注：…… 到行末
    FILE_END = "FILE_END"        # 文件末尾空白

@dataclass
class Trivia:
    类型: TriviaKind
    原文: str
    跨度: SourceSpan
```

Token 只持有前导 Trivia：

```python
@dataclass
class Token:
    token_type: str
    原文: str
    语义值: object
    跨度: SourceSpan
    是否精确: bool = False
    前导Trivia: list[Trivia] = field(default_factory=list)
```

**所有权规则**（下阶段 010.5-B 实现注释附着时使用）：

| 源码片段 | 所有权 |
|---------|--------|
| `甲` 和 `乙` 之间的空格 | 属于 `乙` 的前导 Trivia |
| 行首缩进 | 属于行首 Token 的前导 Trivia |
| 语句后的行尾注释 | 属于该语句末尾 Token 的前导 Trivia（换行前的最后一个 Token） |
| 定义前的连续注释 | 属于 `定义` Token 的前导 Trivia |
| 文件头注释 | 属于第一个 Token 的前导 Trivia |
| 文件尾空白 | 属于特殊的 EOF Token 的前导 Trivia。由于 EOF Token 在 Token 流末尾始终存在，文件尾空白/注释总能找到归属 |

**文件头与文件尾 Trivia 预留出口：**

```python
@dataclass
class SurfaceDocument:
    """Surface 层完整文档（010.5-B 扩展）。"""
    tokens: list[Token]
    ast: 程序
    # 以下为 010.5-B 预留：
    文件头Trivia: list[Trivia] = field(default_factory=list)   # 第一个 Token 的第一个 Trivia 之前的内容
    文件尾Trivia: list[Trivia] = field(default_factory=list)   # 最后一个非 EOF Token 之后的 Trivia
```

当前阶段（010.5-A）：不实现 `SurfaceDocument`，Trivia 只填充 WHITESPACE/LINE_BREAK（不含 COMMENT）。

**行尾注释归属问题明确延后：**

行尾注释（`显示结果。 注：输出结果`）在 010.5-A 阶段不解决。如果行尾注释出现在 `。` 之后的同一行，其归属（是 `显示` 语句的尾随说明、还是下一行 Token 的前导）留到 010.5-B 正式设计。

Lexer 识别 COMMENT Token，但不在 Lexer 阶段将其填入 Trivia 字段。Lexer 只负责将 COMMENT 作为独立 Token 发出。Parser 在构建 AST 时，将 COMMENT Token 转换为 Trivia 并附着到相邻的非 COMMENT Token 上。

当前阶段（010.5-A）不实现注释附着，Token 结构预留 `前导Trivia` 字段，但只填充 WHITESPACE 和 LINE_BREAK 类型，COMMENT 类型的填充延后到 010.5-B。

---

## 四、Surface AST 扩展（修订）

### 4.1 keyword-only 约束

**当前设计问题**：给 `二元运算` 追加 `表层算符` 普通字段，会导致 `二元运算(左, 右)` 等旧位置参数静默赋值给新字段。

**修订**：所有新字段必须 `keyword-only`，配合哨兵测试：

```python
@dataclass
class 二元运算(表达式):
    左: "表达式"
    算符: str
    右: "表达式"
    表层算符: str = field(default="", kw_only=True)
    位置: 源码位置 | None = field(default=None, kw_only=True)
```

**哨兵测试**（加入回归套件）：

```python
def test_二元运算_位置参数不偏移():
    """旧的位置参数构造仍产生正确结果。"""
    node = 二元运算(整数(3), "+", 整数(5))
    assert node.算符 == "+"
    assert node.表层算符 == ""

def test_二元运算_keyword表层():
    node = 二元运算(整数(3), "+", 整数(5), 表层算符="加")
    assert node.表层算符 == "加"
```

### 4.2 具体扩展（负号改为一元运算）

**修订**：撤回 `整数.表层文本`。负号（无论 `负` 还是 `-`）都进入一元运算节点。

```python
@dataclass
class 一元运算(表达式):
    算符: str         # 归一："-" 或 "not"
    操作数: "表达式"
    表层算符: str = field(default="", kw_only=True)  # "负" 或 "-" 或 ""
```

示例：

```
负3     → 一元运算("-", 整数(3), 表层算符="负")
-3      → 一元运算("-", 整数(3), 表层算符="-")
负数量  → 标识符("负数量") ← 不是运算
```

这样 `负2 ** 2` → `一元运算("-", ..., 表层算符="负") ** 整数(2)` → `-(2**2)` = `-4` ✅

唯一开放的默认值场景：翻译器生成的 AST 无表层算符，此时 `表层算符=""`，Formatter 回退到 `算符`。

### 4.3 需要保留表层信息的节点

```python
# 二元运算 —— 运算符表层
@dataclass
class 二元运算(表达式):
    左: "表达式"
    算符: str          # 归一："+", "-", "*", "/", "//", "%", "**", ...
    右: "表达式"
    表层算符: str = field(default="", kw_only=True)

# 一元运算 —— 负号表层
@dataclass
class 一元运算(表达式):
    算符: str          # 归一："-", "not"
    操作数: "表达式"
    表层算符: str = field(default="", kw_only=True)

# 整数 —— 数字原文表层（仅用于字面量写法本身，不承载负号）
@dataclass
class 整数(表达式):
    值: int
    表层文本: str = field(default="", kw_only=True)  # "42" / "0xFF"（保留给未来进制）
```

`整数.表层文本` 只保存数字本身的写法（如 `0xFF` vs `255`），不保存负号。负号属于一元运算。

---

## 五、Lowering 规则

Surface AST → Core IR 时丢弃表层信息：

```python
def _降低二元运算(self, 节点: 二元运算) -> 二元运算IR:
    return 二元运算IR(
        左=self._降低表达式(节点.左),
        算符=节点.算符,             # 只保留归一语义算符
        右=self._降低表达式(节点.右),
    )
    # 表层算符、位置（通过位置映射侧表）、Trivia 均丢弃
```

---

## 六、Lexer 与 Parser 注释责任边界

| 阶段 | 责任 |
|------|------|
| Lexer | 识别 `注：` → 发出 COMMENT Token（原文+跨度）；识别空白/换行 → **暂不**生成 Trivia |
| Parser（010.5-A） | 过滤 COMMENT Token（当前行为，不变） |
| Parser（010.5-B） | 将 COMMENT Token 转换为 `Trivia(COMMENT)` 并附着到相邻的非 COMMENT Token 的 `前导Trivia` 列表 |

当前阶段（010.5-A）不实现注释附着。`前导Trivia` 字段预留但不填充 COMMENT。

---

## 七、Formatter 如何使用（修订）

### 7.1 算符渲染规则

Formatter **不直接输出 `表层算符` 原文**。它输出的是**运算符类别**（汉语式 vs 符号式），并统一控制间距。

```python
_汉语式 = {
    "+": "加", "-": "减", "*": "乘", "/": "除",
    "==": "等于", "!=": "不等于",
    ">": "大于", "<": "小于", ">=": "不少于", "<=": "不多于",
    "**": "**", "//": "//", "%": "%",  # 无双表层
}

_符号式 = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "==": "=", "!=": "!=",
    ">": ">", "<": "<", ">=": ">=", "<=": "<=",
    "**": "**", "//": "//", "%": "%",
}
```

`preserve` 模式根据 `表层算符` 判断风格：

```python
def _判断风格(self, 表层算符: str) -> str:
    """根据表层算符判断用户使用的风格。"""
    if not 表层算符:
        return self._默认风格  # 项目配置或 symbolic 回退
    # 汉语运算符全是中文，符号运算符全是 ASCII
    return "verbal" if 表层算符 and ord(表层算符[0]) >= 0x4e00 else "symbolic"
```

### 7.2 preserve 模式

```
输入：设结果为甲加乙。
表层算符="加" → 风格=verbal → 输出：设结果为甲加乙。

输入：设结果为甲 + 乙。
表层算符="+" → 风格=symbolic → 输出：设结果为甲 + 乙。
```

### 7.3 verbal 模式

```
甲 + 乙 → 甲加乙
甲 - 乙 → 甲减乙
甲 = 乙 → 甲等于乙
甲 ** 乙 → 甲 ** 乙   ← 无双表层，仍输出符号
甲 // 乙 → 甲 // 乙   ← 同上
-3 → 负3
```

### 7.4 symbolic 模式

```
甲加乙 → 甲 + 乙
甲减乙 → 甲 - 乙
甲等于乙 → 甲 = 乙
负3 → -3
```

### 7.5 间距规则（统一，与模式无关）

```python
def 渲染二元运算(self, 节点, 模式):
    算符文 = self._选算符(节点.算符, 节点.表层算符, 模式)
    if ord(算符文[0]) >= 0x4e00:
        # 汉语式：不加空格
        self._写(节点.左); self._写(算符文); self._写(节点.右)
    else:
        # 符号式：两侧各一个半角空格
        self._写(节点.左); self._写(" "); self._写(算符文); self._写(" "); self._写(节点.右)
```

### 7.6 负号三模式

```
preserve:
  表层算符="负" → 负3
  表层算符="-"  → -3
  空 → 回退 symbolic（-3）

verbal:
  -3 → 负3
  表层算符忽略

symbolic:
  负3 → -3
  表层算符忽略
```

### 7.7 优先级感知的括号

三模式转换必须保证 `parse(format(ast))` 与原 AST 语义等价。

当前不需要在 Formatter 中智能增减括号——如果源码中写了括号，`表层算符` 机制无法保留括号本身（括号不是 Token，是语法结构）。所以：

- Formatter 不主动增减括号
- 括号由源码中的显式 `（` `）` 确定
- 三模式只换算符，不涉及括号的添加或删除
- 语义等价测试跑 `转译` 后的 Python 执行结果，而非源码字符串比较

---

## 八、LSP 如何使用

LSP 语义高亮通过 Token 的 `token_type` 前缀区分：

```
OP_*  → 汉语关键字色（青色/绿色）
SYM_* → 运算符色（橙色/黄色）
```

Operators 本身就是 Token，不需要从语义 Tokens 推：

| Token 类别 | 高亮色 | 语义类型 |
|-----------|--------|---------|
| `OP_ADD`, `OP_SUB`, `OP_EQ`… | 汉语关键字 | keyword |
| `SYM_ADD`, `SYM_SUB`, `SYM_EQ`… | 运算符 | operator |
| `OP_FLOOR_DIV`, `OP_MOD` | 汉语关键字(legacy) | keyword |
| `SYM_FLOOR_DIV`, `SYM_MOD` | 运算符 | operator |

---

## 九、与后续功能的关系

| 功能 | 阶段 | 依赖 |
|------|------|------|
| 运算符双表层 | 010.5-A（当前） | Token 结构、Surface AST、Formatter 三模式 |
| 注释保真 | 010.5-B | Trivia 结构、Lexer COMMENT Trivia、Parser 附着规则 |
| 结构指称 | 010.5-C | 焦点栈（语义分析层） |
| JSON 边界 | 010.5-D | 独立实现 |

---

## 十、架构决策记录

| 决策 | 选项 | 结果 |
|------|------|------|
| `Token.值` 拆分 | 原文+语义值 / 不拆 | **拆分**：原文=源码文本，语义值=归一值 |
| 跨度表示 | 起+终 / 起+长度 | **SourceSpan(行,列,长度)** |
| Trivia 所有权 | 前后各持 / 仅前导 | **仅前导，唯一归属后随 Token** |
| `表层算符` 字段方式 | 普通字段 / keyword-only | **keyword-only** |
| `负3` 模型 | 负整数节点 / 一元运算 | **一元运算** |
| `整数.表层文本` | 承载负号 / 不承载 | **不承载**，仅数字原文写法 |
| 注释附着阶段 | Lexer时 / Parser时 | **Parser时**（010.5-B） |
| Formatter preserve 保留粒度 | 原文空格 / 运算符类别 | **运算符类别**，间距由 Formatter 统一 |
| 括号保留 | 智能增减 / 不主动增减 | **不主动增减**，等价性通过运行结果验证 |
