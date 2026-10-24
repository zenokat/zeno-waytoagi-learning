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
# 第一批原生候选与当前月日志开始匹配，默认最多返回 3 条。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py search --query RAG

# 纯日期发现：只读取范围内月份；实际遇到重复文章时保留最近一次。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py search --since 2026-10-01 --until 2026-10-23

# 批量原始社区摘要；支持 Wiki 标识/URL，已知 docx 别名经 node-get 解析。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py summaries --articles Sb82wh600i3t9Nk6yO5cnWhZnCc YTt3wPPIeixEK5kbJPnc0YL7nTf

# 默认文章是能力报告中的 PDF 工具文章，可用 --article 替换为实际链接。
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py locate --keywords MarkItDown MinerU
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py structure --depth 2
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/prototype.py read
```

- 继续检索：`search --cursor '<上次返回的 next_cursor>'`，保持同一个 `--cache-dir` 与配置。
- 目录子层：`structure --section '<返回的章节 id>' --depth 1`。
- 单章或多章：`read --sections '<章节 id>' '<另一章节 id>'`。
- 章节范围：`read --start '<起点章节 id>' --end '<终点章节 id>'`；可仅给其中一端。
- 开篇正文的读取标识为 `@opening`，无标题文章为 `@document`。
- `prototype.py --profile '<已有配置名>'` 全程使用同一配置；演示脚本用默认用户配置。

## 文件与数据

- `prototype.py`：五个统一入口、章节模型和只读调用封装；旧整页日志路径仅为历史性能实验保留。
- `progressive_search.py`：原生候选与月份匹配的继续状态、最多三条交付、按需摘要查找。
- `monthly_logs.py`：跨主题共用的月级读取与七天缓存；不检查整年修订号。
- `verify_progressive.py`：不联网核对渐进续查、缓存期限、月初迁入与原摘要行为。
- `demo.py`：真实场景重放、样本核对及自包含结果页生成。
- `demo.html`：本次已执行的回放；检索与摘要展示实际业务 JSON，保留命中片段及原摘要，内部诊断单独展开。其他三个工具仍展示精简结果，不内嵌文章全文或评论。
- `observed-checks.json`：本次机器可读核对结果，不替代 Linear 中的解释和限制。
- `timings.json`：逐场景、逐命令的作用说明、单条与累计耗时，以及工具完整返回耗时；运行 `demo.py` 会重新生成。
- 相邻 `waytoagi_daily.py`：仅导入已有 CLI 成功/身份校验、来源常量、行内引用解析；不修改正式脚本。

原生 fetch 返回后立即剥除评论 sidecar，再落盘、解析与交付。本次业务样本没有可见评论；过滤器存在不等于复杂评论格式已全面验收。

缓存和续查状态仅供单机、单用户实验，不是账户隔离或持久数据库。原型不会自动登录、改权限、降级钥匙串、升级 CLI 或写飞书内容。

检索保留 `drive +search` 查询语义，以 `create_time` 倒序逐批取得原生候选；内部日志按月份从近到远读取。首次最多读取一批候选和一个月，后续先交付已匹配结果，必要时交替推进一批候选或一个月。每次最多三条，没有对外 `page_size` 或月份推进参数。结果不足三条或暂时为空时，只要仍有工作就返回 `next_cursor` 和 `can_continue`；它表示可继续处理，不保证下一次一定找到文章。未匹配候选保留，不按创建月份排除；只提供时效性偏好，不承诺全局社区日期严格倒序。

社区日期先按查询范围筛选，再对实际遇到的重复文章保留最近记录，不为去重读取范围外日志。摘要读取共用月级缓存，从近到远找齐即停。检索与摘要成功输出只含业务字段；调用记录和缓存诊断留在本地证据与演示内部区域。

当月每次需要读取时正常请求月份章节和近期日志；月初前八天将上月也视作活跃月份，以覆盖近期日志的滚动迁入。历史月缓存从成功获取起有效七天，跨查询词复用；满七天后再次用到才直接重读该月，不后台刷新、不预查整年 revision。活跃月不会直接转成稳定缓存，归档期后首次使用重新读取。续查复用本次查询已取得的数据，跨日长会话的刷新规则仍待 ZEN-44；新查询按上述策略读取。

月份锚点来自 `monthly-fixtures.json` 的真实观测，当前覆盖 2025-06 至 2026-10。新月份发现、标题或块删除重建引起的锚点变化、续查失效与失败恢复交 ZEN-44，本轮不自动修复锚点。

macOS 默认临时目录不在 CLI 图片输出白名单内，所以图片与正文使用 `/tmp`。保留 CLI 返回的 `saved_path`，它可能自动追加扩展名。若宿主沙箱不能访问已有钥匙串，应通过宿主的正常审批在可访问钥匙串的执行环境运行，不改凭证存储方式。

## 交接

### 按月检索性能实验

`monthly_experiment.py` 保留上一轮性能对照，不代表本轮渐进入口：比较一次读取全部日志与逐月读取，同一原生查询、每月结果完全一致时才输出有效对照。该实验首月获取完整原生候选，之后月份复用。`monthly-fixtures.json` 是已实际观测的章节锚点，直接读指定月份，不预读其他年份。锚点若不再对应该月，实验会停止；这不是自动适配未来年份的正式实现。

```bash
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/monthly_experiment.py --rounds 3 --months 17
```

每次使用新的输出目录。输出自包含 `monthly-experiment.html`、逐月业务结果、命令作用与耗时、三轮配对统计。业务结果保留命中片段，内部诊断另外展示。页面中的“提前停止”是以真实候选顺序做的离线检查，耗时由已测调用成本拆分估算，不是独立端到端计时；不能因为一个查询恰好没漏检，就把创建日期当作社区日期。

实测快照保存在 `monthly-results.json` / `monthly-experiment.html`（RAG）与 `monthly-narrow-results.json` / `monthly-narrow-experiment.html`（标题查询）。每个结果都以服务端本次返回至 `has_more=false` 的候选为基准，不承诺搜索覆盖全库。对照未控制服务端缓存，使用交替次序与三轮观测显示波动；本地内容缓存为空，但月份锚点已知。

当前按“可复现的主要路径”验证；未关联搜索候选、别名覆盖、源集合完整性、服务端截断上限、评论与复杂容器、失败状态和完整命中集交付方式均按 Linear 文档所列范围交接 [边界与异常原型票](https://linear.app/zenokat/issue/ZEN-44)。看到文件已生成，不等于这些问题已经解决。
