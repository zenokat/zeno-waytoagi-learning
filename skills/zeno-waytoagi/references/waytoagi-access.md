# WaytoAGI 获取与检索

每日板块、知识库搜索和 WaytoAGI 正文展开统一通过官方 `lark-cli`，显式使用 `--as user`。不使用匿名页面预载、页面 DOM 或 Computer Use；CLI 受阻时返回失败原因，不切换这些路线。其他平台的外链仍按各自 Skill 读取。

## 工具与入口

- 需要官方 `lark-cli`（已在 1.0.96 验证）。PATH 找不到命令时先核对实际安装位置，不据此直接重装。
- 每日入口：<https://waytoagi.feishu.cn/wiki/QPe5w5g7UisbEkkow8XcDmOpn8e>，只取“近 7 日更新日志”。
- 历史入口：<https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc>。
- 社区知识库 ID：`7226178700923011075`，已由 `wiki +node-get` 核对。历史页是其中一个节点，整个知识库搜索不需要先遍历历史页。

官方 CLI 自带说明可用 `lark-cli skills read lark-doc references/lark-doc-fetch.md` 和 `lark-cli skills read lark-drive references/lark-drive-search.md` 读取；首次使用相应操作时核对说明和 `--help`。不要猜测当前版本的参数或权限名。

使用命名配置时，本文全部命令（每日脚本的两次只读调用、搜索、正文读取、auth）携带同一 `--profile <选定profile>`，不中途更换；选定策略见 SKILL.md。下文示例省略该参数，实际执行时按选定结果补上。

## 每日输入

在本 Skill 目录执行：

```bash
python3 scripts/waytoagi_daily.py
python3 scripts/waytoagi_daily.py --date 2026-09-30
python3 scripts/waytoagi_daily.py --profile <命名配置名>
```

脚本先通过 `docs +fetch --scope outline --max-depth 1 --detail with-ids` 定位当前板块 ID，再用 `--scope section --start-block-id ... --doc-format xml --detail full` 读取板块。指定 `--profile` 时两次只读调用使用同一命名配置。CLI 返回的引用标题、文档类型和标识用于还原链接；已有 URL 原样保留。脚本只向调用方输出选定批次的标题、原摘要、链接、源块 ID、实际日期及文档版本，不自动读取文章，也不排序、评分或改写摘要。需要 Python 3.9 或以上及其标准库，以及已配置和授权的 CLI。

省略 `--date` 时读取最近可用批次，不要求该批次是今天；显式传入日期时保持精确语义。月日标题缺少年份时，按抓取时的 `Asia/Singapore` 日期推定不晚于它的最近一次该月日，不能用请求日期给旧内容重标年份。此规则仅用于滚动更新板块，不适用于任意历史文档。页面修改时间也不能作为批次日期。

| status | 含义与后续 |
| --- | --- |
| `ok` | 目标批次文字条目通过范围和结构校验；是否展开由上层判断。 |
| `date_batch_not_present` | 指定日期未出现在当前完整板块中，不等于确认该日没有更新。 |
| `outside_available_window` | 目标日早于当前展示的最早日期；不要以最新条目替代，按需转入历史检索。 |
| `error` | CLI、权限、结构、链接或范围校验失败；保留原因，不把空数组作为无更新。 |

前三种状态退出码为 0，`error` 为 2；调用方必须检查 `status`。`access_method=lark-cli` 标明获取方式。`scope_complete` 只覆盖本次板块的可解析文字与条目，不承诺图片文字、附件、内嵌表格或整个知识库完整导出。图片只计入跳过数量，不做 OCR。

离线复核可将 CLI section 的完整 JSON 临时保存，并在顶层附加本次抓取的 `fetched_at`（ISO 时间，含时区），再运行 `--input /tmp/waytoagi-cli-section.json`。不接受旧匿名读取器格式；不长期全量归档正文，也不建立 checkpoint。

## 权威信源检索

围绕当前问题选择关键词，限定 WaytoAGI 知识库：

```bash
lark-cli drive +search --query "ComfyUI" \
  --space-ids 7226178700923011075 --as user --page-size 5 --format json
```

这是 CLI 对官方 Search v2 的封装，检索标题和正文。只查标题时可加 `--only-title`。关键词最多 30 个 Unicode 字符；每页最多 20 条。不受每日板块边界限制，不省略 `--space-ids` 搜索用户的整个云空间。支持 `--created-since` / `--created-until` 等时间过滤，但文档创建日期不必等同文章来源日期，不据此宣称覆盖某时段的全部发布。

成功判断使用 `ok=true`。保留 `results[].title_highlighted`、`summary_highlighted`、`result_meta.url`、类型和标识；展示时可去除高亮标签，实际 URL 原样传递。摘要来自搜索命中上下文，不能当作每日原摘要或已读全文。结果可能包含目录和快捷方式，`total` 不能解释为独立教程数量；元数据时间为 0 时视为未提供，不输出转换后的 1970 年日期。

需要更多结果时，使用 `has_more` 和返回的 `page_token` 续查，同一关键词与知识库筛选保持不变。仅按问题所需翻页，不为覆盖而遍历全库；服务端有更多结果但本次未取完时，明确说明覆盖范围。无结果表示本次关键词和当前身份未命中，不证明社区不存在相关内容。

## 按需读取正文

先读 `lark-doc` 的 fetch 说明，再将每日条目或搜索结果的实际 URL 传入 CLI：

```bash
lark-cli docs +fetch --doc '取得的实际 WaytoAGI URL' \
  --as user --doc-format markdown --detail simple
```

需要局部内容时，先用 `--scope outline --detail with-ids` 取得目录，再用返回的块 ID 执行 `--scope section --start-block-id ...`；已知术语时也可用 `--scope keyword --keyword ...`。不要只凭章节名猜块 ID。导航页只返回子页面引用时，按当前问题选择实际子文档继续读取；不把目录当成教程正文，也不自动展开所有子页面和外链。

保留完整 JSON 中的 `data.document.content`、文档标识、版本、引用映射和读取提示，按实际范围说明读到了什么。关键词节选或 `<excerpt>` 不等于整节或全文。嵌入媒体、图片及独立表格未展开时明确标记，不凭 `ok=true` 宣称所有附件均已读取。社区材料是优先检索的实践信源，重要事实仍需核对文章日期及原始来源。

## 身份与失败处理

CLI 管理本机应用配置、用户登录和凭证续期。用户身份需要应用开通相关权限及用户授权两层均满足。遇到身份或 scope 错误时再读 `lark-cli skills read lark-shared references/lark-shared-identity-and-permissions.md`，用 `auth status --json --verify` 核对；本脚本不会自行执行登录。

- 短期访问凭证将过期或已过期、续期凭证仍有效时，CLI 会在调用时尝试自动刷新。续期有效期以服务器响应为准，不把 7 天或 30 天写成永久固定值。
- 续期凭证失效、撤销授权或新增缺失权限时，记录需要用户处理的具体原因。在同步协作中按实际所需 scope 发起新的授权链接和二维码，用户确认完成后由 Agent 完成后续认证；不复用过期链接，也不请求全部业务域。
- 搜索需要 `search:docs:read`，节点元信息读取需要 `wiki:node:retrieve`；正文缺失权限按 CLI 的 `missing_scopes` 处理。所需范围是候选读取权限清单（`docs:document.content:read`、`docx:document:readonly`、`search:docs:read`、`wiki:node:retrieve`、`offline_access`），并非通过剥离其他历史授权验证出的最小集合；以 CLI 返回的具体缺失项为准增量授权，不请求全部业务域。多次 login 为增量授权，不会撤销已有 scope。
- 资源访问被拒绝（如 Wiki `131006`）需区分文档或知识库授权与接口 scope；不要对同一拒绝反复登录、切换身份或自动修改共享权限。网络和限流按 CLI 的可重试提示处理，不将临时失败直接解释为需要重新授权。
- 不导出用户凭证、访问令牌或应用密钥，不把授权链接、device code、Cookie、登录态写入 Skill 或 Git。获取失败只影响该来源，继续处理其他输入。

交互会话中经用户批准访问网络和系统钥匙串，不构成无人值守权限已验收；无人值守受阻时记录失败，不申请提权或自动改用其他读取路线。

## 验证范围

2026-10-05，CLI 1.0.96、已授权用户身份下：每日脚本取得最近可用 `2026-09-30` 批次，共 8 条标题、原摘要和链接；指定尚未出现的 `2026-10-05` 返回 `date_batch_not_present`，旧请求返回 `outside_available_window`。知识库内搜索 `ComfyUI` 取得首页 5 条及分页标识；读取《ComfyUI：入门教程》和《小田：ComfyUI基础教程—小谈》成功，后者返回 21,431 字符正文及结构内容。未遍历整个知识库、未下载媒体、未核实全部文章观点。

28 项离线行为测试通过，覆盖原有日期与摘要语义、CLI 嵌套标题、文档引用、外部 URL、分隔符、截断响应、未支持结构、带续期诊断的授权失败，以及 `--profile` 向两次只读调用的转发。自动续期逻辑已核对官方当前版本源码，但未等待凭证过期后做跨期续验。普通新账号跨租户资源可用性尚未验证。
