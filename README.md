# Codex Skill Tracker

English | [Simplified Chinese](README.zh-CN.md)

> Automatically track which Skills Codex actually used in each task.

Codex Skill Tracker is a small, local `Stop` Hook for Codex Desktop and Codex
CLI. It inspects the current turn transcript and reports Skills whose
`SKILL.md` instructions were successfully loaded.

```text
本轮使用 Skill · 2 | openai-docs | skill-creator
```

The Hook generates this result from the transcript rather than asking the
model to recall its activity. In Codex Desktop, the normal answer remains
expanded, and the Skill result is available from the Hook details button below
the answer.

## Install with Codex

Give Codex the following prompt:

```text
Review the installation document below, then follow it exactly to install and
verify Codex Skill Tracker. Preserve all of my existing Hooks and do not
overwrite my current configuration:
https://raw.githubusercontent.com/GODGOD126/codex-skill-tracker/v0.1.0/INSTALL.md
```

Codex will adapt the installation path and Python command to the local
machine, safely merge the Hook into the existing configuration, run a smoke
test, and tell the user when `/hooks` trust is still required.

See [INSTALL.md](INSTALL.md) for the complete installation, upgrade, and
uninstall contract.

## What counts as Skill usage

The tracker counts these runtime signals:

- A platform-injected Skill block containing a real `SKILL.md` path
- A successful tool call that reads a `SKILL.md` file

It deliberately does not count:

- Skills that only appear in the available-Skills catalog
- Skill names that are only mentioned in chat
- Failed reads
- Tools, MCP servers, libraries, plugins, or sub-agents

Codex currently exposes no dedicated `SkillUse` lifecycle event. Successful
loading of the complete Skill instructions is therefore the strongest generic
runtime signal available to this MVP.

## Privacy and safety

At runtime, the Hook:

- Reads only the transcript path supplied by Codex
- Makes no network requests
- Does not modify the transcript or project files
- Writes only unexpected error diagnostics to the operating system's temporary
  directory
- Returns `continue: true`, so it never creates a second assistant response

The installation document requires Codex to back up and merge
`~/.codex/hooks.json` instead of replacing it. Codex may ask the user to review
and trust the Hook after installation; this security step is intentional.

## Development

The project has no third-party runtime dependencies.

```powershell
python -m unittest discover -s tests -v
python -m py_compile src/codex_skill_tracker_hook.py
```

Inspect an existing turn:

```powershell
python src/codex_skill_tracker_hook.py `
  --transcript "C:\path\to\rollout.jsonl" `
  --turn-id "turn-id"
```

## License

[MIT](LICENSE)
