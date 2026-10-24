# ZEN-43 五工具技术原型

可丢弃实验资产。仅在 `codex/prototype-zen43-five-tools` 分支保存，不合入正式实现。

规格、证据解释、技术表及后续限制统一维护在 [技术实现原型票](https://linear.app/zenokat/issue/ZEN-43) 的关联文档与[工具设计](https://linear.app/zenokat/document/工具设计-46589bf68b1a)。本目录不是生产接口或研究报告。

## 一条命令运行

从仓库根目录执行（需要已有可用的 `lark-cli 1.0.96` 用户认证和 Python 3.10+）：

```bash
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/demo.py
```

脚本使用真实只读调用，打印进度，最终返回 `demo.html` 和 `evidence.json` 的绝对路径。双击 HTML 可逐步查看这次运行的输入、内部调用及结果；它是离线回放，切换按钮不会重新联网。原生响应、正文与图片保存在本机临时目录。临时文件清除后可重新执行；演示中的旧路径不会自动恢复。

演示的每条 command 附中文作用、单条耗时和从本次工具接收输入开始的累积耗时（秒）。计时在命令返回结果时记录，包含此前命令和其间本地处理；每个场景独立从零开始，不含人浏览页面的等待。工具完整返回耗时另外列出，包含末尾的本地整理。数据是本次真实运行的观测，不是性能保证。

`demo.py` 的针对性断言用于核对本次样本的分页、原摘要、章节范围及图片，不是系统性异常测试。重复执行会重新读取最新来源；源文章变化可能使固定样本的断言失败，需据真实结构更新演示，不得改成模拟成功。

## 五个独立入口

```bash
# 原生全部候选页完成后，再关联社区日志、排序并生成快照页。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py search --query RAG --page-size 3

# 纯日期发现：先归并同文章的最新记录，再筛日期。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py search --since 2026-10-01 --until 2026-10-23

# 批量原始社区摘要；支持 Wiki 标识/URL，已知 docx 别名经 node-get 解析。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py summaries --articles Sb82wh600i3t9Nk6yO5cnWhZnCc YTt3wPPIeixEK5kbJPnc0YL7nTf

# 默认文章是能力报告中的 PDF 工具文章，可用 --article 替换为实际链接。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py locate --keywords MarkItDown MinerU
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py structure --depth 2
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py read
```

- 下一页：`search --cursor '<上次返回的 next_cursor>' --page-size 3`，保持同一个 `--cache-dir`。
- 目录子层：`structure --section '<返回的章节 id>' --depth 1`。
- 单章或多章：`read --sections '<章节 id>' '<另一章节 id>'`。
- 章节范围：`read --start '<起点章节 id>' --end '<终点章节 id>'`；可仅给其中一端。
- 开篇正文的读取标识为 `@opening`，无标题文章为 `@document`。
- `prototype.py --profile '<已有配置名>'` 全程使用同一配置；演示脚本用默认用户配置。

## 文件与数据

- `prototype.py`：五个统一入口、来源修订缓存、章节模型和只读调用封装。
- `demo.py`：真实场景重放、样本核对及自包含结果页生成。
- `demo.html`：本次已执行的精简回放；只保留标题、定位、计数、调用参数及本地文件指针，不内嵌全文或评论。
- `observed-checks.json`：本次机器可读核对结果，不替代 Linear 中的解释和限制。
- `timings.json`：逐场景、逐命令的作用说明、单条与累计耗时，以及工具完整返回耗时；运行 `demo.py` 会重新生成。
- 相邻 `waytoagi_daily.py`：仅导入已有 CLI 成功/身份校验、来源常量、行内引用解析；不修改正式脚本。

原生 fetch 返回后立即剥除评论 sidecar，再落盘、解析与交付。本次业务样本没有可见评论；过滤器存在不等于复杂评论格式已全面验收。

缓存和快照仅供单机、单用户实验，不是账户隔离或持久数据库。每次正常新查询检查来源修订；快照续页则复用同一次排序结果。源码变化也通过解析版本失效缓存。原型不会自动登录、改权限、降级钥匙串、升级 CLI 或写飞书内容。

macOS 默认临时目录不在 CLI 图片输出白名单内，所以图片与正文使用 `/tmp`。保留 CLI 返回的 `saved_path`，它可能自动追加扩展名。若宿主沙箱不能访问已有钥匙串，应通过宿主的正常审批在可访问钥匙串的执行环境运行，不改凭证存储方式。

## 交接

当前按“可复现的主要路径”验证；未关联搜索候选、别名覆盖、源集合完整性、服务端截断上限、评论与复杂容器、失败状态和完整命中集交付方式均按 Linear 文档所列范围交接 [边界与异常原型票](https://linear.app/zenokat/issue/ZEN-44)。看到文件已生成，不等于这些问题已经解决。
