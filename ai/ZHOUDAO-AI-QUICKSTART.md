# 周道 AI Quickstart

> 给 AI 的快速入门指南。无需阅读编译器源码即可开始协作。

## 三步上手

### 1. 读取语言契约

先读 `ZHOUDAO-LANGUAGE-CONTRACT.md`，了解支持的和不支持的语法。
**不要凭"看起来像 Python"的感觉写周道。**

### 2. 读取项目上下文

如果项目中有 `.zhoudao/ai-context/` 目录，读里面的文件：

| 文件 | 内容 |
|------|------|
| `PROJECT-CONTEXT.md` | 项目结构、模块、入口 |
| `SYMBOL-INDEX.json` | 所有导出符号 |
| `CURRENT-DIAGNOSTICS.json` | 当前错误和警告 |

### 3. 修改 → 检查 → 运行

工作流程：

```
1. 读取语言契约
2. 读取项目上下文
3. 进行最小范围的修改
4. 运行 zhoudao.check 验证
5. 运行 zhoudao.format 格式化
6. 运行程序查看结果
7. 根据周道诊断修正错误
```

## 不能做的事

- ❌ 不能自己发明句式
- ❌ 不能重新拆分 `{精确名称}`
- ❌ 不能直接把 Python 代码混入周道源码
- ❌ 不能绕过 `zhoudao.check` 直接提交
- ❌ 不能假设周道支持了 Python 的全部特性

## 遇到困难时

1. 查看项目中的 `.zhoudao/` 目录
2. 运行 `zhoudao.check` 获取结构化诊断
3. 参考 `canonical-examples/` 目录中的合法示例
