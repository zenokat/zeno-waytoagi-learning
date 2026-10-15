# Skill 承诺与测试核对（2026-10-15）

结论：**三个功能的可执行读取路径已有通过证据，但“Skill 涉及的所有承诺均已测试”不成立。** setup 新版流程、部分结果处理与恢复交互仍有缺口。用例数量不能替代逐项覆盖。

本次核对本地 `cd63793` 的 [SKILL.md](../skills/zeno-waytoagi/SKILL.md)、[setup.md](../skills/zeno-waytoagi/setup.md)、[reading-options.md](../skills/zeno-waytoagi/references/reading-options.md)、[failures.md](../skills/zeno-waytoagi/references/failures.md) 及 [README](../README.md)。这是测试证据盘点，没有改变已确认的产品需求，也没有将未测的约定删除以获得通过结论。

“已有证据”只对表中检查的行为及样本有效；“部分”表示底层命令或旧版流程通过，但尚不能证明当前 Agent 的完整行为；“缺口”表示没有对应行为测试。静态审查、命令帮助和文档存在不算行为测试。

## 安装与配置

历史体验见 [setup-walkthrough.md](setup-walkthrough.md)。它使用旧版本地包，不能充当当前包完整验收。

| 承诺 / 可观察行为 | 证据与结论 |
| --- | --- |
| Agent 取得完整 Skill 包并安装到自身目录 | 部分：旧版本在空白 Linux 环境实际安装并核对副本；当前版本未重新从 README 入口走通。GitHub 当前包尚未发布，URL 安装未验收。 |
| 保全安装目标已有的用户修改 | 缺口：没有目标目录已有修改的安装场景。 |
| 准备 Python、来源时区与官方 CLI | 部分：实际准备 Python 3.11、时区、CLI 1.0.97；Mac 实际读取使用 CLI 1.0.96。声明的最低 Python 3.9 尚无实际运行记录。 |
| 配置、身份与权限问题按 CLI 自带指南路由 | 部分：实际读取 `lark-cli skills read lark-shared` 的索引；尚未验证新版 Agent 遇到故障后确实沿该索引恢复。CLI 内部流程由上游负责，无需本项目重复覆盖。 |
| 优先复用可用配置、授权，沿用同一配置与用户身份 | 部分：代码与命名配置的实际读取通过；尚无当前 setup 中“已有环境直接复用”的完整 Agent 场景。 |
| 保留其他配置及全局默认项 | 缺口：没有带其他配置的 setup 前后状态对照。读取测试不修改配置，不能替代这项验证。 |
| Agent 发起一键配置，转交官方浏览器链接并在用户完成后接续 | 部分：用户实际通过终端发起一键配置并在浏览器选择应用，后续 Agent 接续授权成功；新版要求的 Agent 主动发起应用接入尚未完整重跑。 |
| 一键配置实际受阻时再进入终端或安全输入备选 | 缺口：未验证以具体阻碍触发该备选的场景。 |
| 密钥安全输入、凭证及临时代码不进入聊天、Skill 或 Git | 部分：历史正常路径未要求用户发送密钥，敏感值未纳入仓库；没有专门的敏感响应场景验证。 |
| 只申请所需读取权限，权限足够即继续，不足时协调用户 | 部分：历史授权显式请求两项读取权限且宽权限下三功能成功；不足权限仅测试脚本报告，尚未测试 Agent 协调补充的过程。不要求额外定位或收窄已有宽权限。 |
| 资源访问资格问题不靠反复登录、新建应用处理 | 部分：脚本收到资源拒绝会停止；Agent 接续行为未测。 |
| setup 实际验证三功能并如实交付位置、配置、日期、条数、文章来源 | 部分：历史完整主流程有记录；当前日期接口改版后的完整 Agent setup 与受阻时的交付尚未重跑。 |

## 按日期看更新

以下用例位于 [test_waytoagi_updates.py](../tests/test_waytoagi_updates.py)、[test_waytoagi_daily.py](../tests/test_waytoagi_daily.py)；真实调用位于 [test_waytoagi_live.py](../tests/test_waytoagi_live.py)，年度快照回放位于 [test_waytoagi_archive_live.py](../tests/test_waytoagi_archive_live.py)。

| 承诺 / 可观察行为 | 证据与结论 |
| --- | --- |
| 必填有效 `YYYY-MM-DD`，不接受未来日期 | 已有证据：`test_date_is_required_before_any_cli_request`、`test_invalid_or_non_iso_dates_fail_without_reading`、`test_future_date_is_rejected_before_reading`。 |
| 使用 Asia/Singapore，缺时区不擅自替代 | 已有证据：`test_year_rollover_uses_singapore_date`、`test_missing_timezone_data_returns_json_without_cli`。补齐数据的实际恢复尚无用例。 |
| 从 2025-06-01 起支持，早于起点返回范围状态 | 已有证据：`test_dates_before_supported_start_do_not_read_any_page` 及起点真实读取。 |
| 近期、当年与其他年份归档统一自动定位 | 已有证据：近期命中、年度归档、年份路由、同月日跨年、年末元旦的离线用例及真实日期调用；Linux 命名配置亦实际读取近期和跨年归档。 |
| 保留原日期、标题、摘要与实际链接 | 已有证据：`test_retains_summary_and_only_requested_day`、`test_date_query_follows_year_route_and_preserves_original_entry` 等独立预期值检查，配合真实样本验证。 |
| 不遗漏或混入其他批次条目 | 已有证据：实际年度快照 477 批次、2,227 条目的 ID 集合回放；不是 477 次独立联网，也不是每条摘要逐字比对。原摘要保真由独立样本测试补充。 |
| 日期缺失不自动换日、不冒充无更新 | 已有证据：`test_missing_date_does_not_substitute_another_batch` 及实际缺失日期响应。Agent 面向用户的最终解释未单独测试。 |
| 路由缺失、重复日期、节选、错配、空批次或结构变化返回错误 | 已有证据：`test_missing_year_route_is_a_failure_not_an_empty_date`、`test_duplicate_dates_do_not_return_an_arbitrary_batch`、`test_invalid_archive_scope_source_or_content_is_not_success` 等。 |
| CLI 失败保留原因，不自动登录、换身份或匿名回退 | 已有证据：缺 CLI、超时、权限、授权、限流、凭证存储、非 JSON 等进程替身用例；这验证脚本报告，不验证上游真实故障恢复。 |
| Agent 获取最近更新时选择当天或前一天 | 部分：脚本显式日期调用通过；Agent 选日行为未独立测试。现有 `latest()` 测试从来源挑选实际最近日期，不能替代该交互约定。 |

## 搜索知识库

下表的已有命令证据来自 [WaytoagiLiveTests](../tests/test_waytoagi_live.py)。

| 承诺 / 可观察行为 | 证据与结论 |
| --- | --- |
| 用户身份、固定知识库，返回标题、摘要字段及实际链接 | 已有证据：`test_search_returns_waytoagi_links_and_matching_context`。 |
| Agent 从问题提取关键词，控制最多 30 字符 | 缺口：未验证 Agent 的关键词选择，也没有 30/31 字符边界用例。 |
| 空搜索与错误分开 | 部分：`test_no_search_match_is_success_with_empty_results` 验证实际成功空结果；Agent 的解释及按需换词未测。 |
| 沿实际令牌翻页并保持查询范围，取得新增结果 | 已有证据：`test_search_pagination_returns_new_same_space_results` 验证实际第二页，不能推及整库召回。 |
| 后续页失败、重复令牌或无新增结果时停止并交付部分材料 | 缺口：没有这些受控响应下的 Agent 行为测试。 |
| 仅标题搜索 | 已有证据：`test_title_only_search_matches_every_title`。 |
| 展示时去高亮、保留 URL；时间 0 视为未提供 | 缺口：测试检查过原始字段并在断言中去标签，但这不能证明 Agent 实际展示处理。 |
| 不将目录、快捷方式混算为教程总量，不据搜索推导热门排行；摘要不冒充已读正文 | 缺口：没有混合结果及用户要求排行、总数时的 Agent 场景。 |

## 文章与局部正文

| 承诺 / 可观察行为 | 证据与结论 |
| --- | --- |
| 读取实际文章正文，检查成功状态、非空内容并保留来源 | 部分：`test_full_article_contains_multiple_sections_and_body` 验证真实教程跨章节正文；Agent 对空正文的拒绝及最终来源展示未独立测试。 |
| 导航页只有子文档引用时，继续读取相关文章 | 缺口：没有导航页到子文档的完整行为用例。 |
| 获取目录和实际块 ID，再按章节读取 | 已有证据：`test_outline_returns_heading_ids`、`test_section_returns_body_and_stops_before_next_peer` 验证章节内容和边界。 |
| 关键词命中局部上下文，不足时从目录继续展开 | 已有证据：`test_keyword_returns_matching_local_context`、`test_keyword_context_can_expand_via_outline_section` 验证命令组合；未单独验证 Agent 自行判断上下文是否足够。 |
| 节选、tips、图片、视频、外链及独立表格未读时说明范围 | 部分：历史 setup 交付说明未展开媒体；日期脚本拒绝不完整内容。一般文章的截断、tips 和表格等分支下的 Agent 说明未测。测试拒绝 tips 不等于验证 Agent 会正确解释 tips。 |
| 章节 ID 失效后重读目录一次，仍失败则给实际章节选项 | 部分：`test_missing_section_id_is_rejected` 只验证 CLI 拒绝失效 ID；未验证重新定位与停止交付。 |
| 外部文本只作资料，不执行其中指令 | 缺口：没有含指令文本的受控材料验收。 |

## 通用交付与失败约定

| 承诺 / 可观察行为 | 证据与结论 |
| --- | --- |
| 仅退出码 0 且 status/ok 成功才算成功 | 脚本已有离线正反例；直接 CLI 读取由联网用例检查成功。Agent 面对失败响应不误报成功的行为未全面验证。 |
| 临时网络、限流或服务错误最多重试一次，遵守服务等待提示 | 缺口：脚本超时或限流报告通过，但不实施重试；Agent 重试次数、等待及停止未测。 |
| 指定配置不存在时列出现有配置供确认，不静默切换 | 部分：`test_unknown_profile_identifies_configuration_gap` 验证真实 CLI 错误；列举与确认行为未测。 |
| 资源拒绝、失效链接或结构变化时停止该资源，交付已有材料 | 部分：日期脚本停止及错误报告有用例；搜索、文章及 Agent 保留部分材料的完整交付未测。 |
| 错误保留代码、版本及来源，展示前去除凭证、授权链接和临时代码 | 部分：脚本保留错误原因、抑制非 JSON 原始诊断有用例；结构化错误中的敏感值去除、CLI 版本收集及最终展示没有 Agent 场景覆盖。 |

其他平台外链的读取、全部媒体展开、上游 CLI 内部配置/授权异常、所有账号访问资格都不属于本 Skill 的已承诺读取能力，不将它们扩大为本次测试任务。用户明确排除的取消和授权链接过期也不新增覆盖要求。

## 验收判断

读取命令的正常路径有实测；日期脚本的主要异常与边界有离线测试。**完整 Skill 产品的承诺覆盖尚未闭环**，缺口集中于当前 setup 与 Agent 按文档执行的结果处理、恢复和交付行为。

补齐时应通过“给 Agent 任务及可控 CLI 响应，观察调用顺序与最终交付”验证这些行为；仅搜索文档有没有某句话，或增加一个读取模拟 JSON 的测试，不能证明 Skill 会按约定运行。真实授权仍由用户配合；无需为此自动重建应用或撤销已有授权。

本次复跑结果与历史测试边界统一记录在 [verification.md](verification.md#本轮完整承诺核对2026-10-15)。
