# Domain Docs

## 探索代码前

读取根目录 `GLOSSARY.md`，以及 `docs/adr/` 中与当前任务有关的决策记录。
若以后存在 `GLOSSARY-MAP.md`，按其中的入口读取相关领域资料。

这些文件不存在时直接继续；术语和决策实际明确后，再由 domain-modeling 技能按需创建。

## 文件布局

采用 single-context：根目录 `GLOSSARY.md` 保存术语，`docs/adr/` 保存决策。

## 术语与决策

在 Issue、设计说明、代码及测试中使用术语表已有的名称。
提出的方案与已有 ADR 冲突时，明确指出对应记录及重新考虑的理由。
