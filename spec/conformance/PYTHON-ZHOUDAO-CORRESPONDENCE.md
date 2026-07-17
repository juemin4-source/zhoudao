# Python ↔ 周道对应表 v1.1

> 版本：0.0.10.5
> 等价级别：EXACT / INTENT_EQUIVALENT / SUBSET / ZHOUDAO_NATIVE / UNSUPPORTED / ACCEPTED_LEGACY_ALIAS

---

## 一、词法

| Python | 实际语义 | 母语内语 | 周道 | 级别 | 实现证据 | 状态 |
|--------|---------|---------|------|------|---------|------|
| `# note` | 行末注释 | 注：说明 | `注：说明` | ZHOUDAO_NATIVE | lexer COMMENT | ⚠️ |
| `42` | 整数 | 四十二 | `42` | EXACT | lexer NUMBER | ✅ |
| `3.14` | 小数 | 三点一四 | `3.14` | EXACT | lexer NUMBER | ✅ |
| `"text"` | 字符串 | 文本 | `【文本】` | INTENT_EQUIVALENT | lexer STRING | ✅ |
| `"a】b"` | 含右括号文本 | 需要转义 | `【a】】b】` | ZHOUDAO_NATIVE | 待审议转义方案 | ⚠️ |
| `[1, 2, 3]` | 列表 | 列表 1 2 3 | `［1、2、3］` | EXACT | tests | ✅ |
| `(1, 2)` | 元组 | 固定序列 1 2 | `固定序列［1、2］` | INTENT_EQUIVALENT | tests | ✅ |
| `{1, 2}` | 集合 | 集合 1 2 | `集合［1、2］` | EXACT | tests | ✅ |
| `{"a": 1}` | 映射 | 映射 a 为 1 | `映射［【a】为1］` | EXACT | tests | ✅ |
| `True` | 真值 | 真 | `真` | EXACT | 冻结基线 | ✅ |
| `False` | 假值 | 假 | `假` | EXACT | 冻结基线 | ✅ |
| `None` | 空值 | 没有值 | `没有值` | EXACT | tests | ✅ |
| `-3` | 负整数 | 负三 | `负3` / `-3` | EXACT | WORD_NEG + NUMBER / SYM_SUB + NUMBER | ✅ |

### 运算符（全部双表层：汉语式 / 数学符号）

| Python | 实际语义 | 汉语式 | 数学符号 | 级别 | 实现证据 | 状态 |
|--------|---------|--------|---------|------|---------|------|
| `a + b` | 加法 | `a加b` | `a + b` | EXACT | parser OP_ADD / SYM_ADD | ✅ |
| `a - b` | 减法 | `a减b` | `a - b` | EXACT | parser OP_SUB / SYM_SUB | ✅ |
| `a * b` | 乘法 | `a乘b` | `a * b` | EXACT | parser OP_MUL / SYM_MUL | ✅ |
| `a / b` | 除法 | `a除b` | `a / b` | EXACT | parser OP_DIV / SYM_DIV | ✅ |
| `a // b` | 向下取整除 | `a整除b` | `a // b` | EXACT | ACCEPTED_LEGACY_ALIAS + SYM_FLOOR_DIV | ✅ |
| `a % b` | 模运算 | `a余b` | `a % b` | EXACT | ACCEPTED_LEGACY_ALIAS + SYM_MOD | ✅ |
| `a ** b` | 幂 | — | `a ** b` | EXACT | SYM_POW 独立右结合语法层 | ✅ |
| `-x` | 取负 | `负3`（仅数字） | `-x` | EXACT | WORD_NEG / SYM_SUB 一元运算 | ✅ |
| `a == b` | 等于 | `a等于b` | `a = b` | EXACT | OP_EQ / SYM_EQ | ✅ |
| `a != b` | 不等于 | `a不等于b` | `a != b` | EXACT | OP_NE / SYM_NE | ✅ |
| `a > b` | 大于 | `a大于b` | `a > b` | EXACT | OP_GT / SYM_GT | ✅ |
| `a < b` | 小于 | `a小于b` | `a < b` | EXACT | OP_LT / SYM_LT | ✅ |
| `a >= b` | 大于等于 | `a不少于b` | `a >= b` | EXACT | OP_GE / SYM_GE | ✅ |
| `a <= b` | 小于等于 | `a不多于b` | `a <= b` | EXACT | OP_LE / SYM_LE | ✅ |
| 链式比较 `a < b < c` | 连续比较 | — | — | UNSUPPORTED | — | 🔮 |
| `x in ys` | 成员关系 | `x在ys中` | — | EXACT | OP_IN | ✅ |
| `x not in ys` | 非成员 | `x不在ys中` | — | EXACT | OP_NOT_IN | ✅ |
| `a is b` | 身份 | `a就是b` | — | EXACT | K_IS | ✅ |
| `a is not b` | 身份否定 | `a不是b本身` | — | EXACT | K_IS_NOT + K_SELF | ✅ |
| `a and b` | 逻辑与 | `a且b` | — | INTENT_EQUIVALENT | OP_AND | ⚠️ |
| `a or b` | 逻辑或 | `a或b` | — | INTENT_EQUIVALENT | OP_OR | ⚠️ |
| `not a` | 逻辑非 | `并非（a）` | — | INTENT_EQUIVALENT | OP_NOT | ✅ |
| `a.b` | 成员访问 | `a的b` | — | EXACT | K_DE | ✅ |
| `a[i]` | 下标 | `a［i］` | — | EXACT | parser | ✅ |
| `a[i:j]` | 切片 | `a［i：j］` | — | EXACT | parser | ✅ |

## 三、语句

| Python | 实际语义 | 母语内语 | 周道 | 级别 | 实现证据 | 状态 |
|--------|---------|---------|------|------|---------|------|
| `x = 1` | 绑定 | 设 x 为 1 | `设x为1。` | EXACT | tests | ✅ |
| `x = None` | 空绑定 | 设 x 为没有值 | `设x为没有值。` | EXACT | tests | ✅ |
| `x = True` | 真绑定 | 设 x 为真 | `设x为真。` | EXACT | 冻结基线 001 | ✅ |
| `x = False` | 假绑定 | 设 x 为假 | `设x为假。` | EXACT | 冻结基线 001 | ✅ |
| `x += 1` | 自增 | 使 x 加 1 | `使x加1。` | EXACT | tests | ✅ |
| `x -= 1` | 自减 | 使 x 减 1 | `使x减1。` | EXACT | tests | ✅ |
| `x *= 2` | 自乘 | 使 x 乘 2 | `使x乘2。` | EXACT | tests | ✅ |
| `a[i] = v` | 项目变更 | 使 a 下标 i 变为 v | `使a［i］变为v。` | EXACT | tests | ✅ |
| `del x` | 删除 | 删去 x | `删去x。` | EXACT | tests | ✅ |
| `del a[i]` | 删除项目 | 删去 a 下标 i | `删去a［i］。` | EXACT | tests | ✅ |
| `print(x)` | 输出 | 显示 x | `显示x。` | INTENT_EQUIVALENT | tests | ✅ |
| `if cond:` | 条件 | 如果 cond 就 | `如果cond，就` | EXACT | tests | ✅ |
| `elif cond:` | 否则如果 | 不然如果 cond 就 | `不然，如果cond，就` | EXACT | tests | ✅ |
| `else:` | 否则 | 不然就 | `不然就` | EXACT | tests | ✅ |
| `while cond:` | 当型循环 | 当 cond 时一直 | `当cond时，一直` | EXACT | tests | ✅ |
| `for x in it:` | 遍历 | 从 it 每取一项记作 x 就 | `从it中，每取一项记作x，就` | EXACT | tests | ✅ |
| `async for x in it:` | 异步遍历 | 每等到一项记作 x 就 | `从it中，每等到一项记作x，就` | EXACT | tests | ✅ |
| `break` | 跳出循环 | 跳出循环 | `跳出循环` | EXACT | tests | ✅ |
| `continue` | 继续 | 继续下一轮 | `继续下一轮` | EXACT | tests | ✅ |
| `try:` | 尝试 | 尝试 | `尝试` | EXACT | tests | ✅ |
| `except:` | 捕获全部 | 如果出错就 | `如果出错，就` | EXACT | tests | ✅ |
| `except ValueError:` | 分类捕获 | 如果错误类型是值出错就 | `如果错误类型是值出错，就` | EXACT | tests | ✅ |
| `raise`（原样） | 重抛 | 原样报出当前错误 | `原样报出当前错误` | EXACT | tests | ✅ |
| `finally:` | 最终 | 无论是否出错最后 | `无论是否出错，最后` | EXACT | tests | ✅ |
| `return x` | 返回值 | 以 x 为所得 | `以x为所得` | EXACT | tests | ✅ |
| `return` | 返回空 | 以没有值为所得 | `以没有值为所得` | INTENT_EQUIVALENT | 规范 | ✅ |
| `pass` | 空操作 | 不作处理 | `不作处理` | EXACT | tests | ✅ |
| `global x` | 全局声明 | 下文所用 x 均指全局的 x | `下文所用x，均指全局的x。` | EXACT | tests | ✅ |
| `nonlocal x` | 外层声明 | 下文所用 x 指外层的 x | `下文所用x，指本定义外层的x。` | EXACT | tests | ✅ |
| `assert x > 0` | 断言 | x 须大于 0 | `x须大于0。` | SUBSET | tests | ✅ |

## 四、函数

| Python | 实际语义 | 母语内语 | 周道 | 级别 | 实现证据 | 状态 |
|--------|---------|---------|------|------|---------|------|
| `def f():` | 定义函数 | 定义 f | `定义f（）如下：` | EXACT | tests | ✅ |
| `def f(a, b):` | 多参 | 定义 f 参数 a b | `定义f（a、b）如下：` | EXACT | tests | ✅ |
| `def f(a=1):` | 默认参数 | a 默认为 1 | `定义f（a默认为1）如下：` | EXACT | tests | ✅ |
| `f(a=1)` | 命名参数 | a 为 1 | `f（a为1）` | EXACT | tests | ✅ |
| 函数自然结束 | 隐式返回 None | 自然结束 | 无所得 | INTENT_EQUIVALENT | 规范 | ✅ |
| `*args` | 可变参数 | — | — | UNSUPPORTED | — | 🔮 |
| `**kwargs` | 关键字参数 | — | — | UNSUPPORTED | — | 🔮 |
| `lambda` | 匿名函数 | — | — | UNSUPPORTED | — | 🔮 |
| 闭包 | 词法作用域 | — | 词法作用域 | EXACT | tests | ✅ |

## 五、类别

| Python | 实际语义 | 母语内语 | 周道 | 级别 | 实现证据 | 状态 |
|--------|---------|---------|------|------|---------|------|
| `class C:` | 声明类别 | 设置 C 类别 | `设置C类别，包括` | INTENT_EQUIVALENT | tests | ✅ |
| `C(...)` | 构造实例 | C | `C（）` | EXACT | tests | ✅ |
| `self` | 当前实例 | 自己 | `自己` | ZHOUDAO_NATIVE | tests | ✅ |
| `self.x` | 实例字段 | 自己的 x | `自己的x` | ZHOUDAO_NATIVE | tests | ✅ |
| `{自己}` | — | 名为"自己"的精确名称 | `{自己}` | ZHOUDAO_NATIVE | tests | ✅ |
| `def m(self):` | 实例方法 | 定义 C 类别的 m | `定义C类别的m（）如下：` | ZHOUDAO_NATIVE | tests | ✅ |
| `self.x = v` | 修改字段 | 使自己的 x 变为 v | `使自己的x变为v。` | EXACT | tests | ✅ |
| 字段默认值 | 声明字段初值 | x 默认为 v | `x，默认为v` | EXACT | tests | ✅ |
| `__init__` | 构造方法 | 字段声明 | 字段列表 | SUBSET | tests | ✅ |
| `class A(B):` | 继承 | — | — | UNSUPPORTED | — | 🔮 |
| `@property` | 属性 | — | — | UNSUPPORTED | — | 🔮 |
| `@classmethod` | 类方法 | — | — | UNSUPPORTED | — | 🔮 |

## 六、模块

| Python | 实际语义 | 母语内语 | 周道 | 级别 | 实现证据 | 状态 |
|--------|---------|---------|------|------|---------|------|
| `import os` | 导入 Python 模块 | 引入 Python 模块 os | `引入Python模块《os》。` | EXACT | tests | ✅ |
| `from os import path` | 选择引入 | 从 Python 模块 os 引入 path | `从Python模块《os》中引入path。` | EXACT | tests | ✅ |
| `import os as sys` | 别名 | 下文简称 | `引入Python模块《os》，下文简称sys。` | EXACT | tests | ✅ |
| `from . import tool` | 相对引入 | — | — | UNSUPPORTED | — | 🔮 |
| 周道源文件 | — | 引入周道源文件工具 | `引入周道源文件《工具》。` | ZHOUDAO_NATIVE | tests | ✅ |
| 模块接口 | — | 规定模块接口 | `规定模块接口：整理、统计。` | ZHOUDAO_NATIVE | tests | ✅ |
| `__all__` | 公开接口 | — | `规定模块接口：` | INTENT_EQUIVALENT | tests | ✅ |

## 七、错误

| Python | 实际语义 | 母语内语 | 周道 | 级别 | 实现证据 | 状态 |
|--------|---------|---------|------|------|---------|------|
| `raise RuntimeError("m")` | 抛异常 | 报错 m | `报错【m】。` | EXACT | tests | ✅ |
| `raise ValueError("m")` | 指定类型 | 报错 m 类型值出错 | `报错【m】，错误类型是值出错。` | EXACT | tests | ✅ |
| `raise`（空） | 原样重抛 | 原样报出当前错误 | `原样报出当前错误。` | EXACT | tests | ✅ |
| `__doc__` | 文档字符串 | | 定义前连续 `注：` | SUBSET | 规范 | ⚠️ |
| 异常类型名 | 错误标识 | 6 种预定义 | `值出错` `键出错` 等 | ZHOUDAO_NATIVE | tests | ✅ |

## 八、程序结构

| Python | 实际语义 | 母语内语 | 周道 | 级别 | 实现证据 | 状态 |
|--------|---------|---------|------|------|---------|------|
| `if __name__ == '__main__':` | 入口 | 运行如下 | `运行如下：` | INTENT_EQUIVALENT | tests | ✅ |
| `yield x` | 生成值 | 依次给出 x | `依次给出x。` | EXACT | tests | ✅ |
| `await f()` | 等待完成 | 等待 f 完成 | `等待f（）完成。` | EXACT | tests | ✅ |
| `result = await f()` | 等待并取得结果 | 等待 f 完成记作结果 | `等待f（）完成，记作结果。` | EXACT | tests | ✅ |
| `match x:` | 模式匹配 | 依 x 分情形 | `依x分情形：` | EXACT | tests | ✅ |
| `case 1:` | 分支 | 若为 1 就 | `若为1，就` | EXACT | tests | ✅ |
| `case _:` | 默认 | 其余就 | `其余，就` | EXACT | tests | ✅ |

## 九、周道原生概念

| 概念 | 周道 | 说明 | 级别 | 实现证据 | 状态 |
|------|------|------|------|---------|------|
| 精确名称 | `{名称}` | 永不拆分、不参与上下文判断 | ZHOUDAO_NATIVE | 宪法第1条 | ✅ |
| 上下文自己 | `自己` | 类别方法中绑定到实例 | ZHOUDAO_NATIVE | tests | ✅ |
| 精确自己 | `{自己}` | 普通名称，不绑定到实例 | ZHOUDAO_NATIVE | tests | ✅ |
| 错误上下文字 | `错误` `错误内容` | 异常分支中的当前异常 | ZHOUDAO_NATIVE | tests | ✅ |
| 前置引导词 | `固定序列［` `集合［` `映射［` | 字面量类型前缀 | ZHOUDAO_NATIVE | tests | ✅ |

## 十、明确不支持

| Python 能力 | 理由 | 预期版本 |
|------------|------|---------|
| 链式比较 `a < b < c` | 语法复杂性 | 013+ |
| 继承 | 语义复杂性 | 012+ |
| 装饰器 `@decorator` | 语法未冻结 | 013+ |
| 上下文管理器 `with` | 非基础 | 012+ |
| 推导式 | 非基础 | 013+ |
| `*args` / `**kwargs` | 非基础 | 012+ |
| 参数解包 `*iter` | 非基础 | 012+ |
| 匿名函数 `lambda` | 非基础 | 013+ |
| 运算符重载 | 需完整类模型 | 014+ |
| `yield from` | 非基础 | 012+ |
| 异常组 `except*` | 复杂 | 014+ |
| 类型注解 | 需先确使用需求 | 013+ |
| 相对包引入 | 需包系统设计 | 012+ |
| `__init__` 自定义 | 已有字段模型替代 | 012+ |
| 描述器 `@property` | 需完整属性模型 | 013+ |
