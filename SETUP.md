# zeno-waytoagi 安装与配置（交给 Agent 执行）

把这份文档完整交给一个有终端能力的 Agent。Agent 按本文检查环境、安装官方 CLI 与本 Skill、完成飞书应用配置和用户授权，并验证三类读取能力。

## 执行边界

- 只在本机操作：不推送仓库、不发布内容、不创建远端 Issue，不修改用户已有的其他 Skill。
- 已有可用的 CLI 配置和用户授权一律复用；从零配置使用独立命名 profile，不覆盖默认应用和已有凭证。
- 授权按本文列出的实际所需 scope 发起，不请求全部业务域；资源访问被拒绝与缺少 scope 是两类问题，分开处理，失败时不改用匿名抓取。
- device code、授权链接、凭证只存在于当前会话的变量中，不写入文件、不写入 Git、不随消息外发给第三方。

## 第一步：检查环境

```bash
node --version        # 需要 Node 及自带 npx，用于安装官方 CLI
python3 --version     # 需要 3.9 或以上（依赖标准库 zoneinfo；Windows 若报 ZoneInfoNotFoundError，执行 pip install tzdata）
git --version         # 用于获取本仓库；用户提供本地目录时可不需要
lark-cli --version    # 已安装则记录版本；PATH 找不到时先核对实际安装位置，不直接重装
```

完成判据：四项检查的实际结果已记录，缺哪项就在对应步骤处理。

## 第二步：准备官方 lark-cli

已安装（已在 1.0.96 验证）：保留现有版本，不盲目升级，直接进入下一步。

未安装：按官方文档 <https://github.com/larksuite/cli/blob/main/README.zh.md> 执行：

```bash
npx @larksuite/cli@latest install
```

完成后重新执行 `lark-cli --version` 确认命令可用。

## 第三步：获取本仓库

二选一：

- 用户提供本地目录：直接进入下一步，将该目录记为 REPO。
- 从公开仓库获取：`git clone <本仓库公开地址> zeno-waytoagi`，将克隆结果记为 REPO。

## 第四步：安装 Skill

请用户选定一个 Agent 的 Skill 父目录（常见如 `~/.claude/skills`、`~/.codex/skills`，以用户实际使用的 Agent 为准），然后：

```bash
python3 REPO/install.py --target <用户选定的 Skill 父目录>
```

输出与处理：

- `installed`：首次安装完成。
- `already_installed`：目标内容与本仓库一致，安全跳过。
- `TARGET_CONFLICT: ...`：目标已有不同内容，脚本未做任何改动。向用户报告路径，由用户决定备份删除后重装，或明确执行 `--force`（脚本会把原目录重命名为旁边的 `zeno-waytoagi.backup*` 再安装，新旧并存）。
- `SOURCE_INCOMPLETE: ...`：REPO 不是完整仓库，回到第三步。

安装只复制 `skills/zeno-waytoagi` 包内容，不含仓库工程文件、Git 历史或任何凭证。完成判据：`<目标>/zeno-waytoagi/SKILL.md` 存在。

## 第五步：应用配置与用户授权

先查现状：

```bash
lark-cli config show
lark-cli auth status --json --verify
```

`config show` 已有应用且 `auth status` 显示用户身份有效、所需 scope 已具备：跳到第六步直接验证（已有环境复用路径）。

否则按是否保留既有配置选择一条路径，全程把 `<profile>` 替换为实际选定的名字：

- 本机尚无配置：`lark-cli config init --new` 创建默认配置（完成后 `--profile` 可省略）。
- 已有配置但要独立验收：`lark-cli config show --profile zeno-waytoagi` 确认该名字未占用（已占用则复用它或换一个名字），再 `lark-cli config init --new --name zeno-waytoagi`。`--name` 是追加独立 profile，不替换默认配置。
- `config init --new` 会阻塞并引导用户在浏览器中创建应用：在后台运行它，从输出中取出引导链接发给用户，用户完成后命令返回。
- Agent 上下文（OPENCLAW_HOME / HERMES_HOME 已设置）中该命令默认拒绝：优先 `lark-cli config bind` 绑定 Agent 既有应用；仅当用户明确要求独立应用时加 `--force-init`。

应用就绪后发起用户授权。本 Skill 实际所需 scope：`docs:document.content:read`、`docx:document:readonly`、`search:docs:read`、`wiki:node:retrieve`、`offline_access`。

推荐 split-flow（适用于不能持续阻塞等待的会话）：

```bash
lark-cli auth login --profile <profile> \
  --scope "docs:document.content:read docx:document:readonly search:docs:read wiki:node:retrieve offline_access" \
  --no-wait --json
```

从 JSON 输出取 `verification_url` 发给用户（可用 `lark-cli auth qrcode <url>` 生成二维码），`device_code` 只保留在会话变量里，然后结束本轮并明确告知用户：完成授权后回来确认。用户确认后由 Agent 亲自执行：

```bash
lark-cli auth login --profile <profile> --device-code <device_code>
```

备选官方阻塞流程：去掉 `--no-wait --json`，命令阻塞并展示链接直到用户完成授权。

注意：

- 授权命令必须带 `--scope`（或明确的 `--domain`）；不带范围会请求全部业务域，本 Skill 不需要。
- 会话中断或 device code 失效：按相同 scope 重新执行发起命令，生成新链接和新 code，不复用旧的。
- 多次 login 是增量授权，不撤销已有 scope。

## 第六步：验证三类能力

已有环境复用路径省略 `--profile`；独立 profile 路径每条都带 `--profile <profile>`。

1. 每日更新：

```bash
python3 <目标>/zeno-waytoagi/scripts/waytoagi_daily.py --profile <profile>
```

判据：退出码 0，输出 JSON 的 `status` 为 `ok`、`date_batch_not_present` 或 `outside_available_window` 之一且字段语义与 `references/waytoagi-access.md` 的状态表一致。

2. 知识库搜索：

```bash
lark-cli drive +search --query "ComfyUI" --space-ids 7226178700923011075 \
  --as user --page-size 5 --format json --profile <profile>
```

判据：`ok` 为 true。搜索摘要只代表命中上下文，不代表已读正文。

3. 正文读取（URL 取上一步任一结果的 `result_meta.url`）：

```bash
lark-cli docs +fetch --doc '<取得的 URL>' --as user \
  --doc-format markdown --detail simple --profile <profile>
```

判据：`ok` 为 true 且返回 `data.document.content`。

## 失败处理

- 授权或 scope 不足：错误 JSON 中的 `missing_scopes` 列出缺失项，按该 scope 重新走第五步的授权流程（增量，不影响已有授权）。用户身份要求应用开通 scope 和用户授权两层都满足。
- 资源访问被拒绝（如 Wiki 错误 `131006`）：这是文档或知识库层面的授权问题，与接口 scope 不同。向用户说明实际被拒的资源，由用户核对访问资格；不反复登录、不切换身份、不改用匿名页面抓取。
- 网络或限流：按 CLI 输出中的可重试提示处理，不直接解释为需要重新授权。
- 凭证续期：短期凭证过期时 CLI 会自动尝试刷新；续期凭证失效会返回需要重新授权的明确错误，按第五步重新授权。

## 验收边界

- 本流程在 CLI 1.0.96、已完成应用配置和用户授权的环境验证过三类能力；首次应用配置和授权需要用户本人配合完成。
- 普通新账号（跨租户）访问该知识库的条件尚未验证；未亲自跑通第六步前，不宣称新用户全链路可用。
