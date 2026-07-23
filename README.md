# 周道 · Zhōu Dào

> **用中文写 Python。** 不用英文关键字、不用缩进、不用冒号、不用花括号。

周道是一套完整的**中文编程语言原型**——它使用现代中文句法、数学表达和中文标点，先解析为独立 AST，再转译到标准 Python 执行。它借用 CPython 的运行时与生态，但不创造自己的虚拟机。

```text
定义斐波那契（序号）如下：
  如果序号 <= 1，就以序号为所得；
  以斐波那契（序号-1）+斐波那契（序号-2）为所得。

运行如下：
  设索引为0，当索引<15时，一直显示斐波那契（索引），并使索引加1。
```

---

## 为什么有周道

编程语言的语法本质上是**给人类读的协议**。英文关键词对非英语母语者构成了一道隐形的认知门槛——不是不能学，而是每次阅读都需要在"英文关键词 → 语义"之间做一次映射。

周道尝试一个简单的假设：

> **如果用完整的母语句法来表达逻辑，阅读代码的认知负荷会不会更低？**

这不是要取代 Python，也不是否定英文编程的价值。周道是一个语言原型，用来探索这个假设的真实边界。

---

## 示例一览

周道自带 **10 个渐进式示例项目**，覆盖从基础到进阶的全部语法特性：

| 项目 | 说明 | 语法亮点 |
|------|------|---------|
| `projects/p1-text-processor/` | 文本处理 | 函数定义、字符串操作、遍历 |
| `projects/p2-multi-file/` | 多文件模块 | 模块引入、跨文件调用 |
| `projects/p3-state-machine/` | 红绿灯状态机 | 类别定义、状态切换、`自己` |
| `projects/p4-error-handler/` | 错误处理 | `尝试`、`报错`、错误类型 |
| `projects/p5-generator-pipeline/` | 生成器流水线 | `依次给出`、惰性求值 |
| `projects/p6-async/` | 异步消息 | `等待`、`每等到一项记作` |
| `projects/p7-python-interop/` | Python 互操作 | 引入 Python 标准库 |
| `projects/p8-word-frequency/` | 词频统计 | 映射（字典）、方法链 |
| `projects/p9-table-cleaner/` | CSV 清洗 | 字符串分割、逐行处理 |
| `projects/p10-list-cleaner/` | 列表操作 | `的`方法调用、排序、复制 |

```bash
# 运行任一项目
python -m 周道 projects/p1-text-processor/main.zd
python -m 周道 projects/p3-state-machine/traffic.zd
```

---

## 快速开始

```bash
pip install -e .          # 安装周道

# 运行 .zd 文件
python -m 周道 projects/p1-text-processor/main.zd

# 仅查看生成的 Python 代码
python -m 周道 projects/p1-text-processor/main.zd --emit

# 仅检查语法
python -m 周道 projects/p1-text-processor/main.zd --check
```

### 语法一览

| 句式 | 形式 | 说明 |
|------|------|------|
| 绑定 | `设 甲 为 乙。` | 建立名称 |
| 变更 | `使 甲 变为 乙。` | 改变值 |
| 输出 | `显示 甲。` | 打印 |
| 条件 | `如果 甲，就 乙，不然就 丙。` | if/else |
| 循环 | `当 甲 时，一直 乙。` | while |
| 遍历 | `从 甲 中，每取一项记作 乙，就 丙。` | for |
| 函数 | `设 平方（数）为 数 * 数。` | 函数定义 |
| 异常 | `尝试 甲，如果出错，就 乙。` | try/except |
| 模块 | `引入 Python 模块《json》` | import |

完整的运算符、字面量和句式表见 [语法索引](./docs/SURFACE-GRAMMAR-INDEX.md)。

---

## 设计理念

- **不翻译 Python 关键词**——不使用 `定义` 对应 `def`、`返回` 对应 `return`，而是寻找中文读者无需编程知识也能理解的完整句式
- **数学符号 + 汉语式双表层**——`+ - * / =` 保留数学直觉，`加 减 等于` 保留母语节奏，两者等价
- **设与使用别**——`设` 用于建立，`使` 用于改变
- **所得即结果**——`以…为所得` 表达函数返回值
- **结构指称**——`其姓名` 在遍历体内指向当前元素

---

## 管线架构

```
源码 → Lexer → Parser → Surface AST → Lowering → Core IR
     → Semantic Analysis → Backend（AST / text）→ Python
```

- **ast 后端（默认）**：直接构造 Python `ast.AST`，带异常位置映射
- **text 后端**：字符串拼接，用于调试和差分对照

```bash
python -m 周道 file.zd          # 编译 + 执行
python -m 周道 file.zd --emit   # 仅输出 Python 代码
python -m 周道 file.zd -o out.py # 转译为 .py 文件
python -m 周道 file.zd --check  # 仅检查语法
```

---

## 标准库

周道内置了中文命名的基础能力库，无需引入即可使用：

- **文件与路径**：`读取文本` `写入文本` `判断存在` `建立目录` `列出目录`
- **文本处理**：`分割` `替换` `查找` `计数` `转为大写` `转为小写`
- **数据结构**：`排序` `反转` `追加` `插入` `移除` `各键` `各值`
- **系统调用**：`执行命令` `环境变量` `目前目录` `此刻时间` `休眠`
- **软技能调用**：`调用软技能`——调用 MCP 软技能（Soma 集成）

完整列表见 [stdlib.py](./周道/stdlib.py)。

---

## 项目结构

```
周道/
├── 周道/                     # 核心源码
│   ├── lexer.py              # 词法分析器
│   ├── parser.py             # 句法解析器
│   ├── lowering.py           # 降低到 Core IR
│   ├── emitter.py            # text 后端
│   ├── ast_backend.py        # Python AST 后端（默认执行路径）
│   ├── semantic_analyzer.py  # 语义分析
│   ├── runner.py             # 运行器与 CLI
│   ├── stdlib.py             # 中文标准库
│   └── ...
├── projects/                 # 10 个渐进式示例项目
│   ├── p1-text-processor/    # 文本处理
│   ├── p2-multi-file/        # 多文件模块
│   ├── p3-state-machine/     # 红绿灯状态机
│   ├── p4-error-handler/     # 错误处理
│   ├── p5-generator-pipeline/# 生成器流水线
│   ├── p6-async/             # 异步消息
│   ├── p7-python-interop/    # Python 互操作
│   └── ...
├── tests/                    # 验收测试
├── docs/                     # 设计与规范文档
└── README.md
```

---

## 许可

v0.0.10rc1 — 候选发布，非生产软件。

周道在 Python 3 的 Unicode 标识符支持和标准库之上构建。文件名、包名、变量名全面使用中文。
