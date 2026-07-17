# 表达式层实施 v3 — 修订版 R1

> 基于双表层裁决 + 首轮审计修订。
> 依赖前置文档：`SURFACE-PRESERVATION-MODEL-0105.md`
> 关键修订：负3 改为一元运算；SYM_* 无分叉；全角括号统一；Formatter 空格规则。

---

## 一、双表层精确范围

### 1.1 正式双表层（汉语式 + 数学符号，完全等价）

| 语义 | 汉语式 | 数学符号 |
|------|--------|---------|
| 加法 | `甲加乙` | `甲 + 乙` |
| 减法 | `甲减乙` | `甲 - 乙` |
| 乘法 | `甲乘乙` | `甲 * 乙` |
| 除法 | `甲除乙` | `甲 / 乙` |
| 相等 | `甲等于乙` | `甲 = 乙` |
| 不等 | `甲不等于乙` | `甲 != 乙` |
| 大于 | `甲大于乙` | `甲 > 乙` |
| 小于 | `甲小于乙` | `甲 < 乙` |
| 大于等于 | `甲不少于乙` | `甲 >= 乙` |
| 小于等于 | `甲不多于乙` | `甲 <= 乙` |

### 1.2 一元负号双表层

| 语义 | 汉语式 | 数学符号 |
|------|--------|---------|
| 数值取负 | `负3` | `-3` |
| 变量取负 | —（不开放通用汉语一元） | `-数量` |
| 表达式取负 | —（暂不开放） | `-（甲 + 乙）` |

`负数量` 是普通标识符，不是一元运算。

### 1.3 符号优先

| 语义 | 符号式 | 汉语 | 状态 |
|------|--------|------|------|
| 幂 | `甲 ** 乙` | —（无已成立的汉语表层） | SYM_POW，无双表层 |
| 整除 | `甲 // 乙` | `甲整除乙` | ACCEPTED_LEGACY_ALIAS |
| 取余 | `甲 % 乙` | `甲余乙` | ACCEPTED_LEGACY_ALIAS |

### 1.4 ACCEPTED_LEGACY_ALIAS 规则

- 能解析
- `preserve` 格式化时保留原写法
- `symbolic` / `verbal` 格式化时转为 `//` `%`
- 新教程和 AI 不主动生成汉语
- LSP 悬停说明实际语义：向下取整除法 / 模运算

### 1.5 `负3` 的正确模型（修订）

**撤回** `负数字面量 → 整数(-3)` 方案。改为两种都进入一元运算：

```
负3    → 一元运算("-", 整数(3), 表层算符="负")
-3     → 一元运算("-", 整数(3), 表层算符="-")
```

这样幂优先级正确：

```
负2 ** 2   → 一元运算("-", 整数(2), 表层="负") ** 整数(2)   → -(2**2) = -4  ✅
-2 ** 2    → 一元运算("-", 整数(2), 表层="-") ** 整数(2)    → -(2**2) = -4  ✅
（负2）** 2 → 整数(2) 作为一元运算的操作数，被括号包裹      → (-2)**2 = 4   ✅
（-2）** 2  → 同上                                           → (-2)**2 = 4   ✅
2 ** 负2   → 2 ** 一元运算("-", 整数(2), 表层="负")         → 2**(-2) = 0.25 ✅
2 ** -2    → 2 ** 一元运算("-", 整数(2), 表层="-")          → 2**(-2) = 0.25 ✅
```

**Lexer 实现**：遇到 `负`+digit 时，发出两个 Token：

```
WORD_NEG（原文="负", 语义值="-"）
NUMBER（原文="3", 语义值=3）
```

不是之前方案的单个负数 Token。

### 1.6 `==` 保持非法

既不属汉语式，也不属数学式。

```
甲 == 乙   → 词法错误：「周道使用「=」或「等于」判断相等。」
```

### 1.7 Unicode 数学字形不进入源码

`≥` `≤` `≠` `×` `−` 仅用于编辑器显示层，不修改源码。

---

## 二、Token 分权方案（修订）

### 2.1 全部 Token 类型（无分叉）

```python
# 汉语运算符（表达式 + 使 共用）
OP_ADD = "OP_ADD"       # 加
OP_SUB = "OP_SUB"       # 减
OP_MUL = "OP_MUL"       # 乘
OP_DIV = "OP_DIV"       # 除

# 符号运算符（仅表达式）
SYM_ADD = "SYM_ADD"     # +
SYM_SUB = "SYM_SUB"     # -
SYM_MUL = "SYM_MUL"     # *
SYM_DIV = "SYM_DIV"     # /

# 汉语比较（表达式）
OP_EQ = "OP_EQ"         # 等于
OP_NE = "OP_NE"         # 不等于
OP_GT = "OP_GT"         # 大于
OP_LT = "OP_LT"         # 小于
OP_GE = "OP_GE"         # 不少于
OP_LE = "OP_LE"         # 不多于

# 符号比较（表达式）
SYM_EQ = "SYM_EQ"       # =
SYM_NE = "SYM_NE"       # !=
SYM_GT = "SYM_GT"       # >
SYM_LT = "SYM_LT"       # <
SYM_GE = "SYM_GE"       # >=
SYM_LE = "SYM_LE"       # <=

# 幂（无双表层，符号优先）
SYM_POW = "SYM_POW"     # **

# ACCEPTED_LEGACY_ALIAS
OP_FLOOR_DIV = "OP_FLOOR_DIV"   # 整除
OP_MOD = "OP_MOD"               # 余
SYM_FLOOR_DIV = "SYM_FLOOR_DIV" # //
SYM_MOD = "SYM_MOD"             # %

# 汉语一元负号（仅数值语境）
WORD_NEG = "WORD_NEG"   # 负（紧邻数字时）
```

### 2.2 Parser 接受规则

| Parser 入口 | 接受 Token | 归一为 |
|------------|-----------|--------|
| `_解析加性表达式` | `OP_ADD` / `SYM_ADD` / `OP_SUB` / `SYM_SUB` | `"+"` / `"-"` |
| `_解析乘性表达式` | `OP_MUL` / `SYM_MUL` / `OP_DIV` / `SYM_DIV` / `OP_FLOOR_DIV` / `SYM_FLOOR_DIV` / `OP_MOD` / `SYM_MOD` | `"*"` / `"/"` / `"//"` / `"%"` |
| `_解析幂表达式` | `SYM_POW` | `"**"` |
| `_解析前缀表达式`（一元负） | `WORD_NEG` / `SYM_SUB` | `"-"` |
| `_解析比较表达式` | `OP_EQ` / `SYM_EQ` / `OP_NE` / `SYM_NE` / `OP_GT` / `SYM_GT` / `OP_LT` / `SYM_LT` / `OP_GE` / `SYM_GE` / `OP_LE` / `SYM_LE` | `"=="` / `"!="` / `">"` / `"<"` / `">="` / `"<="` |
| `_解析使`（动作） | `OP_ADD` / `OP_SUB` / `OP_MUL` / `OP_DIV` | `"+="` / `"-="` / `"*="` / `"/="` |
| `_解析使`（变为） | `K_BECOME` | 赋值 |

### 2.3 一元解析（按 Token 类型，不查 `.值`）

```python
def _解析前缀表达式(self):
    token = self._当前()
    if token.token_type == SYM_SUB:
        # 符号一元负号
        self._吃()
        右侧 = self._解析幂表达式()
        return 一元运算("-", 右侧, 表层算符="-")
    elif token.token_type == WORD_NEG:
        # 汉语一元负号（仅紧邻数字时出现）
        self._吃()
        右侧 = self._解析幂表达式()
        return 一元运算("-", 右侧, 表层算符="负")
    return self._解析幂表达式()
```

**关键**：`OP_SUB`（减）不在此处出现。`减` 永远是二元运算符，只在 `_解析加性表达式` 中作为中缀出现。一元负号只来自 `WORD_NEG`（汉语 `负`+数字）和 `SYM_SUB`（符号 `-`）。

### 2.4 使语句拒绝清单

```python
def _解析使(self, 位置):
    # ... 解析左值 ...
    
    if self._匹配(K_BECOME):
        return 变更(...)
    
    token = self._当前()
    if token.token_type in (OP_ADD, OP_SUB, OP_MUL, OP_DIV):
        # 合法汉语动作
        映射 = {OP_ADD: "+=", OP_SUB: "-=", OP_MUL: "*=", OP_DIV: "/="}
        self._吃()
        return 算术变更(..., 算符=映射[token.token_type], ...)
    
    if token.token_type in (SYM_ADD, SYM_SUB, SYM_MUL, SYM_DIV,
                            SYM_POW, SYM_FLOOR_DIV, SYM_MOD,
                            OP_FLOOR_DIV, OP_MOD):
        raise 语法错误(
            "「使」后需要变化动作：加、减、乘、除 或 变为。"
            "不接受符号运算符。",
            token.位置)
```

### 2.5 KW_MAP

```python
KW_MAP = {
    "加": OP_ADD, "减": OP_SUB, "乘": OP_MUL, "除": OP_DIV,
    "等于": OP_EQ, "不等于": OP_NE,
    "大于": OP_GT, "小于": OP_LT,
    "不少于": OP_GE, "不多于": OP_LE,
    "整除": OP_FLOOR_DIV, "余": OP_MOD,
    # WORD_NEG 不是关键字——由 lexer 特判 `负`+digit 生成
    # 其他不变...
}
```

### 2.6 Lexer 符号识别

```python
_多字符符号 = {
    "**": SYM_POW,
    "//": SYM_FLOOR_DIV,
    "!=": SYM_NE,
    "<=": SYM_LE,
    ">=": SYM_GE,
}
# == → 单独报错

_单字符符号 = {
    '+': SYM_ADD, '-': SYM_SUB, '*': SYM_MUL, '/': SYM_DIV,
    '%': SYM_MOD, '=': SYM_EQ,
    '<': SYM_LT, '>': SYM_GT,
}
```

Lexer 中 `负`+digit 的处理：

```python
# 在 KW_MAP 匹配之后、标识符扫描之前：
if ch == "负" and i + 1 < 长度 and 源码[i + 1].isdigit():
    # 汉语一元负号 + 数字
    tokens.append(Token(token_type=WORD_NEG, 原文="负", 语义值="-",
                        跨度=SourceSpan(行, 列, 1)))
    i += 1; 列 += 1
    continue
```

`负3` 会先匹配 `负`+digit 发出 WORD_NEG，然后 `3` 在数字分支被处理为 NUMBER Token。Parser 的 `_解析前缀表达式` 收到 WORD_NEG 后创建一元运算。

---

## 三、幂语法层（修订）

```python
def _解析前缀表达式(self):
    token = self._当前()
    if token.token_type == SYM_SUB:
        self._吃()
        右侧 = self._解析幂表达式()   # -2**2 → -(2**2)
        return 一元运算("-", 右侧, 表层算符="-")
    elif token.token_type == WORD_NEG:
        self._吃()
        右侧 = self._解析幂表达式()   # 负2**2 → -(2**2)
        return 一元运算("-", 右侧, 表层算符="负")
    return self._解析幂表达式()

def _解析幂表达式(self):
    左侧 = self._解析后缀起始()
    if self._当前().token_type == SYM_POW:
        self._吃()
        右侧 = self._解析前缀表达式()  # 右结合 + 2 ** -2
        return 二元运算(左侧, "**", 右侧, 表层算符="**")
    return 左侧
```

验证：

```
2 ** 3 ** 2       → 2**(3**2) = 512      ✅
-2 ** 2           → -(2**2) = -4         ✅
（-2）** 2         → (-2)**2 = 4          ✅
2 ** -2           → 2**(-2) = 0.25       ✅
2 * 3 ** 2        → 2*(3**2) = 18        ✅
负2 ** 2          → -(2**2) = -4         ✅
（负2）** 2        → (-2)**2 = 4          ✅
2 ** 负2          → 2**(-2) = 0.25       ✅
```

---

## 四、相等处理

```python
# Lexer
if ch == '=' and i + 1 < 长度 and 源码[i+1] == '=':
    raise 词法错误("周道使用「=」或「等于」判断相等。")

# Parser _解析比较表达式
if self._当前().token_type in (OP_EQ, SYM_EQ, ...):
    算符名 = "=="  # 归一
```

---

## 五、混写规则

### 允许

```
设结果为甲加乙 * 丙。     ← 合法，语义为 甲 +（乙 * 丙）
```

优先级由统一 `_二元映射` 确定。

### Linter 非阻塞提示

```
警告：同一表达式混用了汉语式和数学式运算符。
可使用格式化风格统一。
```

不是语法错误，不影响编译和执行。

---

## 六、全角括号

周道所有括号统一使用全角：

```
（  ）    ← 表达式分组、参数列表
【  】    ← 字符串字面量
［  ］    ← 列表、下标
《  》    ← 模块名
```

本方案不引入半角括号。文档和测试全部使用全角：

```
（-2）** 2    ← 正确
(-2) ** 2    ← 错误，不使用半角
```

Lexer 应确认 `（` `）` 识别为 `PAREN_OPEN` / `PAREN_CLOSE`，半角 `(` `)` 默认走"无法识别"路径。

---

## 七、Surface AST 扩展

依据 `SURFACE-PRESERVATION-MODEL-0105.md`：

```python
@dataclass
class 二元运算(表达式):
    左: "表达式"
    算符: str
    右: "表达式"
    表层算符: str = field(default="", kw_only=True)

@dataclass
class 一元运算(表达式):
    算符: str
    操作数: "表达式"
    表层算符: str = field(default="", kw_only=True)
```

Parser 创建节点时传入表层写法：

```python
def _解析加性表达式(self):
    left = self._解析乘性表达式()
    while self._当前().token_type in (OP_ADD, SYM_ADD, OP_SUB, SYM_SUB):
        op_tok = self._吃()
        算符名 = "+" if op_tok.token_type in (OP_ADD, SYM_ADD) else "-"
        right = self._解析乘性表达式()
        left = 二元运算(left, 算符名, right, 表层算符=op_tok.原文)
    return left
```

`op_tok.原文` 是 `"加"` / `"+"` / `"减"` / `"-"`。

---

## 八、Formatter 三模式（修订）

### 8.1 风格判断

```python
_STYLE_MAP = {
    # 汉语式
    OP_ADD: "verbal", OP_SUB: "verbal", OP_MUL: "verbal", OP_DIV: "verbal",
    OP_EQ: "verbal", OP_NE: "verbal", OP_GT: "verbal", OP_LT: "verbal",
    OP_GE: "verbal", OP_LE: "verbal",
    OP_FLOOR_DIV: "verbal", OP_MOD: "verbal",
    WORD_NEG: "verbal",
    # 符号式
    SYM_ADD: "symbolic", SYM_SUB: "symbolic", SYM_MUL: "symbolic", SYM_DIV: "symbolic",
    SYM_EQ: "symbolic", SYM_NE: "symbolic", SYM_GT: "symbolic", SYM_LT: "symbolic",
    SYM_GE: "symbolic", SYM_LE: "symbolic",
    SYM_FLOOR_DIV: "symbolic", SYM_MOD: "symbolic",
}
```

### 8.2 算符映射（只含算符，不含空格）

```python
_汉语算符 = {
    "+": "加", "-": "减", "*": "乘", "/": "除",
    "==": "等于", "!=": "不等于",
    ">": "大于", "<": "小于", ">=": "不少于", "<=": "不多于",
    "**": "**", "//": "//", "%": "%",  # 无双表层
}

_符号算符 = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "==": "=", "!=": "!=",
    ">": ">", "<": "<", ">=": ">=", "<=": "<=",
    "**": "**", "//": "//", "%": "%",
}
```

### 8.3 preserve 模式

```python
def _渲染二元运算(self, 节点, 模式):
    if 模式 == "preserve" and 节点.表层算符:
        风格 = "verbal" if ord(节点.表层算符[0]) >= 0x4e00 else "symbolic"
    else:
        风格 = 模式 if 模式 != "preserve" else self._默认风格

    算符文 = (_汉语算符 if 风格 == "verbal" else _符号算符)[节点.算符]

    if 风格 == "verbal":
        self._写(节点.左); self._写(算符文); self._写(节点.右)
    else:
        self._写(节点.左); self._写(" "); self._写(算符文); self._写(" "); self._写(节点.右)
```

### 8.4 负号三模式

```python
def _渲染一元运算(self, 节点, 模式):
    if 模式 == "preserve" and 节点.表层算符:
        风格 = "verbal" if ord(节点.表层算符[0]) >= 0x4e00 else "symbolic"
    else:
        风格 = 模式 if 模式 != "preserve" else self._默认风格

    if 风格 == "verbal":
        self._写("负"); self._化表达式(节点.操作数)
    else:
        self._写("-"); self._化表达式(节点.操作数)
```

### 8.5 共识语义等价

```python
def test_formatter_semantic_equivalence():
    """格式化后重新编译执行，结果不变。"""
    源码 = "设结果为负2 ** 2。显示结果。"
    for 风格 in ["preserve", "verbal", "symbolic"]:
        格式化后 = 格式化(源码, 风格=风格)
        env = 运行(格式化后)
        assert env.get("结果") == -4, f"{风格} 模式改变语义"
```

---

## 九、实施顺序

```
A1 Token 分权          tokens.py: 新增全部 SYM_* + WORD_NEG
A2 符号 Lexer          lexer.py: 符号识别 + WORD_NEG 特判 + == 报错
A3 Parser 双表层        parser.py: 双入口 + 幂层 + 使守卫 + 表层算符保存
A4 Surface AST 扩展      ast_nodes.py: keyword-only 新字段
A5 Lowering 无变化       lowering.py: 只读 算符，丢弃 表层算符
A6 Formatter 三模式      formatter.py: 删除硬编码反向映射，实现三模式
A7 LSP 高亮同步          lsp_server.py: OP_* / SYM_* 分别着色
A8 双表层差分测试
A9 全量回归
```

---

## 十、未纳入本轮的事项

- 注释保真（010.5-B）
- 结构指称（010.5-C）
- JSON 边界（010.5-D）
- `负（数量）` 通用汉语一元运算（未批准）
- 半角括号语法（未提案）
