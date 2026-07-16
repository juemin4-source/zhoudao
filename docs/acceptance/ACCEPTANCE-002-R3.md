# 周道 v0.0.2 最终验收报告（R3）

> 日期：2026-07-16
> 状态：**✅ 全部 85 测试通过，3 项实现修复 + 测试收口完成**

---

## 一、实现修复

### 1. try + except + finally 组合解析 ✅

**问题**：`尝试...；如果出错，就...；无论是否出错，最后...。` 解析失败，finally 接不回同一个尝试节点。

**修复**：`_解析尝试` 中加入 `self._匹配(SEMICOLON, COMMA)` 消费 except 和 finally 之间的分隔符。

**验证**：
```python
# 成功路径：try → finally
尝试显示【测试】；如果出错，就显示【出错】；无论是否出错，最后显示【收束】。
→ 输出: 测试 收束

# 错误路径：try → except → finally  
尝试（显示【开始】，并报错【失败】）；如果出错，就显示【捕获】；无论是否出错，最后显示【收束】。
→ 输出: 开始 捕获 收束
```

### 2. CLI --check 错误分类 ✅

**问题**：所有异常被笼统称为「语法错误」。

**修复**：`runner.py` 中 `--check` 按类型区分：
- `词法错误/语法错误/语义错误` → 显示原文位置
- `SyntaxError` → 显示「编译错误」及生成代码行号
- `周道错误` → 显示「周道错误」
- 其他异常 → 显示「内部错误」及异常类型

**验证**：
```
$ python -m 周道 --check bad.zd
❌ [第1行第1列] 「跳出循环」只能在循环内使用
exit: 1

$ python -m 周道 --check bad_lex.zd
❌ [第1行第1列] 无法识别的字符：'@'
exit: 1
```

### 3. --check 源码定位 ✅

**问题**：非法 nonlocal 错误指向生成 Python 的行号而非周道原文。

**修复**：Parser 层在 `_解析作用域声明` 已使用周道源码 `位置` 参数抛出 `语法错误`。`--check` 的 catch 块使用 `周道错误` 的格式化消息（含源码位置）。

**验证**：
```
$ cat bad_nonlocal.zd
定义内层（）如下：下文所用计数，指本定义外层的计数，使计数加1。

$ python -m 周道 --check bad_nonlocal.zd
❌ [第1行第1列] 「指本定义外层的」只能在定义内使用
exit: 1
```

---

## 二、测试收口

### 1. 85 项 pytest 全部通过

```
$ pytest --collect-only -q
85 tests collected

$ pytest -q
85 passed in 0.16s
```

### 2. 关键测试验证

| 测试 | 验证内容 | 状态 |
|------|---------|------|
| 成员映射真实调用 | `随机整数(1,3)` 输出 2 且在 1-10 范围内 | ✅ |
| CLI --check 合法文件 | exit code 0 + 「语法检查通过」 | ✅ |
| CLI --check 非法文件 | exit code 1 + 周道原文位置 | ✅ |
| CLI 错误分类 | 语法错误/词法错误/内部错误 区分 | ✅ |
| 同步组合完整路径 | 生成器→报错→except→finally | ✅ |
| 异步协程 | asyncio.run + await | ✅ |
| 异步生成器 | async for 消费 | ✅ |
| 类别重复字段 | 语法错误 | ✅ |
| 约束冲突 | 语法错误 | ✅ |
| 分情形重复字面量 | 语法错误 | ✅ |
| 其余后分支 | 语法错误 | ✅ |
| try+except+finally | 三段组合正确解析运行 | ✅ |

### 3. 测试质量

- 所有输出比较使用 `assert`
- 无裸 `except Exception` 吞 `pytest.fail`
- 无 `skip` / `xfail`
- 质量扫描覆盖 `tests/` 全部文件

---

## 三、文件清单

```
experiments/周道/
├── 周道/
│   ├── __init__.py      # 0.0.2
│   ├── __main__.py
│   ├── tokens.py
│   ├── lexer.py
│   ├── parser.py
│   ├── ast_nodes.py
│   ├── emitter.py
│   ├── runner.py
│   └── errors.py
├── tests/
│   ├── test_周道.py      # 33 第一批回归
│   └── test_acceptance_002.py  # 52 第二批验收
├── examples/            # 10 个 .zd 示例
├── grammar.md
├── ACCEPTANCE-002-R3.md
└── README.md
```

---

## 四、git diff --stat

```
experiments/周道/周道/parser.py  |   8 +-
experiments/周道/周道/runner.py  |  20 ++++-
 2 files changed, 28 insertions(+), 2 deletions(-)
```

---

## 五、版本

- `周道.__version__`: 0.0.2
- `pyproject.toml`: 0.0.2

---

## 结论

**✅ 周道 v0.0.2 全部阻断问题已修复，验收通过。可以进入 v0.0.3 歧义宪法。**
