# Issue tracker: GitHub

本仓库的任务和规格记录在 GitHub Issues，使用 `gh` CLI 操作。从项目的 Git remote 判断仓库。

## 操作约定

- 创建任务：`gh issue create --title "..." --body-file <file>`。多段正文先写入临时文件，保留实际换行。
- 读取任务：`gh issue view <number> --json number,title,body,labels,comments`。
- 列出任务：`gh issue list --state open --json number,title,body,labels`；按需使用 `--label`。
- 评论：`gh issue comment <number> --body-file <file>`。
- 设置或移除标签：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`。
- 完成任务：`gh issue close <number>`，先在任务中留下结果与验证依据。
- 父子任务优先使用当前 CLI 支持的原生 sub-issue 操作；不可用时在子任务正文记录 `Part of #<parent>`，并在父任务中维护任务清单。
- 依赖优先使用 GitHub 原生 issue dependencies；不可用时记录 `Blocked by: #<number>` 并核对阻塞任务状态。

## Pull requests as a triage surface

**PRs as a request surface: no.**

技能要求“发布到 issue tracker”时，创建 GitHub Issue；要求“获取 ticket”时，读取对应 Issue。
