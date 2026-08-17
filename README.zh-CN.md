# Codex Skill Tracker

[English](README.md) | 简体中文

> 查看 Codex 在任务中真正加载了哪些 Skill。

Codex Skill Tracker 是一个适用于 Codex Desktop 和 Codex CLI 的轻量级本地
`Stop` Hook。每轮结束时，它会检查该轮 transcript，并显示一行简洁结果：

```text
Skills used · 2 | openai-docs | skill-creator
```

该结果来自运行时证据，并非要求模型回忆自己使用过哪些 Skill。正常的助手回答
不会被修改；统计结果会显示在该回答对应的 Hook 详情中。

本项目是非官方社区项目，与 OpenAI 没有关联。

## 功能特点

- 按首次使用顺序报告 Skill，并自动去重
- 识别平台注入的 Skill 和成功读取的 `SKILL.md`
- 支持普通工具调用和 Code Mode transcript 记录
- 仅使用 Python 标准库在本地运行
- 运行时不发起网络请求
- 保留正常回答，仅输出一行最终状态
- 明确区分“没有使用 Skill”和“无法完成追踪”

## 项目状态

本项目仍处于早期阶段。Codex 会向命令 Hook 提供 `transcript_path`，但
transcript 格式并不是稳定的公共接口，因此未来的 Codex 更新可能需要同步修改
解析逻辑。参见
[Codex Hooks 官方文档](https://learn.chatgpt.com/docs/hooks)。

## 环境要求

- 支持 Hooks 的 Codex Desktop 或 Codex CLI
- Python 3.10 或更高版本
- 当前用户的 Codex 主目录可写
- 已审查的本地仓库副本，或不可变的版本标签（tag）

不需要安装任何第三方 Python 包。

## 安装

### 推荐方式：让 Codex 安装当前 checkout 中的版本

从本地 checkout 安装，可以保证 `INSTALL.md` 与 Python 源码属于同一个版本。
优先使用带标签的正式版本；如果所需修改尚未发布，请先克隆仓库并审查选定的
commit。

1. 下载一个带标签的正式版本，或克隆本仓库。
2. 在 Codex Desktop 中打开仓库目录，或从仓库根目录启动 Codex CLI。
3. 将下面的提示词发送给 Codex：

```text
请从当前仓库 checkout 安装 Codex Skill Tracker。

在修改任何内容之前：
1. 完整阅读 INSTALL.md 和 src/codex_skill_tracker_hook.py。
2. 告诉我将使用哪个 Codex 主目录、Python 可执行文件、脚本安装路径和
   hooks.json 文件。
3. 保留所有现有 Hook，并通过结构化 JSON 合并新的 Stop Hook。

然后严格执行 INSTALL.md，编译已安装脚本，运行冒烟测试，并报告每个被修改的
路径。在告诉我如何通过 /hooks 检查和信任该 Hook 之前，不要声称安装已经生效。
```

Codex 应当完成以下明确操作：

1. 选择 Python 3.10 或更高版本。
2. 审查 `src/codex_skill_tracker_hook.py`，并复制到：

   ```text
   <codex-home>/hooks/codex-skill-tracker/codex_skill_tracker_hook.py
   ```

3. 向 `<codex-home>/hooks.json` 合并一个 `Stop` 条目，不替换任何现有 Hook。
4. 编译已安装文件，并使用空 transcript 运行冒烟测试。
5. 报告安装路径、配置备份，以及是否仍需通过 `/hooks` 完成审查。

完整的跨平台执行约定见 [INSTALL.md](INSTALL.md)。

### 手动配置参考

安装后的条目结构如下。应当把它合并到已有 JSON 中，不能用该示例替换整个
配置文件。

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "<python-command> <absolute-script-path>",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

请根据操作系统正确引用路径并进行 JSON 转义。`hooks.json` 中配置的 Python
命令必须与验证时使用的解释器完全一致。

### 激活与验证

安装完成后：

1. 如果 Codex 没有自动重新加载配置，请重启 Codex。
2. 打开 `/hooks`；如果出现提示，请检查并信任新的命令 Hook。Codex 会跳过
   尚未信任的命令 Hook。
3. 新建一个会加载 Skill 的任务。
4. 打开回答下方的 Hook 详情，确认其中出现 `Skills used` 状态行。

### 升级或卸载

使用目标 release 或 checkout 中的 `INSTALL.md`，让 Codex 执行其中的
**Upgrade** 或 **Uninstall** 部分。升级只替换追踪器脚本并保留现有 Hook
条目；卸载只移除追踪器条目和追踪器安装目录。

## 工作原理

每次触发 `Stop` 事件时，Codex 会向 Hook 提供当前 `turn_id` 和
`transcript_path`。追踪器随后：

1. 读取本地 JSONL transcript。
2. 选取属于当前轮次的记录。
3. 查找平台注入的 Skill 块，以及成功读取 `SKILL.md` 的操作。
4. 在可能的情况下，利用可用 Skill 目录规范化名称。
5. 通过 `systemMessage` 返回结果，同时保持 `continue: true`。

它不会阻止当前轮次，也不会生成第二条助手回答。

## 哪些情况会被计为使用 Skill

追踪器会统计：

- 包含真实 `SKILL.md` 路径的平台注入 Skill 块
- 成功读取 `SKILL.md` 文件的工具调用

追踪器不会统计：

- 只出现在可用 Skill 目录中的 Skill
- 只在对话或源代码中被提及的 Skill 名称
- 失败或未完成的读取操作
- 普通工具、MCP 服务器、库、插件或子代理

成功加载完整 Skill 指令，是本项目目前能够获得的最可靠通用运行时信号。它能
证明 Codex 加载了该 Skill，但不能证明其中每一条指令都影响了最终回答。

## 输出说明

| 状态 | 示例 |
| --- | --- |
| 检测到一个或多个 Skill | `Skills used · 2 | openai-docs | skill-creator` |
| 未检测到 Skill | `Skills used · 0 | None` |
| transcript 不存在或无法读取 | `Skills used · ? | Tracking unavailable` |

## 隐私与安全

Hook 在运行时：

- 只读取 Codex 提供的 transcript 路径
- 不发起网络请求
- 不修改 transcript 或项目文件
- 仅将意外错误的诊断信息写入操作系统临时目录
- 始终返回 `continue: true`

transcript 可能包含敏感对话或工具数据。不要在公开 issue 中上传原始
transcript；请制作最小化且经过脱敏的复现样例。

## 已知限制

- Codex transcript 适合作为 Hook 输入，但其格式可能变化。
- 新增或少见的 transcript 记录类型，在适配前可能无法识别。
- 如果读取操作没有暴露可识别的 `SKILL.md` 路径，追踪器可能漏报。
- 追踪器以当前轮次为范围，不声称能够审计独立子代理 transcript 内的全部操作。
- 不同 Codex 客户端显示 Hook 的方式不同；在 Codex Desktop 中，状态行可能位于
  可展开的 Hook 详情内。

## 故障排查

| 问题 | 检查方法 |
| --- | --- |
| 没有显示追踪结果 | 打开 `/hooks`，确认 Hook 已启用并受信任；必要时重启 Codex。 |
| 显示 `Tracking unavailable` | 确认 Codex 提供了可读 transcript，并且已安装脚本有权读取它。 |
| 某个 Skill 没有被统计 | 确认同一轮中确实成功加载了该 Skill 的完整 `SKILL.md`。 |
| 出现重复追踪结果 | 检查所有生效的 `hooks.json` 和 `config.toml` 层，查找重复命令。 |
| Hook 无法启动 | 手动运行配置中的同一 Python 命令，并确认 Python 不低于 3.10。 |

意外 Python 异常会追加到
`<temporary-directory>/codex-skill-tracker-hook-errors.log`。

## 开发

在仓库根目录运行测试和语法检查：

```sh
python -m unittest discover -s tests -v
python -m py_compile src/codex_skill_tracker_hook.py
```

Windows 可以使用 `py -3` 代替 `python`。如需直接检查已有轮次：

```sh
python src/codex_skill_tracker_hook.py \
  --transcript /path/to/rollout.jsonl \
  --turn-id turn-id
```

### 项目结构

```text
src/codex_skill_tracker_hook.py   Hook 主程序与诊断命令行
src/show_skills_hook.py           兼容旧安装的入口文件
tests/                             单元测试和 transcript 回归测试
INSTALL.md                         安装、升级与卸载执行约定
README.md                          英文文档
```

## 参与贡献

欢迎提交 bug 报告和 pull request。对于检测问题，请提供能够复现问题的最小化
脱敏 transcript fixture、期望 Skill 列表、实际输出、Codex 客户端、操作系统和
Python 版本。新增行为应同时添加回归测试。

## 许可证

本项目采用 [MIT License](LICENSE)。
