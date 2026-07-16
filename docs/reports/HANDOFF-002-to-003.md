# 周道 Handoff — v0.0.2 → v0.0.3

> 日期：2026-07-16
> 当前版本：v0.0.3
> 状态：003 歧义宪法已完成文档 + 模块 + 语料，尚未集成到主线解析器

---

## 项目架构

```
experiments/周道/
├── 周道/                    # Python 包（核心引擎）
│   ├── lexer.py           # 词法分析器（字符级扫描 + 最长关键字匹配）
│   ├── parser.py          # 递归下降解析器
│   ├── emitter.py         # 周道 AST → Python 代码生成
│   ├── ast_nodes.py       # AST 节点类型
│   ├── tokens.py          # Token 类型常量 + 关键字映射
│   ├── runner.py          # CLI 入口（转译/运行/检查）
│   ├── errors.py          # 错误类型（词法/语法/语义/运行时）
│   ├── exact_identifier.py # 精确名称 `{名称}` 提取器（v0.0.3 新增）
│   ├── nametable.py        # 单作用域名称表（v0.0.3 新增）
│   ├── name_lattice.py     # 嵌套作用域名称解析（v0.0.3 新增）
│   └── context_resolver.py # 上下文关键字消歧（v0.0.3 新增）
├── docs/                    # 规范文档（v0.0.3）
│   ├── AMBIGUITY-CONSTITUTION.md   # 歧义宪法总纲
│   ├── IDENTIFIER-SPEC.md          # 标识符规范
│   ├── NAME-RESOLUTION.md          # 名称解析规则
│   ├── CONTEXTUAL-KEYWORDS.md      # 上下文关键字规范
│   ├── EXPRESSION-PRECEDENCE.md    # 表达式优先级表
│   └── PUNCTUATION-SCOPE.md        # 标点作用域规范
├── tests/
│   ├── test_周道.py                # 第一批回归（33 项）
│   ├── test_acceptance_002.py      # 第二批验收（52 项）
│   └── corpus/
│       └── ambiguity_cases.json    # 265 条歧义语料
├── examples/                # 10 个 .zd 示例程序
├── grammar.md               # 形式语法
├── ACCEPTANCE-002-R3.md     # v0.0.2 最终验收报告
├── README.md                # 语言文档
└── HANDOFF-002-to-003.md    # 本文件
```

---

## 已完成的工作

### v0.0.1 — 基础管线（33 测试）
- 词法分析 → AST → Python 发射器管线
- 基础句法：绑定/变更/输出/如果/当/遍历/函数/模块/异常
- 第一批 33 项回归测试

### v0.0.2 — 第二批句法（85 测试，3 轮修复）
- 第二批语法：类别、断言、作用域、分情形、等待、依次给出
- 修复 5 个阻断问题（类别爆破、async def、成员映射、测试假阳性、try/finally）
- 经过 3 轮外部验收（R1→R2→R3）
- CLI --check 完整管线 + 错误分类
- 中文模块/成员名映射

### v0.0.3 — 歧义宪法与名称系统（当前）
- 六份歧义规范文档（宪法/标识符/名称解析/上下文关键词/优先级/标点）
- 265 条歧义语料（26 分类）
- 4 个名称系统模块：
  - `ExactIdentifier` — `{名称}` 精确名称提取
  - `NameTable` — 单作用域名称表
  - `NameLattice` — 嵌套作用域名称解析
  - `ContextResolver` — 上下文关键字消歧

---

## 当前限制

1. **名称系统未集成**：NameLattice / ContextResolver 尚未接入 parser.py
2. **精确名称词法**：`{}` 的 lexer 支持尚未在 lexer.py 中实现
3. **控制结构作用域**：函数体内 `如果` 块的变量作用域隔离为建议，非强制
4. **语料未转 pytest**：265 条歧义语料尚未转为可执行的自动化测试
5. **花括号名称**：ExactIdentifier 提取器已实现，但尚未替换 parser 中的普通标识符解析

---

## 下一步（004 / 具体路线）

### 短期（下一任务）
1. **精确名称集成**：将 `{}` 支持加入 lexer.py，parser 识别精确名称
2. **NameLattice 集成**：在 parser 中添加作用域跟踪，替代当前的 `_在定义内`/`_循环深度`
3. **语义拒绝前置**：将 ContextResolver 接入 --check 管线
4. **语料测试化**：将 ambiguity_cases.json 转为 pytest 参数化测试

### 中期
- Core IR 设计（表层 AST → 归一化中间表示）
- 避免 "中文句子 → 拼接 Python 字符串" 的长期依赖
- 使不同的白语句式归一为相同底层语义

### 远期
- 类别方法、继承
- 更丰富的静态分析
- SomaOS 能力域注册（`language.zhoudao`）

---

## 关键技术债务

| 债务 | 影响 | 建议解决时机 |
|------|------|------------|
| parser.py 已膨胀到 700+ 行 | 可维护性下降 | 004 拆分为多文件 |
| emitter.py 的 `_发射语句` 用长串 isinstance 链 | 难扩展 | 004 改用访问者模式 |
| 词法层关键字与中文标识符冲突（"完成""等待""时"等） | 用户变量名受限 | 003 宪法已定义精确名称机制 |
| 无独立语义分析阶段 | 语义检查散布在 parser 中 | 004 引入独立语义通道 |
| 组合程序测试依赖特定运行环境 | 可重现性受限 | 005 容器化测试 |

---

## 关键联系人

- 项目：SomaOS Combo Lab（somaos-combo-lab）
- 仓库：`G:/AI/Claude-Workspace/Projects/somaos-combo-lab`
- 实验目录：`experiments/周道/`
- Git：`integration/soma-runtime-candidate-001` 分支

---

## 启动下一任务

```bash
# 运行全部测试
cd G:/AI/Claude-Workspace/Projects/somaos-combo-lab
PYTHONPATH="experiments/周道" python -m pytest "experiments/周道/tests/" -q

# CLI 检查
PYTHONIOENCODING=utf-8 python -m 周道 --check examples/counter.zd
PYTHONIOENCODING=utf-8 python -m 周道 examples/counter.zd

# 版本确认
python -c "import 周道; print(周道.__version__)"
```
