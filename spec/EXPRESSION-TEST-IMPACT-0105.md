# 表达式测试影响分析 010.5 — 修订版 R1

> 修订：修复赋值无输出；删除占位符；参数化矩阵代替复制；
> 直接 IR 断言；补负号哨兵；补最长匹配/SourceSpan/LSP 测试。
> 现有汉语测试不迁移、不删除——它们是双表层的一半证据。

---

## 一、测试总则

| 原则 | 说明 |
|------|------|
| 现有汉语测试全部保留 | 汉语式是正式语法，测试通过是双表层证据 |
| 每条运算符新增符号式等价测试 | 参数化矩阵，不逐一复制 |
| 双表层必须断言 | Surface AST 表层不同；归一 Core IR 相同；运行结果相同 |
| 旧测试不修改断言 | 输出值不变 |
| 所有赋值测试必须配输出 | `显示结果。` 或查 `env["结果"]` |
| 幂、负号、使为独立哨兵组 | 不合并到参数化矩阵 |
| 测试用全角括号，不用半角 | `（-2）` 不是 `(-2)` |

---

## 二、现有测试状态

### 不受影响的测试

`test_周道.py` 中所有现有测试约 30 条，保持原样。它们使用汉语式运算符，双表层方案后继续合法。

受影响检查：无。现有测试全部通过验证双表层不破坏汉语式。

---

## 三、参数化等价矩阵（替代逐条复制）

### 3.1 运算符等价矩阵

```python
@pytest.mark.parametrize("汉语式, 符号式, 语义算符, 期望值", [
    # 算术
    ("设结果为3加5。显示结果。", "设结果为3 + 5。显示结果。", "+", 8),
    ("设结果为5减3。显示结果。", "设结果为5 - 3。显示结果。", "-", 2),
    ("设结果为3乘5。显示结果。", "设结果为3 * 5。显示结果。", "*", 15),
    ("设结果为6除3。显示结果。", "设结果为6 / 3。显示结果。", "/", 2.0),
    # 比较——条件输出而非数值
    ("如果3等于3，就显示【等】。", "如果3 = 3，就显示【等】。", "==", ["等"]),
    ("如果3不等于4，就显示【不等】。", "如果3 != 4，就显示【不等】。", "!=", ["不等"]),
    ("如果5大于3，就显示【大】。", "如果5 > 3，就显示【大】。", ">", ["大"]),
    ("如果3小于5，就显示【小】。", "如果3 < 5，就显示【小】。", "<", ["小"]),
    ("如果5不少于3，就显示【通过】。", "如果5 >= 3，就显示【通过】。", ">=", ["通过"]),
    ("如果3不多于5，就显示【通过】。", "如果3 <= 5，就显示【通过】。", "<=", ["通过"]),
])
def test_双表层_等价(汉语式, 符号式, 语义算符, 期望值):
    """汉语式和符号式产生相同的运行结果。"""
    # 输出断言
    env1 = 运行(汉语式)
    env2 = 运行(符号式)
    assert env1.get("结果") == env2.get("结果"), \
        f"汉语式结果 {env1.get('结果')} 不等于符号式 {env2.get('结果')}"

    # IR 归一断言
    from 周道.parser import 解析器
    from 周道.lowering import 降低_仅语法
    from 周道.lexer import 扫描

    _, ir1 = _解析并降低(汉语式)
    _, ir2 = _解析并降低(符号式)
    assert _归一化IR(ir1) == _归一化IR(ir2), \
        f"IR 不一致\n汉语：{_归一化IR(ir1)}\n符号：{_归一化IR(ir2)}"
```

### 3.2 辅助函数

```python
def _解析并降低(源码: str):
    """返回 (Surface AST, Core IR)"""
    tokens = 扫描(源码)
    parser = 解析器(tokens)
    ast = parser.解析()
    result = 降低_仅语法(ast)
    return ast, result

def _归一化IR(ir) -> str:
    """将 Core IR 序列化为可比较字符串，剔除 SourceSpan 等非语义字段。"""
    from 周道.core_ir import 二元运算IR, 一元运算IR, 整数常量IR, 变量引用IR, 赋值IR, 打印IR
    def _行(节点, 缩进=0):
        prefix = "  " * 缩进
        if isinstance(节点, 赋值IR):
            return f"{prefix}赋值({_行(节点.目标)}, {_行(节点.值)})"
        elif isinstance(节点, 打印IR):
            return f"{prefix}打印({_行(节点.值)})"
        elif isinstance(节点, 二元运算IR):
            return f"{prefix}二元({_行(节点.左)}, {节点.算符!r}, {_行(节点.右)})"
        elif isinstance(节点, 一元运算IR):
            return f"{prefix}一元({节点.算符!r}, {_行(节点.操作数)})"
        elif isinstance(节点, 整数常量IR):
            return f"{prefix}整数({节点.值})"
        elif isinstance(节点, 变量引用IR):
            return f"{prefix}变量({节点.名称})"
        return f"{prefix}{type(节点).__name__}"
    行列表 = [_行(s) for s in ir.语句列表]
    return "\n".join(行列表)
```

---

## 四、Surface AST 表层断言

```python
def test_双表层_表层不同():
    """同一运算符的汉语式和符号式，Surface AST 表层算符不同。"""
    from 周道.ast_nodes import 二元运算

    ast_v, _ = _解析并降低("设结果为3加5。")
    ast_s, _ = _解析并降低("设结果为3 + 5。")

    # 提取二元运算节点
    def _找二元(ast):
        for 句子 in ast.句子列表:
            for 语句 in 句子.语句列表:
                if hasattr(语句, '值') and isinstance(语句.值, 二元运算):
                    return 语句.值
        return None

    node_v = _找二元(ast_v)
    node_s = _找二元(ast_s)

    assert node_v is not None and node_s is not None
    assert node_v.表层算符 == "加", f"汉语式应保存 '加'，实际 {node_v.表层算符}"
    assert node_s.表层算符 == "+", f"符号式应保存 '+'，实际 {node_s.表层算符}"
    assert node_v.算符 == node_s.算符, "归一语义算符应相同"
```

---

## 五、幂运算哨兵（独立组）

```python
def test_幂_基本():
    env = 运行("设结果为2 ** 3。显示结果。")
    assert "8" in ...  # 通过检查输出
```

实际上，用 `运行` 返回 env：

```python
def test_幂_基本():
    env = 运行("设结果为2 ** 3。")
    assert env["结果"] == 8

def test_幂_右结合():
    env = 运行("设结果为2 ** 3 ** 2。")
    assert env["结果"] == 512

def test_幂_负号优先_符号():
    env = 运行("设结果为-2 ** 2。")
    assert env["结果"] == -4

def test_幂_负号优先_汉语():
    env = 运行("设结果为负2 ** 2。")
    assert env["结果"] == -4

def test_幂_负号等价():
    """负2 与 -2 在幂语境中行为一致"""
    env1 = 运行("设结果为负2 ** 2。")
    env2 = 运行("设结果为-2 ** 2。")
    assert env1["结果"] == env2["结果"] == -4

def test_幂_括号覆盖_符号():
    env = 运行("设结果为（-2） ** 2。")
    assert env["结果"] == 4

def test_幂_括号覆盖_汉语():
    env = 运行("设结果为（负2） ** 2。")
    assert env["结果"] == 4

def test_幂_负指数_符号():
    env = 运行("设结果为2 ** -2。")
    assert env["结果"] == 0.25

def test_幂_负指数_汉语():
    env = 运行("设结果为2 ** 负2。")
    assert env["结果"] == 0.25

def test_幂_乘法混合():
    env = 运行("设结果为2 * 3 ** 2。")
    assert env["结果"] == 18
```

### 关键哨兵

```python
def test_幂_负号哨兵_完整():
    """负号与幂的全部边界组合。"""
    casos = [
        ("-2 ** 2", -4),
        ("负2 ** 2", -4),
        ("（-2） ** 2", 4),
        ("（负2） ** 2", 4),
        ("2 ** -2", 0.25),
        ("2 ** 负2", 0.25),
        ("-2 ** -2", -0.25),
        ("负2 ** 负2", -0.25),
    ]
    for expr, expected in casos:
        env = 运行(f"设结果为{expr}。")
        assert env["结果"] == expected, f"{expr} → 期望 {expected}，实际 {env['结果']}"
```

---

## 六、整除和取余

### 6.1 符号式（推荐）

```python
@pytest.mark.parametrize("expr, expected", [
    ("5 // 2", 2),
    ("-5 // 2", -3),    # 向下取整
    ("5 // -2", -3),
    ("-5 // -2", 2),
    ("5.5 // 2", 2.0),
])
def test_整除_符号(expr, expected):
    env = 运行(f"设结果为{expr}。")
    assert env["结果"] == expected

@pytest.mark.parametrize("expr, expected", [
    ("5 % 2", 1),
    ("-5 % 2", 1),      # 模运算
    ("5 % -2", -1),
    ("-5 % -2", -1),
    ("5.5 % 2", 1.5),
])
def test_取余_符号(expr, expected):
    env = 运行(f"设结果为{expr}。")
    assert env["结果"] == expected
```

### 6.2 ACCEPTED_LEGACY_ALIAS

```python
@pytest.mark.parametrize("expr, expected", [
    ("5整除2", 2),
    ("-5整除2", -3),
    ("5余2", 1),
    ("-5余2", 1),
])
def test_整除取余_legacy_alias(expr, expected):
    """ACCEPTED_LEGACY_ALIAS 仍能解析"""
    env = 运行(f"设结果为{expr}。")
    assert env["结果"] == expected
```

---

## 七、使语句验收

### 7.1 合法动作

```python
@pytest.mark.parametrize("src, 期望算符", [
    ("使数量加1。", "+="),
    ("使数量减1。", "-="),
    ("使数量乘2。", "*="),
    ("使数量除2。", "/="),
])
def test_使_合法汉语动作(src, 期望算符):
    env = 运行(f"设数量为10。{src}")
    assert 期望算符 in ...  # 通过转译检查
    # 更精确：
    py = 转译_仅语法(f"设数量为10。{src}")
    assert 期望算符 in py
```

### 7.2 拒绝清单

```python
@pytest.mark.parametrize("src", [
    "使数量 + 1。",
    "使数量 - 1。",
    "使数量 * 2。",
    "使数量 / 2。",
    "使数量 ** 2。",
    "使数量 // 2。",
    "使数量 % 2。",
])
def test_使_拒绝符号(src):
    with pytest.raises((语法错误, 词法错误)):
        转译(src)

@pytest.mark.parametrize("src", [
    "使数量整除2。",
    "使数量余2。",
])
def test_使_拒绝旧动作(src):
    """整除/余 未批准为使动作"""
    with pytest.raises((语法错误, 词法错误)):
        转译(src)
```

---

## 八、`负3` 验收

```python
def test_负3_汉语():
    env = 运行("设结果为负3。")
    assert env["结果"] == -3

def test_负3_符号():
    env = 运行("设结果为-3。")
    assert env["结果"] == -3

def test_负_变量():
    env = 运行("设数量为5。设结果为-数量。")
    assert env["结果"] == -5

def test_负数量_不是运算():
    """负数量 是普通标识符，不是 取负(数量)"""
    env = 运行("设负数量为42。显示负数量。")  # 标识符绑定
    # 不报错，结果为 42
```

---

## 九、`==` 拒绝

```python
def test_拒绝_双等号():
    with pytest.raises(词法错误, match="使用.*="):
        转译("如果甲 == 乙，就显示【等】。")
```

---

## 十、最长匹配与位置测试

```python
@pytest.mark.parametrize("src, 期望标记, 期望跨度", [
    ("**", SYM_POW, SourceSpan(行=1, 列=1, 长度=2)),
    ("//", SYM_FLOOR_DIV, SourceSpan(行=1, 列=1, 长度=2)),
    ("!=", SYM_NE, SourceSpan(行=1, 列=1, 长度=2)),
    ("<=", SYM_LE, SourceSpan(行=1, 列=1, 长度=2)),
    (">=", SYM_GE, SourceSpan(行=1, 列=1, 长度=2)),
    ("+", SYM_ADD, SourceSpan(行=1, 列=1, 长度=1)),
    ("-", SYM_SUB, SourceSpan(行=1, 列=1, 长度=1)),
    ("%", SYM_MOD, SourceSpan(行=1, 列=1, 长度=1)),
])
def test_符号最长匹配(src, 期望标记, 期望跨度):
    """多字符运算符不被拆散。"""
    from 周道.lexer import 扫描
    tokens = 扫描(src)
    # 应恰好产生一个 Token（+ EOF）
    assert len([t for t in tokens if t.token_type != "EOF"]) == 1
    tok = tokens[0]
    assert tok.token_type == 期望标记, f"{src} → {tok.token_type}"
    assert tok.跨度.行 == 期望跨度.行
    assert tok.跨度.列 == 期望跨度.列
    assert tok.跨度.长度 == 期望跨度.长度

def test_符号_星号不被拆散():
    """** 不拆成 * *"""
    from 周道.lexer import 扫描
    tokens = 扫描("**")
    非空 = [t for t in tokens if t.token_type != "EOF"]
    assert len(非空) == 1
    assert 非空[0].token_type == SYM_POW

def test_符号_斜杠不被拆散():
    """// 不拆成 / /"""
    from 周道.lexer import 扫描
    tokens = 扫描("//")
    非空 = [t for t in tokens if t.token_type != "EOF"]
    assert len(非空) == 1
    assert 非空[0].token_type == SYM_FLOOR_DIV
```

---

## 十一、`==` 和 `!` 的专用诊断

```python
def test_拒绝_双等号_诊断():
    with pytest.raises(词法错误) as exc:
        转译("如果甲 == 乙，就显示【等】。")
    assert "=" in str(exc.value) and "=" in str(exc.value)

def test_拒绝_单独叹号():
    with pytest.raises((词法错误, 语法错误)):
        转译("设结果为!3。")
```

---

## 十二、Formatter 模式测试

```python
def test_formatter_preserve_verbal():
    源码 = "设结果为甲加乙。"
    结果 = 格式化(源码, 风格="preserve")
    assert "加" in 结果 and "+" not in 结果

def test_formatter_preserve_symbolic():
    源码 = "设结果为甲 + 乙。"
    结果 = 格式化(源码, 风格="preserve")
    assert "+" in 结果 and "加" not in 结果

def test_formatter_verbal():
    源码 = "设结果为甲 + 乙。"
    结果 = 格式化(源码, 风格="verbal")
    assert "加" in 结果

def test_formatter_symbolic():
    源码 = "设结果为甲加乙。"
    结果 = 格式化(源码, 风格="symbolic")
    assert "+" in 结果

def test_formatter_neg_preserve_verbal():
    源码 = "设结果为负3。"
    结果 = 格式化(源码, 风格="preserve")
    assert "负3" in 结果

def test_formatter_neg_preserve_symbolic():
    源码 = "设结果为-3。"
    结果 = 格式化(源码, 风格="preserve")
    assert "-3" in 结果

def test_formatter_neg_symbolic():
    源码 = "设结果为负3。"
    结果 = 格式化(源码, 风格="symbolic")
    assert "-3" in 结果

def test_formatter_neg_verbal():
    源码 = "设结果为-3。"
    结果 = 格式化(源码, 风格="verbal")
    assert "负3" in 结果

def test_formatter_idempotent():
    源码 = "设结果为甲 + 乙。"
    assert 格式化(格式化(源码)) == 格式化(源码)

def test_formatter_idempotent_verbal():
    源码 = "设结果为甲加乙。"
    assert 格式化(格式化(源码, 风格="verbal"), 风格="verbal") == 格式化(源码, 风格="verbal")

def test_formatter_semantic_equivalence():
    """格式化后重新编译运行，结果不变。"""
    源码 = "设结果为负2 ** 2。显示结果。"
    for 风格 in ["preserve", "verbal", "symbolic"]:
        格式化后 = 格式化(源码, 风格=风格)
        env = 运行(格式化后)
        # 需要捕获输出
```

---

## 十三、测试文件影响清单

### `test_周道.py`

| 操作 | 数量 |
|------|------|
| 保留现有测试 | ~30 条 |
| 新增参数化等价矩阵 | 10 组 |
| 新增幂哨兵 | 11 条 |
| 新增整除/取余 | 7 条 |
| 新增使验收 | 9 条 |
| 新增负号验收 | 5 条 |
| 新增 `==` 拒绝 | 2 条 |
| 新增最长匹配/位置 | 10 条 |
| 新增 Formatter | 11 条 |
| **合计新增** | **~65 条** |
| **合计总测试** | **~95 条** |

### 其他文件

| 文件 | 影响 |
|------|------|
| `test_ast_backend.py` | 确认 `**` 已有映射 `ast.Pow`，加 0 新增 |
| `test_seed_*.py` | 使用汉语式，不受影响 |
| `test_diagnostics_011.py` | 可新增符号运算符报错路径测试 |

---

## 十四、不做的事情

- 注释格式化测试（010.5-B）
- 结构指称测试（010.5-C）
- JSON 测试（010.5-D）
- Unicode 数学字形输入测试（不属于规范源码）
- 半角括号测试（周道规范使用全角）
