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
6. 容器内重新发起设备码登录成功，等待 Zeno 在本机浏览器完成授权。前一次普通登录进程已退出，临时本机回调转送服务已关闭。

以上属于实验所需 Agent 的运行环境准备，不能记作 Skill setup 已通过或 Skill 产品故障。认证链接、临时代码和凭证不收录在本记录或 Git 中。

## 接续位置

当前尚未启动容器内 Agent 的 Skill 安装任务，尚未新建飞书应用或发起飞书授权。

完成 Agent 登录后，向容器内 Agent 提供当前 Skill 副本和首次安装请求；由其读取 [setup.md](../skills/zeno-waytoagi/setup.md) 并执行。遇到用户操作时交还控制权，由双方逐环节体验，再记录行为、阻碍和需求讨论结果。

本次仅代表 Linux 空白环境的一条真实路径，不能据此宣称 Mac、其他系统或所有异常分支均已验收。
