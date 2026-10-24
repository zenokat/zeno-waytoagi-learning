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
# 第一批原生候选先定向匹配缓存，未知记录才逐月找，默认最多返回 3 条。
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
- `progressive_search.py`：原生候选与月份匹配的继续状态、最多三条交付。
- `summary_reader.py`：检索与摘要共用的记录索引及条目刷新；摘要陌生文章逐月查找。
- `monthly_logs.py`：跨主题共用的月级读取与七天缓存；不检查整年修订号。
- `verify_progressive.py`：不联网核对渐进续查、缓存期限、月初迁入与原摘要行为。
- `demo.py`：真实场景重放、样本核对及自包含结果页生成。
- `demo_template.html`：展示模板，按五个工具组织场景、结果卡片、调用时间线和核对结论；生成的 demo.html 仍是无需额外文件的独立回放。
- `demo.html`：本次已执行的回放；检索与摘要展示实际业务 JSON，保留命中片段及原摘要，内部诊断单独展开。其他三个工具仍展示精简结果，不内嵌文章全文或评论。
- `observed-checks.json`：本次机器可读核对结果，不替代 Linear 中的解释和限制。
- `timings.json`：逐场景、逐命令的作用说明、单条与累计耗时，以及工具完整返回耗时；运行 `demo.py` 会重新生成。
- 相邻 `waytoagi_daily.py`：仅导入已有 CLI 成功/身份校验、来源常量、行内引用解析；不修改正式脚本。

原生 fetch 返回后立即剥除评论 sidecar，再落盘、解析与交付。本次业务样本没有可见评论；过滤器存在不等于复杂评论格式已全面验收。

缓存和续查状态仅供单机、单用户实验，不是账户隔离或持久数据库。原型不会自动登录、改权限、降级钥匙串、升级 CLI 或写飞书内容。

检索保留 `drive +search` 查询语义，以 `create_time` 倒序逐批取得原生候选；取得候选 token 后先在日期范围内定向匹配有效缓存，有结果即交付，即使不足三条也不为凑数请求日志。无可交付结果时，优先刷新一条具有已知位置的过期记录；没有待定点刷新记录才逐月查找。首次最多取一批候选并做一次日志动作，后续优先交付已匹配结果，必要时推进一条刷新、一批候选或一个月；新批次候选也先匹配缓存。每次最多三条，没有对外 `page_size` 或月份推进参数。结果不足三条或暂时为空时，只要仍有工作就返回 `next_cursor` 和 `can_continue`；它表示可继续处理，不保证下一次一定找到文章。未匹配候选保留，不按创建月份排除；只提供时效性偏好，不承诺全局社区日期严格倒序。

社区日期先按查询范围筛选，再对实际遇到的重复文章保留最近记录，不为去重读取范围外日志。检索与摘要成功输出只含业务字段；调用记录和缓存诊断留在本地证据与演示内部区域。

摘要读取遵循三条路径：先按 token 查有效的本地原摘要；没有有效记录但保留日志 URL 与条目块 ID 时，仅刷新对应条目；完全没有可用记录或位置时，才逐月从近往远查找，找齐即停。检索已经保存原摘要，因此随后使用相同配置、缓存目录和返回的文章标识读取摘要，无须新增请求；不要求严格紧跟检索调用。完全陌生的旧文章独立读取仍可能较慢，演示保留这一缺口。

检索与摘要的条目记录均从成功获取后 7 天有效，包括已取得的当月记录；关键词检索命中有效条目即可复用，不再机械重读当月。相同 token 先选有效记录；同类记录再保留已观测的最近日期，不扫描范围外日志来证明全局最新。单条刷新另存记录及自己的获取时间，不改动整月缓存期限，也不更新同月其他条目。直接刷新保留已知的社区批次日期，不把抓取时间当作社区更新日期。

日志块读取允许外层容器 excerpt，但必须找到精确块 ID 的目标条目、核对文章引用且不存在条目内部节选或 tips，才按原日志解析规则返回摘要。位置失效或文章身份不符时明确失败，自动恢复仍交 ZEN-44。Wiki URL 可本地提取 token；独立传入 docx 别名仍可能需要原生身份解析请求。

纯日期发现没有候选 token，仍需月级覆盖，不能以零散条目缓存代替完整月份。未知记录需要按月查找时也沿用月级规则：当月每次需要读取时正常请求月份章节和近期日志；月初前八天将上月也视作活跃月份，以覆盖近期日志的滚动迁入。历史月缓存从成功获取起有效七天，跨查询词复用；满七天后再次用到才直接重读该月，不后台刷新、不预查整年 revision。活跃月不会直接转成稳定缓存，归档期后首次使用重新读取。续查复用本次查询已取得的数据，跨日长会话的刷新规则仍待 ZEN-44；新查询按上述策略读取。

月份锚点来自 `monthly-fixtures.json` 的真实观测，当前覆盖 2025-06 至 2026-10。新月份发现、标题或块删除重建引起的锚点变化、续查失效与失败恢复交 ZEN-44，本轮不自动修复锚点。

macOS 默认临时目录不在 CLI 图片输出白名单内，所以图片与正文使用 `/tmp`。保留 CLI 返回的 `saved_path`，它可能自动追加扩展名。若宿主沙箱不能访问已有钥匙串，应通过宿主的正常审批在可访问钥匙串的执行环境运行，不改凭证存储方式。

## 交接

### 摘要直接定位探索

`summary_lookup_probe.py` 对三篇已观测文章执行 11 项只读对照，输入为 `summary-lookup-samples.json`，本次观测保存于 `summary-lookup-results.json`。复跑命令：

```bash
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/summary_lookup_probe.py
```

它比较文章 token、标题、URL、已知日志块，以及一项已知摘要文字正对照。输出逐次请求、耗时、返回尺寸、目标引用是否存在和与固定原摘要是否逐字相等。正对照事先知道摘要文字，不能作为未知摘要的查找算法；已知块读取也不解决陌生文章 token 的反向定位。该实验保留探索阶段证据；后续主入口已按上述三条路径迭代，未采用年度整页兜底。来源变化后原文比较可能不再相等，应核查实际内容。研究解释与后续方案仍维护在 ZEN-43 关联报告。

### 按月检索性能实验

`monthly_experiment.py` 保留上一轮性能对照，不代表本轮渐进入口：比较一次读取全部日志与逐月读取，同一原生查询、每月结果完全一致时才输出有效对照。该实验首月获取完整原生候选，之后月份复用。`monthly-fixtures.json` 是已实际观测的章节锚点，直接读指定月份，不预读其他年份。锚点若不再对应该月，实验会停止；这不是自动适配未来年份的正式实现。

```bash
python3 skills/zeno-waytoagi-search/scripts/prototype_zen43/monthly_experiment.py --rounds 3 --months 17
```

每次使用新的输出目录。输出自包含 `monthly-experiment.html`、逐月业务结果、命令作用与耗时、三轮配对统计。业务结果保留命中片段，内部诊断另外展示。页面中的“提前停止”是以真实候选顺序做的离线检查，耗时由已测调用成本拆分估算，不是独立端到端计时；不能因为一个查询恰好没漏检，就把创建日期当作社区日期。

实测快照保存在 `monthly-results.json` / `monthly-experiment.html`（RAG）与 `monthly-narrow-results.json` / `monthly-narrow-experiment.html`（标题查询）。每个结果都以服务端本次返回至 `has_more=false` 的候选为基准，不承诺搜索覆盖全库。对照未控制服务端缓存，使用交替次序与三轮观测显示波动；本地内容缓存为空，但月份锚点已知。

当前按“可复现的主要路径”验证；未关联搜索候选、别名覆盖、源集合完整性、服务端截断上限、评论与复杂容器、失败状态和完整命中集交付方式均按 Linear 文档所列范围交接 [边界与异常原型票](https://linear.app/zenokat/issue/ZEN-44)。看到文件已生成，不等于这些问题已经解决。
