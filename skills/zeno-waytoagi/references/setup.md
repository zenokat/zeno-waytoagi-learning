# zeno-waytoagi 完整安装与配置指南

本指南由 Agent 执行：检查环境、安装官方 `lark-cli` 与本 Skill、按需完成飞书应用配置与用户授权、验证三类读取能力。仓库根目录 `SETUP.md` 是入口；本文件是唯一完整步骤来源。

## 执行边界

- 只在本机操作：不推送仓库、不发布内容、不创建远端 Issue，不修改用户已有的其他 Skill。
- 已有应用和已有用户授权一律复用；只有应用实际缺失（或用户明确选择其他应用）时才创建新应用，且使用命名 profile，不覆盖默认配置和已有凭证。
- 授权只按实际缺失的具体 scope 增量发起，不请求全部业务域；资源访问被拒绝与缺少 scope 是两类问题，分开处理，失败时不改用匿名抓取。
- device code、授权链接、凭证只存在于当前会话的变量中，不写入文件、不写入 Git、不随消息外发。
- 不执行 `lark-cli profile use` 切换全局活动 profile；全程用 `--profile` 显式指定。

## 路径变量约定

执行任何命令前，先把下列变量替换为真实绝对路径，替换后命令从任意工作目录可用：

- `REPO`：本仓库本地目录（包含 `install.py` 与 `skills/`）。
- `SKILLS_DIR`：当前 Agent Harness 的 Skill 父目录。
- `SKILL_DIR`：安装后的 `SKILLS_DIR/zeno-waytoagi`。
- `PROFILE`：第五步选定的 profile 名。

## 已安装 Skill 的接续

若 `SKILL_DIR/SKILL.md` 已存在（用户此前装过本 Skill），跳过第一至第四步，直接从第五步"应用配置与用户授权"接续；已验证过的环境只复核不复装。

## 第一步：检查环境

```bash
node --version        # 仅在需要安装官方 CLI 时才需要（CLI 已安装则跳过本项）
python3 --version     # 需要 3.9 或以上（仅依赖标准库 zoneinfo）
git --version         # 仅在需要克隆仓库时才需要（用户提供本地目录则跳过本项）
lark-cli --version    # 已安装则记录版本；PATH 找不到时先核对实际安装位置，不直接重装
```

本机已满足的项直接使用，无需安装。缺失项由 Agent 按当前操作系统与已有官方包管理器给出安装命令，并以官方入口核对（Node：<https://nodejs.org/>；Python：<https://python.org/>；Git：<https://git-scm.com/>）。例如 macOS 有 Homebrew 时对应 `brew install node`、`brew install python@3.13`、`brew install git`。需要管理员权限或系统级确认的步骤，把具体命令交给用户执行并等待确认，Agent 不擅自提权。Windows 上若每日脚本报 `ZoneInfoNotFoundError`，执行 `pip install tzdata`（PEP 615 的官方时区数据包）。不对未亲自验证过的平台组合做兼容性承诺。

## 第二步：准备官方 lark-cli

已安装（本指南在 1.0.96 验证）：保留现有版本，不盲目升级，直接进入下一步。

未安装（此时需要 Node 及自带 npx）：按官方文档 <https://github.com/larksuite/cli/blob/main/README.zh.md> 执行：

```bash
npx @larksuite/cli@latest install
```

完成后重新执行 `lark-cli --version` 确认命令可用。

## 第三步：获取本仓库

- 用户提供本地完整目录：设为 `REPO`，直接进入下一步。
- 从公开仓库获取：`git clone https://github.com/zenokat/zeno-waytoagi.git zeno-waytoagi`，将克隆结果设为 `REPO`。

发布状态：首版实现当前只在本地提交，公开仓库尚未包含。若克隆结果中没有 `install.py` 和 `skills/zeno-waytoagi/`，说明拿到的是初始化状态——请改用用户提供的本地完整目录继续；这是发布进度问题，不是 CLI 或权限问题。

## 第四步：安装 Skill

先确定 `SKILLS_DIR`：Agent 按自己 Harness 的约定识别（例如 Claude Code 默认 `~/.claude/skills`，Codex 默认 `${CODEX_HOME:-~/.codex}/skills`；其他 Agent 查其官方文档）。无法确定时向用户确认 Agent 类型与安装范围（仅当前用户还是本机共享），不让用户凭空选择文件系统目录。然后：

```bash
python3 REPO/install.py --target SKILLS_DIR
```

输出与处理：

- `installed`：首次安装完成。
- `already_installed`：目标内容与本仓库一致，安全跳过。
- `TARGET_CONFLICT: ...`：目标已有不同内容，脚本未做任何改动。向用户报告路径，由用户决定备份删除后重装，或明确执行 `--force`（脚本把原目录重命名为旁边的 `zeno-waytoagi.backup*` 再安装，新旧并存）。
- `SOURCE_INCOMPLETE: ...`：安装源缺少必需文件（SKILL.md、每日脚本、读取参考或本指南），回到第三步取得完整仓库。

安装只复制 `skills/zeno-waytoagi` 包内容，不含仓库工程文件、Git 历史或任何凭证；缓存与编译产物（`__pycache__`、`.DS_Store`、`.pyc`/`.pyo`）不进入安装结果。完成判据：`SKILL_DIR/SKILL.md` 存在。

## 第五步：应用配置与用户授权

应用是否存在与用户授权是否有效是两个独立判断，分开处理。

### 5.1 选定 PROFILE

```bash
lark-cli profile list
```

按顺序确定：

1. 用户明确指定的 profile 优先。
2. 存在标准命名 `zeno-waytoagi` 的 profile：核对后使用。
3. 无命名配置：复用默认生效 profile（列表中 `effective: true` 的项），后续命令可省略 `--profile`。
4. 存在多个无法判断的候选：列出候选及各自用户身份，请用户选择。

选定后，同一 `PROFILE` 贯穿本指南全部 daily、search、docs、auth 命令，不中途更换，不执行 `profile use`。

### 5.2 应用配置（仅在应用实际缺失时新建）

`lark-cli profile list` 中选定 profile 带有 `appId`：应用存在，始终保留复用，直接进入 5.3，无论其授权状态如何。

应用实际缺失（本机没有任何可用应用），或用户明确选择使用其他应用：

```bash
lark-cli config show --profile zeno-waytoagi   # 返回 not_configured 说明名字未占用；已占用则复用它或换名
lark-cli config init --new --name zeno-waytoagi
```

`--name` 追加独立命名 profile，不替换默认配置；`config init` 不会自动切换当前生效 profile。该命令阻塞并引导用户在浏览器中创建应用：在后台运行它，从输出取出引导链接发给用户，用户完成后命令返回。Agent 上下文（`OPENCLAW_HOME` / `HERMES_HOME` 已设置）中该命令默认拒绝：优先 `lark-cli config bind` 绑定 Agent 既有应用；仅当用户明确要求独立应用时加 `--force-init`。

### 5.3 用户授权（独立于应用配置）

```bash
lark-cli auth status --json --verify --profile PROFILE   # 复用默认 profile 时省略 --profile
```

- 用户身份有效且 scope 已覆盖所需范围：直接进入第六步。
- 令牌显示即将过期或需续期：先做一次只读调用（如第六步的每日命令）让 CLI 自动刷新凭证；成功则继续，不因此新建应用或重新授权。
- 未授权、刷新失败或缺少 scope：按下面的 split-flow 发起授权。所需范围是候选读取权限（未经剥离验证的最小集合）：`docs:document.content:read`、`docx:document:readonly`、`search:docs:read`、`wiki:node:retrieve`、`offline_access`。首次授权使用该清单；补齐场景以 CLI 错误中 `missing_scopes` 列出的具体 scope 为准，只增量授权缺失项。

```bash
lark-cli auth login --profile PROFILE \
  --scope "docs:document.content:read docx:document:readonly search:docs:read wiki:node:retrieve offline_access" \
  --no-wait --json
```

从 JSON 输出取 `verification_url` 发给用户（可用 `lark-cli auth qrcode <url>` 生成二维码），`device_code` 只保留在会话变量里，然后结束本轮并明确告知用户：完成授权后回来确认。用户确认后由 Agent 亲自执行：

```bash
lark-cli auth login --profile PROFILE --device-code <device_code>
```

备选官方阻塞流程：去掉 `--no-wait --json`，命令阻塞并展示链接直到用户完成授权。

注意：

- 授权命令必须带 `--scope`（或明确的 `--domain`）；不带范围会请求全部业务域，本 Skill 不需要。
- 会话中断或 device code 失效：按相同 scope 重新执行发起命令，生成新链接和新 code，不复用旧的。
- 多次 login 是增量授权，不撤销已有 scope。

## 第六步：验证三类能力

每条命令都带 `--profile PROFILE`（复用默认 profile 时省略）。

1. 每日更新：

```bash
python3 SKILL_DIR/scripts/waytoagi_daily.py --profile PROFILE
```

判据：退出码 0，输出 JSON 的 `status` 为 `ok`、`date_batch_not_present` 或 `outside_available_window` 之一，字段语义与 [waytoagi-access.md](waytoagi-access.md) 的状态表一致。

2. 知识库搜索：

```bash
lark-cli drive +search --query "ComfyUI" --space-ids 7226178700923011075 \
  --as user --page-size 5 --format json --profile PROFILE
```

判据：`ok` 为 true。搜索摘要只代表命中上下文，不代表已读正文。

3. 正文读取（URL 取上一步任一结果的 `result_meta.url`）：

```bash
lark-cli docs +fetch --doc '<取得的 URL>' --as user \
  --doc-format markdown --detail simple --profile PROFILE
```

判据：`ok` 为 true 且返回 `data.document.content`。

## 失败处理

- 授权或 scope 不足：错误 JSON 中的 `missing_scopes` 列出缺失项，按该 scope 重新走 5.3 的授权流程（增量，不影响已有授权）。用户身份要求应用开通 scope 和用户授权两层都满足。
- profile 不存在：`--profile` 指定的名字未配置时 CLI 返回 `not_configured` 及可用列表；回到 5.1 重新选定，不新建同名配置冒充。
- 资源访问被拒绝（如 Wiki 错误 `131006`）：这是文档或知识库层面的授权问题，与接口 scope 不同。向用户说明实际被拒的资源，由用户核对访问资格；不反复登录、不切换身份、不改用匿名页面抓取。
- 网络或限流：按 CLI 输出中的可重试提示处理，不直接解释为需要重新授权。
- 凭证续期：短期凭证过期时 CLI 会自动尝试刷新；续期凭证失效会返回需要重新授权的明确错误，按 5.3 重新授权。

## 验收边界

- 本指南在 CLI 1.0.96 验证。既有应用与已授权用户身份下，三类能力（每日批次、知识库搜索、正文读取）已经真实用户确认。
- 新建应用的引导流程本轮操作超时退出，未完整验证；命名 profile 的首次创建与首次授权全流程、普通新账号（跨租户）访问该知识库的条件均未验证。未亲自跑通第六步前，不宣称相应路径可用。
