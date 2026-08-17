# Codex Skill Tracker

English | [简体中文](README.zh-CN.md)

> See which Codex Skills were actually loaded during a task.

Codex Skill Tracker is a lightweight, local `Stop` Hook for Codex Desktop and
Codex CLI. At the end of each turn, it inspects that turn's transcript and
shows one compact line:

```text
Skills used · 2 | openai-docs | skill-creator
```

The result is generated from runtime evidence instead of asking the model to
remember which Skills it used. The normal assistant answer stays unchanged;
the tracker result appears in the Hook details for that answer.

This is an unofficial community project and is not affiliated with OpenAI.

## Features

- Reports Skills in first-use order and removes duplicates
- Recognizes platform-injected Skills and successful `SKILL.md` reads
- Supports normal tool calls and Code Mode transcript records
- Runs locally with the Python standard library only
- Makes no network requests at runtime
- Preserves the normal assistant answer and emits only one final status line
- Distinguishes "no Skill used" from "tracking unavailable"

## Project status

This project is early-stage. Codex provides `transcript_path` to command Hooks,
but the transcript format is not a stable public interface. Future Codex
updates may therefore require parser changes. See the
[official Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks).

## Requirements

- Codex Desktop or Codex CLI with Hooks support
- Python 3.10 or newer
- Permission to write to the current user's Codex home directory
- A trusted local copy of this repository or an immutable tagged release

No third-party Python package is required.

## Installation

### Recommended: let Codex install the checked-out version

Using a local checkout keeps `INSTALL.md` and the Python source on the same
revision. Prefer a tagged release. If the revision you want has not been
released yet, clone the repository and review the selected commit first.

1. Download a tagged release or clone this repository.
2. Open the repository folder in Codex Desktop, or start Codex CLI from the
   repository root.
3. Send Codex this prompt:

```text
Install Codex Skill Tracker from this repository checkout.

Before changing anything:
1. Read INSTALL.md and src/codex_skill_tracker_hook.py completely.
2. Tell me which Codex home, Python executable, script path, and hooks.json
   file you will use.
3. Preserve every existing Hook and merge the new Stop Hook structurally.

Then follow INSTALL.md, compile the installed script, run its smoke test, and
report every changed path. Do not claim the Hook is active until you have told
me how to review and trust it with /hooks.
```

Codex should perform these concrete actions:

1. Select Python 3.10 or newer.
2. Review and copy `src/codex_skill_tracker_hook.py` to:

   ```text
   <codex-home>/hooks/codex-skill-tracker/codex_skill_tracker_hook.py
   ```

3. Merge one `Stop` entry into `<codex-home>/hooks.json` without replacing any
   existing Hook.
4. Compile the installed file and run an empty-transcript smoke test.
5. Report the installed paths, any configuration backup, and whether `/hooks`
   review is still required.

The detailed, cross-platform execution contract is in
[INSTALL.md](INSTALL.md).

### Manual configuration reference

The installed entry has this shape. Merge it into the existing JSON; do not
replace the entire configuration with this example.

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

Quote and JSON-escape paths correctly for the operating system. The Python
command in `hooks.json` must be the same interpreter used during verification.

### Activate and verify

After installation:

1. Restart Codex if it does not reload the configuration automatically.
2. Open `/hooks` and review/trust the new command Hook if prompted. Codex skips
   untrusted command Hooks.
3. Start a new task that loads a Skill.
4. Open the Hook details below the answer and confirm that a `Skills used` line
   is present.

### Upgrade or uninstall

Use `INSTALL.md` from the target release or checkout and ask Codex to follow
its **Upgrade** or **Uninstall** section. An upgrade replaces only the tracker
script and keeps the existing Hook entry. Uninstallation removes only tracker
entries and the tracker installation directory.

## How it works

For every `Stop` event, Codex supplies the Hook with the current `turn_id` and
`transcript_path`. The tracker then:

1. Reads the local JSONL transcript.
2. Selects records belonging to the current turn.
3. Finds platform-injected Skill blocks and successful reads of `SKILL.md`.
4. Normalizes names using the available-Skills catalog when possible.
5. Returns the result through `systemMessage` with `continue: true`.

It does not block the turn or generate a second assistant response.

## What counts as Skill usage

The tracker counts:

- A platform-injected Skill block that contains a real `SKILL.md` path
- A successful tool call that reads a `SKILL.md` file

It does not count:

- Skills that appear only in the available-Skills catalog
- Skill names mentioned only in conversation or source code
- Failed or incomplete reads
- Ordinary tools, MCP servers, libraries, plugins, or sub-agents

Loading the complete Skill instructions is the strongest generic runtime
signal currently available to this project. It shows that Codex loaded the
Skill, not that every instruction necessarily affected the final answer.

## Output reference

| State | Example |
| --- | --- |
| One or more Skills detected | `Skills used · 2 | openai-docs | skill-creator` |
| No Skill detected | `Skills used · 0 | None` |
| Transcript unavailable or unreadable | `Skills used · ? | Tracking unavailable` |

## Privacy and safety

At runtime, the Hook:

- Reads only the transcript path supplied by Codex
- Makes no network requests
- Does not modify the transcript or project files
- Writes only unexpected error diagnostics to the operating system's temporary
  directory
- Returns `continue: true`

The transcript may contain sensitive conversation or tool data. Do not share
raw transcripts in public issues; create a minimal, redacted reproduction.

## Known limitations

- Codex transcripts are convenient Hook inputs, but their format may change.
- Unusual or newly introduced transcript record types may not be recognized
  until support is added.
- Reads that do not expose a recognizable `SKILL.md` path may be missed.
- The tracker is turn-scoped and does not claim to audit every operation inside
  separate sub-agent transcripts.
- Hook presentation differs between Codex clients; in Codex Desktop the line
  may be shown inside expandable Hook details.

## Troubleshooting

| Problem | Check |
| --- | --- |
| No tracker result appears | Open `/hooks`, confirm the Hook is enabled and trusted, then restart Codex if needed. |
| `Tracking unavailable` appears | Confirm Codex supplied a readable transcript and that the installed script can read it. |
| A Skill is missing | Confirm its complete `SKILL.md` was successfully loaded during the same turn. |
| Duplicate tracker results appear | Search all active `hooks.json` and `config.toml` layers for duplicate tracker commands. |
| The Hook fails to start | Run the exact configured Python command manually and confirm Python is version 3.10 or newer. |

Unexpected Python exceptions are appended to
`<temporary-directory>/codex-skill-tracker-hook-errors.log`.

## Development

Run the test suite and syntax check from the repository root:

```sh
python -m unittest discover -s tests -v
python -m py_compile src/codex_skill_tracker_hook.py
```

On Windows, `py -3` can be used instead of `python`. To inspect an existing
turn directly:

```sh
python src/codex_skill_tracker_hook.py \
  --transcript /path/to/rollout.jsonl \
  --turn-id turn-id
```

### Project layout

```text
src/codex_skill_tracker_hook.py   Main Hook and diagnostic CLI
src/show_skills_hook.py           Compatibility entry point for older installs
tests/                             Unit and transcript-regression tests
INSTALL.md                         Installation, upgrade, and uninstall contract
README.zh-CN.md                    Simplified Chinese documentation
```

## Contributing

Bug reports and pull requests are welcome. For detection bugs, include the
smallest redacted transcript fixture that reproduces the issue, the expected
Skill list, the actual output, the Codex client, operating system, and Python
version. New behavior should include regression tests.

## Upstream and license

This repository originated from
[GODGOD126/codex-skill-tracker](https://github.com/GODGOD126/codex-skill-tracker).
Please retain upstream attribution when redistributing modified versions.

Released under the [MIT License](LICENSE).
