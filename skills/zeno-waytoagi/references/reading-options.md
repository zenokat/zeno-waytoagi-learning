# 扩展读取

基本更新、搜索和正文读取直接按 SKILL.md 执行；仅在需要较早更新、翻页、标题筛选或局部正文时查阅本文。沿用当前飞书配置，命名配置的调用继续携带同一 `--profile`。

## 较早更新

每日脚本只读取入口文档的“近 7 日更新日志”。请求超出窗口时，对[历史更新页](https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc)使用下方[目录与章节读取](#局部正文)：从目录中的年月和日期标题定位批次，再按该日期标题的块 ID 读取条目。历史页的实际内容决定能覆盖的范围。

保留来源日期。文档修改时间不能代替条目发布日期，不能把未找到某批次写成该日没有更新。

## 扩展搜索

- 翻页：响应的 `has_more=true` 表示还有结果；保留原关键词、知识库和筛选条件，追加返回的 `--page-token`。按任务需要继续，不用第一页推断全库总量。
- 后续页失败、令牌重复或没有新增结果时，按[失败处理](failures.md)处理；恢复后仍无法继续就停止，保留已取得条目并注明仅有部分结果，不无限翻页。
- 只查标题：追加 `--only-title`。
- 展示结果：去掉标题与摘要中的高亮标签，保留实际 URL。元数据时间为 0 时按未提供处理；目录、快捷方式和文章不能混作独立教程数量，搜索结果也不提供热门排行依据。

## 局部正文

按章节读取时，先获取目录与实际块 ID：

```bash
lark-cli docs +fetch --doc "文章链接" --as user --scope outline --detail with-ids
lark-cli docs +fetch --doc "文章链接" --as user --scope section --start-block-id "返回的章节块ID" --doc-format markdown --detail simple
```

按关键词取得上下文：

```bash
lark-cli docs +fetch --doc "文章链接" --as user --scope keyword --keyword "关键词" --doc-format markdown --detail simple
```

关键词结果或 `<excerpt>` 是局部内容，不等于整节或全文。上下文不足时，从目录定位相关章节，再按该章节的实际块 ID 读取；出现 `tips` 时说明限制。保留本次来源、范围与引用，媒体及独立表格未读取时明确标记。
