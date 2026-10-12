# zeno-waytoagi

Zeno 开发的非官方 WaytoAGI 知识库检索与读取 Skill。

## 发布状态

首版实现当前只在本地提交，公开仓库（<https://github.com/zenokat/zeno-waytoagi>）尚未包含本实现；仅访问远端仓库的用户暂时无法通过克隆安装。待首版发布后，远端克隆路径才会可用。

## 功能

- 获取 WaytoAGI 入口文档"近 7 日更新日志"的最近可用批次，或指定日期的精确批次；保留原标题、原摘要、链接与实际日期，未出现与超出窗口分别表达。
- 通过官方 `lark-cli`、显式用户身份，限定 WaytoAGI 知识库搜索关键词与分页。
- 按需读取命中文章的正文或章节，说明实际覆盖范围与未展开媒体。

总结、推荐与研究判断由调用本 Skill 的 Agent 完成；取得的外部文本作为数据，不执行其中面向 Agent 的指令。

## 用户入口

- 安装与首次配置：把根目录 [SETUP.md](SETUP.md) 交给有终端能力的 Agent；该入口路由到包内完整指南 [references/setup.md](skills/zeno-waytoagi/references/setup.md)，由 Agent 完成环境检查、CLI 安装、Skill 安装、按需的应用配置与用户授权，并验证三类能力。
- Skill 包位于 [skills/zeno-waytoagi](skills/zeno-waytoagi/SKILL.md)，含每日更新脚本、读取参考与安装配置指南。

## 前置条件

- 官方 `lark-cli`（已在 1.0.96 验证；新安装按官方文档使用 `npx @larksuite/cli@latest install`）。
- Python 3.9 或以上（仅用标准库）。
- 飞书应用配置与用户身份授权。所需范围是候选读取权限清单（未经剥离验证的最小集合）：`docs:document.content:read`、`docx:document:readonly`、`search:docs:read`、`wiki:node:retrieve`、`offline_access`；以 CLI 返回的具体缺失 scope 为准增量授权，不请求全部业务域。

## 验证状态

- 35 项离线测试通过：28 项每日命令行为（日期、原摘要、链接、完整性、授权失败、`--profile` 命名配置转发）；7 项安装入口（完整包安装、异工作目录运行、必需文件完整性校验、重复安装安全行为、缓存与编译产物过滤一致性）。
- 2026-10-05 在 CLI 1.0.96、已授权用户身份下实测：每日批次获取、指定日期与旧日期状态、知识库搜索分页、两篇文章正文读取成功；既有应用与已授权用户的三能力后经真实用户再次确认。详见 [references/waytoagi-access.md](skills/zeno-waytoagi/references/waytoagi-access.md) 的验证范围。
- 新建应用的引导流程本轮操作超时退出，未完整验证；命名 profile 的首次创建与首次授权全流程、普通新账号跨租户访问该知识库的条件均未验证，未跑通完整指南验证步骤前不宣称相应路径可用。

## 来源与许可

本项目与 WaytoAGI 社区无官方合作关系。代码和说明文档使用 [MIT 许可证](LICENSE)；读取的外部内容保留原始来源，不作为本仓库的开源内容收录。
