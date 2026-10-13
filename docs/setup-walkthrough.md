# 从空白环境共同走一遍 setup

本记录保存 Zeno 与 Echo 共同体验首次配置的实际经过，用于后续界定 setup 的产品需求。先观察流程，再讨论边界与预期行为；此时不改动 Skill 或实现。

## 本次起点

- 日期：2026-10-13。
- 实验容器：`zeno-waytoagi-setup-20261013-01`，Debian bookworm-slim，Linux ARM64。
- 容器无宿主目录挂载，未使用特权模式；不复制本机飞书配置、应用凭证或授权。
- Agent 运行准备：Codex CLI 0.162.1 官方 Linux 完整发行包，以及 curl、Git、sudo 和系统根证书；Agent 使用独立用户 `setup-agent`。
- Skill 配置前已确认 Python、Node、lark-cli 不存在，Agent 用户尚无 Codex 登录凭证或 lark-cli 配置。
- 输入是本地提交 `0d52f66` 中的 README、许可证和完整 Skill 包，放在容器的 `/home/setup-agent/source/`；并未上传远端，也未代替 Agent 安装 Skill。
- 本次体验要求新建飞书应用并完成首次用户授权，不复用 Zeno 已有的飞书应用。

## 实验环境准备的实际阻碍

1. Docker Hub 的 Ubuntu 镜像下载超时，改用本机缓存的 Debian 基础镜像创建空白容器。
2. Debian 默认软件源下载很慢，容器内改用清华 Debian 镜像后正常下载；软件包签名校验保留。
3. Codex 设备码登录请求返回 403；普通浏览器登录可以到达容器回调，但兑换凭证时明确返回 `Country, region, or territory not supported`。
4. 对照发现：Mac 已启用本机 HTTP/HTTPS 系统代理，命令行直连与容器直连的出网国家代码为 CN，显式使用现有系统代理的对照结果为 JP。容器没有继承 Mac 的系统代理。
5. 通过 Colima 提供的宿主入口验证，容器可以使用同一个既有代理。只为本次 Codex 调用设置代理环境变量，未修改 Mac 全局代理设置。
6. 容器内重新发起设备码登录成功。Zeno 完成授权后，登录进程返回成功，`codex login status` 确认为 ChatGPT 登录。前一次普通登录进程已退出，临时本机回调转送服务已关闭。

以上属于实验所需 Agent 的运行环境准备，不能记作 Skill setup 已通过或 Skill 产品故障。认证链接、临时代码和凭证不收录在本记录或 Git 中。

## Skill 首次配置：已观察到的第一段

将首次安装请求交给容器内的真实 Codex Agent，要求从零新建飞书应用，遇到用户操作时先停下来等待确认。没有向它提供本机原有飞书配置、此前测试结果或主会话的隐藏操作。

- Agent 读取 Skill、setup、失败处理说明及其自带的安装规范，将完整 Skill 副本安装到 `/home/setup-agent/.codex/skills/zeno-waytoagi`，检查副本与源包一致。
- Agent 安装 Python、tzdata、Node/npm，确认 Python 3.11 与 `Asia/Singapore` 时区可用。
- 第一次执行官方 `npx --yes @larksuite/cli@latest install` 失败。Agent 报告 Debian 提供的 Node 18 无法运行当前安装器，自行改为下载官方 Node 22 后重试；本回合结束时 Node 升级及 CLI 安装仍未完成，不能记作依赖准备通过。
- Agent 查阅官方应用配置与权限说明后，选择先由用户在飞书开发者后台创建企业自建应用，再逐项配置权限。它给出官方后台链接、应用名称和描述，要求创建后停在详情页，明确不要发送 App Secret 或令牌，然后结束本回合等待用户。

以上手动创建路线是本次 Agent 的执行选择，尚未确认为产品的默认流程；也没有据此证明 CLI 浏览器引导的新建应用路线不能满足读取权限要求。两条路线的交互成本与权限边界仍需在后续共同讨论。

## 接续位置

当前等待 Zeno 完成企业自建应用的创建并回复；权限配置、应用发布、CLI 接入、飞书用户授权和三个功能验证均未执行。Node 升级与 CLI 安装也仍待继续。

容器内 Agent 会话为 `01a1357a-0c5b-7b92-a9e3-8a7a0de687b8`，回合正常结束，源码副本未修改；仍沿用 [setup.md](../skills/zeno-waytoagi/setup.md) 接续。CLI 收尾另报会话记录错误，但对应 rollout 文件实际存在，原会话恢复能力将在下一回合验证。

本次仅代表 Linux 空白环境的一条真实路径，不能据此宣称 Mac、其他系统或所有异常分支均已验收。
