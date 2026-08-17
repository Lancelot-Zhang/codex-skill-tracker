# Codex Skill Tracker

[English](README.md) | 简体中文

> 自动记录 Codex 每轮任务真正加载并使用过的 Skill。

Codex Skill Tracker 是一个适用于 Codex Desktop 和 Codex CLI 的轻量级本地
`Stop` Hook。它会检查当前轮次的 transcript，并报告已成功加载 `SKILL.md`
指令的 Skill。

```text
本轮使用 Skill · 2 | openai-docs | skill-creator
```

该结果由 Hook 根据 transcript 生成，并非由模型回忆得出。在 Codex Desktop
中，正常回答会保持展开，Skill 统计结果可通过回答下方的 Hook 详情按钮查看。

## 使用 Codex 安装

将下面的提示词发送给 Codex：

```text
请先审查下面的安装文档，然后严格按照文档安装并验证 Codex Skill Tracker。
保留我现有的所有 Hook，不要覆盖现有配置：
https://raw.githubusercontent.com/GODGOD126/codex-skill-tracker/v0.1.0/INSTALL.md
```

Codex 会根据本机环境调整安装路径和 Python 命令，安全地将 Hook 合并到现有
配置中，运行冒烟测试，并在仍需通过 `/hooks` 信任 Hook 时提醒用户。

完整的安装、升级和卸载约定请参阅 [INSTALL.md](INSTALL.md)。

## 哪些情况会被计为使用 Skill

追踪器会统计以下运行时信号：

- 平台注入的 Skill 块中包含真实的 `SKILL.md` 路径
- 工具调用成功读取了 `SKILL.md` 文件

以下情况不会被统计：

- Skill 只出现在可用 Skill 目录中
- Skill 名称只在对话中被提及
- 读取操作失败
- 工具、MCP 服务器、库、插件或子代理

Codex 目前没有提供专用的 `SkillUse` 生命周期事件。因此，对于这个最小可用
版本而言，成功加载完整的 Skill 指令是目前最可靠的通用运行时信号。

## 隐私与安全

Hook 在运行时：

- 只读取 Codex 提供的 transcript 路径
- 不发起网络请求
- 不修改 transcript 或项目文件
- 仅将意外错误的诊断信息写入操作系统临时目录
- 返回 `continue: true`，因此不会创建第二条助手回答

安装文档要求 Codex 先备份并合并 `~/.codex/hooks.json`，而不是直接覆盖。
安装完成后，Codex 可能要求用户检查并信任 Hook；这是有意保留的安全步骤。

## 开发

本项目没有第三方运行时依赖。

```powershell
python -m unittest discover -s tests -v
python -m py_compile src/codex_skill_tracker_hook.py
```

检查已有轮次：

```powershell
python src/codex_skill_tracker_hook.py `
  --transcript "C:\path\to\rollout.jsonl" `
  --turn-id "turn-id"
```

## 许可证

[MIT](LICENSE)
