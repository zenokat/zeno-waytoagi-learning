# 读取功能验收

Skill 中的可执行读取路径必须有对应的用例并实际通过。CLI 帮助、文档格式和链接检查不能替代行为验证。新增参数组合应先补用例，验证实际内容与范围，再写入 Skill。

## 功能与用例

| SKILL.md / reading-options.md 的能力 | 用例与检查内容 |
| --- | --- |
| 按日期读取近期更新 | `test_recent_date_reads_only_the_matching_recent_batch` 验证显式日期与来源；联网 `test_latest_update_has_original_material_and_actual_date` 从实际日期调用脚本，检查批次、原条目和链接。 |
| 指定日期 | 离线 `test_retains_summary_and_only_requested_day` 等；联网 `test_requested_date_returns_same_batch` 验证指定真实日期取得同批次原条目。 |
| 日期未出现、超出支持范围及读取失败 | `DateCommandTests` 覆盖目标缺失、2025-06-01起点及前一天、无效/未来日期和归档失败；保留结构变化、节选、缺引用与 CLI 错误报告检查。 |
| 知识库搜索 | 联网 `test_search_returns_waytoagi_links_and_matching_context` 检查关键词命中、标题、摘要字段及知识库 URL。 |
| 翻页 | 联网 `test_search_pagination_returns_new_same_space_results` 用真实令牌取得新增结果并保持同一知识库。 |
| 仅查标题 | 联网 `test_title_only_search_matches_every_title` 检查每个返回标题实际命中。 |
| 全文与目录 | 联网 `test_full_article_contains_multiple_sections_and_body`、`test_outline_returns_heading_ids` 检查跨章节正文、范围和实际块 ID。 |
| 按章节读取 | 联网 `test_section_returns_body_and_stops_before_next_peer` 检查该节正文和同级标题边界。 |
| 关键词上下文及继续展开 | 联网 `test_keyword_returns_matching_local_context`、`test_keyword_context_can_expand_via_outline_section` 检查局部标记、实际命中及从目录定位章节后的继续读取。 |
| 统一历史更新 | `test_date_query_follows_year_route_and_preserves_original_entry`、同月日跨年与年末元旦用例；联网 `test_historical_update_page_returns_older_dated_entries` 用同一脚本核对2025起点、年末、2026元旦与当年历史条目。 |
| 全年度实际批次 | `test_all_supported_archive_batches_preserve_original_entry_ids` 临时读取真实年度快照，对每个支持日期回放脚本公开入口，核对全部原条目ID，避免漏项和混入其他日期。回放不是逐日联网。 |
| 命名配置转发 | 离线测试覆盖每日命令及两次底层请求；整组联网用例可携带同一 `WAYTOAGI_PROFILE` 复验真实配置。 |
| 脚本对环境与 CLI 失败的报告 | 离线 `DailyFailureTests` 覆盖缺 CLI、超时、授权/权限/资源/限流/凭证存储错误和非 JSON 响应下的原因保留与退出行为；缺时区库用真实独立进程复现并验证错误 JSON。不验证 CLI 内部授权或故障恢复流程。 |
| 无命中与不合法读取目标 | 联网 `test_no_search_match_is_success_with_empty_results`、`test_unknown_profile_identifies_configuration_gap`、`test_missing_section_id_is_rejected` 区分空搜索、未配置和失效章节错误。 |

离线用例见 [原文提取与失败报告](../tests/test_waytoagi_daily.py)、[统一日期命令](../tests/test_waytoagi_updates.py)；联网用例见 [真实读取](../tests/test_waytoagi_live.py)、[年度快照回放](../tests/test_waytoagi_archive_live.py)。

## 运行方式

从仓库根目录运行离线测试：

```bash
python3 -m unittest discover -s tests -v
```

默认执行 48 个离线用例，并明确跳过 15 个联网用例。跳过不等于联网验收通过。

在可访问系统钥匙串、已有有效飞书授权的环境中，单独运行联网验收：

```bash
WAYTOAGI_LIVE=1 python3 -m unittest discover -s tests -p '*live.py' -v
```

需要指定已有配置时，同一命令再设置 `WAYTOAGI_PROFILE=<配置名>`。测试只读，不登录、不创建应用、不保存响应正文或凭证；没有可用账号、网络失败或来源变化都会报失败，需要核对后重验。

## 本次结果与边界

2026-10-12，官方 CLI 1.0.96、已有飞书应用及用户授权：28 个离线用例通过，11 个联网用例通过；显式指定现有配置的整组读取也通过。

2026-10-13，官方 CLI 1.0.96 补充异常验收：缺少时区数据时原脚本在导入阶段崩溃，现已改为返回失败 JSON 与补齐 `tzdata` 的提示；缺 CLI 和超时增加明确原因。33 个离线用例、14 个联网用例均通过，含无命中、未配置及失效章节的真实响应。

2026-10-14，共同完成一次空白 Linux 环境的实际 setup 主流程：独立 Codex Agent 从本地 Skill 副本安装，准备 Python、时区与官方 CLI 1.0.97，使用新创建的飞书应用完成浏览器接入和首次用户授权。三项用户身份读取均通过：最近批次 2026-10-13、5 条，ComfyUI 本页 5 条且还有下一页，命中文章正文输出 21,431 字符。过程、遇到的问题和接续记录见[首次配置体验记录](setup-walkthrough.md)。实际权限范围宽于请求的两项；按已确认需求，权限足够即继续，不以收窄权限作为完成条件。本次没有验证最小权限集合，也没有新增自动化测试覆盖。

创建时间筛选暂未纳入 Skill。搜索结果的创建、更新时间样本为 0；2026-10-15 补查发现可通过 `wiki +node-get` 的节点详情核对真实时间，候选路径的实际探索见下节。完整筛选与分页覆盖仍需验证后再加入。

测试证明这里列出的读取路径及样本结果；不保证所有文档、账号和日期都可访问，也不验证其他平台外链或未展开媒体。[失败处理](../skills/zeno-waytoagi/references/failures.md)中的有界重试与部分结果交付是 Agent 执行约定，不是脚本自动恢复能力。CLI 的配置、授权与通用故障恢复由 [setup.md](../skills/zeno-waytoagi/setup.md) 路由到上游，不列为本 Skill 需要逐项覆盖的内部流程。

2026-10-14 的路由改稿已在 CLI 1.0.97 确认 `lark-cli skills read lark-shared` 可返回配置、身份与权限参考索引；改稿后的完整 Agent setup 尚未重跑。此前首次配置覆盖了新应用接入、用户授权确认后的接续和三项实际读取，没有覆盖本产品职责内的所有分支、其他安装环境或普通新账号的访问条件，不能写成完整异常与边界验收。

同日检查 setup 对其他文档的影响并统一路由与测试职责说明。修改前后均为 33 个离线用例通过、14 个联网用例跳过；13 份 Markdown 的本地文件链接与 diff 检查通过。脚本与测试代码未变，未新增覆盖项通过的声明。

## 按创建时间统一检索的探索（2026-10-15）

本次为候选方案的只读实测，未修改 Skill 功能、脚本或测试。环境为官方 CLI 1.0.96、已有用户授权，统一按 `Asia/Singapore`（UTC+8）比较日期。

依据 [CLI 官方搜索说明](https://github.com/larksuite/cli/blob/main/skills/lark-drive/references/lark-drive-search.md)，`--created-since/until` 对应文档创建时间，`--edited-since/until` 对应“我编辑过”的时间，不能当作全库的修改日期筛选。空关键词加知识库范围可浏览，`--sort edit_time` 可排序；本次首页混合返回了文章、首页与表格，样本的 `create_time/update_time` 均为 0，不能用其格式化后的 1970 年日期作证据。

实际执行 2026-10-01 至 10-15、2025-05-01 至 06-01 两个创建日期窗口，均返回非空结果且还有下一页；各抽查前两篇的节点详情，四篇文档创建时间均在对应窗口内。这仅证明这些样本吻合，不是全量召回、分页或日期边界验收。

随后按用户要求，比较更新日志日期与引用文档的实际时间。固定取近期两天全部条目，以及历史页 9 月、5 月、1 月各最新一天的全部引用，共 32 篇；不是随机样本，历史样本集中在月末，比例不能推及全库。近期来源为[入口更新日志](https://waytoagi.feishu.cn/wiki/QPe5w5g7UisbEkkow8XcDmOpn8e)，历史来源为[历史更新页](https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc)。历史三个章节均未返回节选或限制提示。

| 日志日期 | 文档数 | 当天创建 | 次日创建 |
| --- | ---: | ---: | ---: |
| 2026-10-14 | 6 | 3 | 3 |
| 2026-10-13 | 5 | 5 | 0 |
| 2026-09-30 | 8 | 1 | 7 |
| 2026-05-31 | 6 | 0 | 6 |
| 2026-01-31 | 7 | 4 | 3 |
| 合计 | 32 | 13 | 19 |

全部节点查询成功，文档创建时间与节点创建时间在这 32 篇中逐秒相同；与日志的日期差均为 0 或 +1 天。最近修改日期则有 11 篇当天、20 篇次日、1 篇晚 31 天：[Clawdbot 教程 01](https://waytoagi.feishu.cn/wiki/GycBwU1RxiSYjYkYEaOcWgHhnCb)列在 1 月 31 日日志，2 月 1 日 01:10 创建，3 月 3 日 15:15 最近修改。逐条数据与来源链接见[日期对照表](update-date-comparison.csv)。

当时判断：样本支持创建日期与日志“时间接近”，不支持“精确同日等价”，也不能证明搜索结果集合与日志条目完全一致。后续用户已决定保留日志日期口径，最终实现见下一节。

## 按日志日期统一读取（2026-10-15）

用户决定保留更新日志日期口径，统一使用 `waytoagi_daily.py --date YYYY-MM-DD`；随后根据实际旧记录的混合格式，将产品支持起点收敛到 **2025-06-01**。早于起点直接返回 `outside_supported_range`，不读取或兼容2023—2024年、2025年上半年的杂项与范围记录。上一节的创建时间方案保留为探索证据，不纳入产品。

脚本先查近期板块；目标不在其中时，查[年度更新页](https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc)，并按页首真实路由进入[2025年归档](https://waytoagi.feishu.cn/wiki/GL7xwM3fyitr4kkiv76c1GHjnNg)。年份依据来源目录与年份路由，正文引用的外部平台链接原样保留。原始正文只在测试内存或临时目录使用，不收录进仓库；仓库发布代码、测试和验证结果。

| 需求 / 推导方向 | 覆盖与证据 |
| --- | --- |
| 日期输入 / 等价类与边界 | 必填、错误格式、不存在日期、未来日期；起点2025-06-01成功，前一天和更早年份超出范围。 |
| 来源选择 / 决策表与场景 | 近期命中、当前年度归档、跨年路由、同月日不同年份、年末与次年元旦；命名配置和用户身份贯穿各页。 |
| 结果与失败分支 / 场景 | 日期缺失不换日，路由缺失报错；重复日期、来源/锚点/日期错配、节选、空批次、未知结构和权限失败不冒充空更新。 |
| 原文保真与全部条目 | 已有摘要、引用与链接检查；年度快照每个支持日期的输出条目ID与原始列表逐项对应。 |

最终离线 **48 个用例通过**；联网 **15 个检查通过**，含已有搜索、分页与正文读取。年度快照回放覆盖2025年下半年213个日期批次、658条文章，以及2026年归档264个日期批次、1,569条文章，合计 **477个批次、2,227条文章**。这是两份年度快照的数据，不包含近期页面的额外批次，不是477次独立联网请求，也不证明其他账号或未来页面格式。

此外，直接运行重构脚本的真实日期结果如下：

| 查询日期 | 结果 | 原条目数 |
| --- | --- | ---: |
| 2026-10-14 | 近期页面 `ok` | 6 |
| 2026-09-30 | 当年归档 `ok` | 8 |
| 2025-06-01 | 支持起点、跨年归档 `ok` | 1 |
| 2025-12-31 | 2025年归档 `ok` | 6 |
| 2026-01-01 | 2026年归档 `ok` | 5 |
| 2026-10-15、2026-10-01 | `date_batch_not_present`，列出已检查来源 | 0 |

来源本次未列出10月1日，并非脚本能补齐的连续日历。对外承诺是“读取支持起点之后、页面实际列出的更新日期”，不是每个日历日一定有内容。仍未重新执行完整安装与首次授权的 Agent 流程。

同日将新脚本放入原隔离 Linux 容器的临时目录，以官方 CLI 1.0.97 和已有 `waytoagi` 命名配置执行2025-06-01、2026-10-14，两次分别取得1条、6条，均为 `status=ok`。没有覆盖容器已安装的 Skill，也没有重新授权；这补充了 Linux 与命名配置下的真实多页读取证据，不是新版首次安装验收。
