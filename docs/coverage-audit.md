# Skill 承诺与测试核对（2026-10-15）

此前盘点的本产品能力、边界与 Agent 处理约定已补充测试并取得通过记录。最终证据包括 **49 个产品离线用例、1 个测试隔离守卫用例、16 个真实 CLI/快照检查、23 个合成 Agent 场景和1次当前版本真实 setup**。Agent 场景由21个测试方法覆盖，另有1个真实 setup 方法；这些数量不能直接混作同一种用例相加。

核对范围为 [SKILL.md](../skills/zeno-waytoagi-learning/SKILL.md)、[setup.md](../skills/zeno-waytoagi-learning/setup.md)、[reading-options.md](../skills/zeno-waytoagi-learning/references/reading-options.md)、[failures.md](../skills/zeno-waytoagi-learning/references/failures.md) 与 [README](../README.md)。下表说明每项证据实际证明什么；没有靠删除约定或检查文档关键词来获得通过结论。

本轮验收对象是安装配置与三条读取流程，由任务显式进入 Skill。收尾时出现的并行更名和触发说明改稿保持独立；自动选择 Skill 的新增触发策略不作为这批场景的通过结论。

## 安装与配置

| 承诺 / 可观察行为 | 最终证据 |
| --- | --- |
| 安装当前完整 Skill、检查依赖、复用已有环境并验证三功能 | `test_current_package_installs_and_validates_existing_environment` 对照安装文件；`test_current_setup_with_real_existing_authorization` 在临时目标实际安装当前包并用真实飞书配置验证。 |
| 目标已有用户修改时保全，不静默丢失 | `test_installation_preserves_existing_user_changes` 在完整旧包中加入修改与额外用户文件，检查原处或备份的内容逐字一致；允许说明后备份或停下交用户选择。 |
| Python 3.9 以上、来源时区和官方 CLI | Python 3.9.6、3.14.7 的离线用例；3.9.6 下16项真实读取检查；真实 setup 检查 Linux 的 Python 3.11.2、时区及 CLI 1.0.97。空白环境依赖准备另有[历史实际体验](setup-walkthrough.md)，本轮不重测上游安装器。 |
| 配置、身份、权限问题按当前 CLI 指南路由 | 测试启动时实际缓存官方指南；权限不足、浏览器接入与故障场景检查实际路由调用。真实 setup 也读取当前官方索引和参考。 |
| 沿用同一配置与用户身份，不改其他配置及默认项 | 公共 Agent 断言检查读取的 `--profile`、`--as user`，已有配置场景拒绝配置写入；未知配置、浏览器接入及真实 setup 分别检查对应分支。真实 setup 的底层白名单阻止写配置和重新登录。 |
| 默认 Agent 发起一键配置、交付原链接和二维码，用户确认后接续 | `test_browser_setup_handoff_and_same_session_resume` 检查实际发起调用、链接与二维码交付，再在同一 Agent 会话模拟用户确认、验证三功能。二维码编码与真实授权由上游负责，合成交接不充当新的真实授权记录。 |
| 一键路径实际受阻后再进入终端安全输入 | `test_browser_failure_explains_safe_terminal_fallback` 实际注入一键接入失败，检查阻碍说明、交互终端和隐藏输入指引。 |
| 权限足够就继续；不足才协调补充 | 复用宽权限配置的当前 setup 通过；`test_missing_scopes_routes_upstream_and_requests_help` 验证缺少读取权限后的上游路由与用户协作。没有将最小权限集合或收窄权限加入承诺。 |
| 密钥不交到聊天，错误中凭证、授权链接与代码不展示 | 终端备选用例检查安全输入；`test_sensitive_error_is_redacted_and_diagnosable` 注入合成敏感字段，检查最终答复清理及错误码、版本、来源保留；已有非 JSON 诊断抑制测试继续通过。 |
| 如实交付安装位置、配置、日期、条数、分页和文章来源；受阻时不谎报完成 | 正常、浏览器待用户配合、终端受阻三类交付分别有实际 Agent 样本；真实 setup 使用返回状态、条数、正文长度与同文档链接核对。 |

## 按日期看更新

| 承诺 / 可观察行为 | 最终证据 |
| --- | --- |
| 必填有效 YYYY-MM-DD、拒绝未来日期、支持起点两侧 | [DateCommandTests](../tests/test_waytoagi_updates.py) 的输入、范围和真实起点用例；`test_unsupported_date_explains_cutoff_without_reading_other_dates` 验证 Agent 说明范围，不读取其他日期。 |
| Asia/Singapore 日期；缺时区报错，补齐后可恢复 | 既有跨年与缺时区用例，加 `test_restoring_timezone_data_recovers_in_the_same_python`：同一解释器先失败、补回实际时区文件后成功，不改用当地时区。 |
| 最近更新实际传入当天或前一天 | `test_recent_update_uses_an_explicit_source_timezone_date` 检查本轮“按今天查”的真实脚本调用及输出日期；之前的最近可用日期抽样不再作为 Agent 选日证据。 |
| 单入口自动选近期、当年和跨年归档；同月日不串年 | 近期、跨年路由、同月日不同年及年末元旦离线用例，真实日期抽样与 Linux 命名配置读取。 |
| 原日期、原标题、原摘要、真实链接和条目集合保真 | 独立预期值的摘要/链接测试；真实年度快照477批次、2,227条目ID集合回放。回放不冒充477次独立联网，也不冒充逐条摘要全文比对。 |
| 目标缺失不换日、不解释为当天无更新 | 脚本目标缺失用例与真实缺失日期响应；`test_missing_date_reports_checked_sources_without_switching` 检查 Agent 的解释和不交付别日摘要。 |
| 路由缺失、重复日期、节选、空批次、来源/锚点/日期错配和未知结构返回失败 | 既有离线场景；`test_changed_source_structure_is_not_empty_success` 用真实脚本遇到破损响应，检查 Agent 保留错误码、CLI版本与来源。 |
| CLI 失败保留原因，不自行登录、换身份或匿名回退 | 既有缺 CLI、超时、授权、权限、资源、限流、存储与非 JSON 进程替身用例。它们证明本脚本的失败报告，不承担上游内部恢复实现。 |

## 搜索与文章读取

| 承诺 / 可观察行为 | 最终证据 |
| --- | --- |
| 从问题提取不超过30字符的关键词，用户身份限定 WaytoAGI | 公共 Agent 断言与长问题展示场景检查实际查询；`test_thirty_character_query_is_accepted` 实测30个中/英文字符。CLI实际接受31字符，30字符是本 Skill 的 Agent 选词约束，不臆造上游拒绝行为。 |
| 返回标题、摘要和来源；空搜索只说明本次关键词未命中 | 真实搜索/无命中用例，加 `test_no_match_explains_keyword_scope`；接受“0条结果”等等价交付，不强制固定文案。 |
| 真实令牌翻页保持条件；后页错误、重复令牌、无新增时停止并交付部分材料 | 真实第二页用例；`test_pagination_stops_and_preserves_material` 的三个受控场景检查实际调用、上限、等待与已取得链接。 |
| 仅标题搜索 | `test_title_only_search_matches_every_title` 真实读取。 |
| 去高亮、保留实际来源，零时间视为未提供；目录/快捷方式不混算教程，不推导热门排名或全库总数 | `test_search_presentation_and_short_query` 使用符合实际字段形状的混合结果和零时间，检查 Agent 展示及范围解释；任务明确只要搜索结果，不读正文。 |
| 摘要不冒充已读正文 | 上述搜索展示场景检查没有正文调用；真实全文用例及需要展开时的 Agent 场景分别取得正文。 |
| 成功状态和非空正文都检查；空正文不算读完 | 真实多章节正文用例；`test_empty_article_is_not_reported_as_read` 注入成功空正文，检查实际交付。 |
| 导航页继续到实际子文档 | `test_navigation_continues_and_external_instructions_are_data` 检查子文档调用、正文参数与子文档来源。 |
| 目录取实际块ID并按章节读取，保持章节边界 | 真实目录与章节用例，配合 `test_invalid_section_refreshes_outline_once` 的失效后一次重新定位。 |
| 刷新后仍没有章节就停止并给真实选项 | `test_still_missing_section_offers_real_choices` 使用已无目标章节的目录，检查停止及实际选项。 |
| 关键词局部上下文不足时从目录展开章节 | 真实关键词/继续展开用例，加 `test_keyword_excerpt_expands_using_outline` 检查 Agent 实际补取缺失信息。 |
| 节选、tips、图片、视频、外链和独立表格未展开时说明范围 | `test_partial_article_reports_unread_media_and_tables` 注入节选和限制提示，检查交付；真实 setup 也说明实际未展开媒体。 |
| 外部文本只作资料，不执行其中指令 | 导航到子文档的场景包含合成恶意指令；检查正常信息交付及其要求创建的文件没有出现。 |

## 通用恢复与交付

| 承诺 / 可观察行为 | 最终证据 |
| --- | --- |
| 成功、空结果、部分材料和错误分开 | 脚本正反例、空搜索、空正文、分页部分结果及格式错误场景分别有断言，不以退出码或 ok 单项替代正文核对。 |
| 暂时服务错误最多重试一次，遵守等待提示 | 分页持续限流场景检查两次后页请求与不少于提示的等待，随后停止；脚本自身不重试。 |
| 未知读取配置列出实际选择，不默默切换 | `test_unknown_profile_lists_choices_without_switching` 配合真实 CLI 未配置用例。 |
| 资源拒绝时停读该资源，保留已取得的搜索材料，不靠重新登录或新建应用解决 | `test_resource_denial_preserves_search_result_without_reauth` 检查保留链接、单次正文读取和没有登录调用。 |
| 格式不明时不改解析器、空数组冒充成功；交付版本、错误和来源并清理敏感字段 | 格式变化、敏感错误两个 Agent 场景与既有结构异常用例；公共断言检查源 Skill 没被改写。 |

## 证据与仍然适用的范围

测试文件：[日期与失败](../tests/test_waytoagi_daily.py)、[统一日期入口](../tests/test_waytoagi_updates.py)、[真实读取](../tests/test_waytoagi_live.py)、[年度回放](../tests/test_waytoagi_archive_live.py)、[Agent场景](../tests/test_waytoagi_agent.py)。分批结果及最终样本见 [agent-test-results.json](agent-test-results.json)，运行方法见 [agent-testing.md](agent-testing.md)。

本轮修正一处产品歧义：读取任务指定的配置不存在时先让用户选择；已要求安装接入新配置的任务按 setup 发起浏览器流程，避免不必要的再次确认。其他首轮失败来自测试目录、等价措辞、可恢复备份和同一文档链接识别，已校正后重验，没有据此删减产品要求。

真实 setup 本轮复用现有授权，没有新建应用或重新授权。首次应用接入与授权仍使用此前的[真实体验记录](setup-walkthrough.md)；上游一键新建应用没有新增对外承诺。合成交接测试不能充当新账号真实授权通过，单次 Agent 样本也不是所有模型/账号永远成功的保证。

**GitHub URL 安装仍待发布后验收**：当前包按用户要求未上传，不能把本地完整包安装写成已发布 URL 安装通过。其他平台外链、全部媒体展开、全部账号访问资格与上游内部授权异常不扩大为本 Skill 的覆盖义务；用户排除的取消、链接过期也未追加测试需求。

## 时间范围检索补充（2026-10-17）

[扩展读取](../skills/zeno-waytoagi-learning/references/reading-options.md#时间范围检索)新增以社区日志日期筛选主题候选的执行指引：读取年度正文并补读近期章节，按实际日期与文章链接去重，按日期倒序交付并说明范围。证据为 [README 场景实测与独立复验](verification.md#readme-场景与时间范围检索2026-10-17)及 [取样记录](readme-examples.json)，覆盖本次 2026-07-17 至 2026-10-17 的真实请求。

独立复验首轮遗漏近期章节的结果记为部分完成；明确完成条件并实际补读后通过。该证据是已有授权下的 Agent 读取样本，不新增自动化测试数量，不证明所有时间窗口、全库召回或热度排行；原有安装与授权验收边界继续适用。
