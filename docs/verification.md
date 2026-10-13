# 读取功能验收

Skill 中的可执行读取路径必须有对应的用例并实际通过。CLI 帮助、文档格式和链接检查不能替代行为验证。新增参数组合应先补用例，验证实际内容与范围，再写入 Skill。

## 功能与用例

| SKILL.md / reading-options.md 的能力 | 用例与检查内容 |
| --- | --- |
| 最近可用更新 | 离线测试验证日期选择、原标题、原摘要、引用链接；联网 `test_latest_update_has_original_material_and_actual_date` 验证真实批次、条目和链接。 |
| 指定日期 | 离线 `test_retains_summary_and_only_requested_day` 等；联网 `test_requested_date_returns_same_batch` 验证指定真实日期取得同批次原条目。 |
| 日期未出现、窗口之外及读取失败 | 离线测试验证独立状态、空条目、结构变化、节选、缺引用和授权失败，避免误报无更新。 |
| 知识库搜索 | 联网 `test_search_returns_waytoagi_links_and_matching_context` 检查关键词命中、标题、摘要字段及知识库 URL。 |
| 翻页 | 联网 `test_search_pagination_returns_new_same_space_results` 用真实令牌取得新增结果并保持同一知识库。 |
| 仅查标题 | 联网 `test_title_only_search_matches_every_title` 检查每个返回标题实际命中。 |
| 全文与目录 | 联网 `test_full_article_contains_multiple_sections_and_body`、`test_outline_returns_heading_ids` 检查跨章节正文、范围和实际块 ID。 |
| 按章节读取 | 联网 `test_section_returns_body_and_stops_before_next_peer` 检查该节正文和同级标题边界。 |
| 关键词上下文及继续展开 | 联网 `test_keyword_returns_matching_local_context`、`test_keyword_context_can_expand_via_outline_section` 检查局部标记、实际命中及从目录定位章节后的继续读取。 |
| 较早更新 | 联网 `test_historical_update_page_returns_older_dated_entries` 定位当前窗口之前的日期，读取该日原摘要和文档引用。 |
| 命名配置转发 | 离线测试覆盖每日命令及两次底层请求；整组联网用例可携带同一 `WAYTOAGI_PROFILE` 复验真实配置。 |
| 环境与 CLI 失败 | 离线 `DailyFailureTests` 覆盖缺 CLI、超时、授权/权限/资源/限流/凭证存储错误和非 JSON 响应；缺时区库用真实独立进程复现并验证错误 JSON。 |
| 无命中与不合法读取目标 | 联网 `test_no_search_match_is_success_with_empty_results`、`test_unknown_profile_identifies_configuration_gap`、`test_missing_section_id_is_rejected` 区分空搜索、未配置和失效章节错误。 |

离线用例见 [test_waytoagi_daily.py](../tests/test_waytoagi_daily.py)，联网用例见 [test_waytoagi_live.py](../tests/test_waytoagi_live.py)。

## 运行方式

从仓库根目录运行离线测试：

```bash
python3 -m unittest discover -s tests -v
```

默认执行 33 个离线用例，并明确跳过 14 个联网用例。跳过不等于联网验收通过。

在可访问系统钥匙串、已有有效飞书授权的环境中，单独运行联网验收：

```bash
WAYTOAGI_LIVE=1 python3 -m unittest discover -s tests -p test_waytoagi_live.py -v
```

需要指定已有配置时，同一命令再设置 `WAYTOAGI_PROFILE=<配置名>`。测试只读，不登录、不创建应用、不保存响应正文或凭证；没有可用账号、网络失败或来源变化都会报失败，需要核对后重验。

## 本次结果与边界

2026-10-12，官方 CLI 1.0.96、已有飞书应用及用户授权：28 个离线用例通过，11 个联网用例通过；显式指定现有配置的整组读取也通过。

2026-10-13，官方 CLI 1.0.96 补充异常验收：缺少时区数据时原脚本在导入阶段崩溃，现已改为返回失败 JSON 与补齐 `tzdata` 的提示；缺 CLI 和超时增加明确原因。33 个离线用例、14 个联网用例均通过，含无命中、未配置及失效章节的真实响应。

创建时间筛选暂未纳入 Skill。实际请求接受时间参数，但搜索结果的创建时间均为 0，无法逐项核对日期窗口是否正确。待取得可检查的真实时间数据及对应范围用例后再加入。

测试证明这里列出的读取路径及样本结果；不保证所有文档、账号和日期都可访问，也不验证其他平台外链或未展开媒体。[失败处理](../skills/zeno-waytoagi/references/failures.md)中的有界重试、用户授权接续和部分结果交付是 Agent 执行约定，不是脚本自动恢复能力，尚未完成实际用户交互验收。普通用户首次安装、应用配置、首次授权和跨租户资料访问仍需单独验收，不能仅凭本机与模拟失败测试宣称这些路径已通过。
