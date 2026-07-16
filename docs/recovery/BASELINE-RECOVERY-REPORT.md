# 基线恢复报告

## 可信基线

| 字段 | 值 |
|------|-----|
| Git commit | `c2cd659` |
| 版本 | v0.0.7 (SEED-007) |
| 测试结果 | 602 passed, 1 skipped, 0 failed |
| 日期 | 2026-07-16 |

## 当前分支

`integration/soma-runtime-candidate-001`

## 故障版本（stashed）

所有 008/009/010 修改已保存为两个 stash：

| Stash | 内容 |
|-------|------|
| `stash@{0}` | `full-recovery-snapshot-all` — 全部改动（含新增文件） |
| `stash@{1}` | `pre-recovery-snapshot` — 仅跟踪文件改动 |

## 恢复路线

按照 TASK-ZHOUDAO-SEED-009-010-RECOVERY 的顺序：

1. ✅ **基线建立完成**（当前）
2. ⬜ 修复精确名称宪法
3. ⬜ 恢复 Core IR 构造契约
4. ⬜ 修复文章结构归属
5. ⬜ 停止补丁式分词
6. ⬜ 重新验收 009
7. ⬜ 完成 010

每步从 stash 弹出最小改动集，记录相互影响，避免"一起修复"的混乱。
