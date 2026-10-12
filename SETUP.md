# zeno-waytoagi 安装入口（交给 Agent 执行）

把这份文档完整交给一个有终端能力的 Agent。Agent 按本文定位完整指南，再由完整指南完成环境检查、CLI 安装、Skill 安装、飞书应用配置与用户授权，并验证三类读取能力。

## 发布状态

首版实现当前只在本地提交，公开仓库（<https://github.com/zenokat/zeno-waytoagi>）尚未包含本实现。仅访问远端仓库的用户现在无法通过克隆获得可安装版本；需要用户提供本地完整目录。这是发布进度状态，不是 CLI 或权限问题。

## 完整指南位置

完整步骤只维护一份：`skills/zeno-waytoagi/references/setup.md`。按实际情形定位：

- 用户提供了本地完整目录：读取 `<本地目录>/skills/zeno-waytoagi/references/setup.md`，按其中步骤执行。
- 用户已安装本 Skill：读取已安装包内的 `references/setup.md`（位于 Skill 父目录下的 `zeno-waytoagi/`），按其"已安装 Skill 的接续"节直接从应用配置与授权步骤继续。
- 只能从公开仓库获取：待首版发布后，读取 <https://github.com/zenokat/zeno-waytoagi/blob/main/skills/zeno-waytoagi/references/setup.md>，或执行 `git clone https://github.com/zenokat/zeno-waytoagi.git zeno-waytoagi` 后读本地副本。发布前克隆结果不含 `install.py` 与 `skills/`，此时改用用户提供的本地完整目录。

## 执行边界

- 只在本机操作：不推送仓库、不发布内容、不创建远端 Issue，不修改用户已有的其他 Skill。
- 已有应用和已有用户授权一律复用；只有应用实际缺失（或用户明确选择其他应用）时才创建新应用，且使用命名 profile，不覆盖默认配置和已有凭证。
- 授权只按实际缺失的具体 scope 增量发起，不请求全部业务域；资源访问被拒绝与缺少 scope 是两类问题，分开处理，失败时不改用匿名抓取。
- device code、授权链接、凭证只存在于当前会话的变量中，不写入文件、不写入 Git、不随消息外发。

## 验收边界

- 本流程在 CLI 1.0.96 验证；既有应用与已授权用户身份下，三类能力已经真实用户确认。
- 新建应用的引导流程本轮操作超时退出，未完整验证；命名 profile 的首次创建与首次授权全流程、普通新账号（跨租户）访问条件均未验证。未跑通完整指南第六步前，不宣称相应路径可用。
