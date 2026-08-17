# Codex Skill Tracker installation contract

This document is written for Codex to execute. The human user should be able to
provide only this document URL and ask Codex to install, verify, upgrade, or
uninstall the Hook.

Release described by this document: `v0.1.0`

Source file:

```text
https://raw.githubusercontent.com/GODGOD126/codex-skill-tracker/v0.1.0/src/codex_skill_tracker_hook.py
```

## Safety requirements

Follow all of these requirements:

1. Read the source file before executing it.
2. Do not overwrite or remove any existing Hook.
3. Back up an existing `hooks.json` before changing it.
4. Merge JSON structurally. Do not use string replacement.
5. Install only inside the user's Codex home directory.
6. Use the exact tagged source URL above, not a mutable branch.
7. Do not disable Hook review, trust prompts, sandboxing, or other safety
   controls.
8. If the configuration is malformed or the correct Codex home cannot be
   determined safely, stop and report the exact problem.

## Installation

### 1. Determine Codex home

Use `CODEX_HOME` when it is explicitly set to a non-empty absolute path.
Otherwise use the current user's `.codex` directory:

- Windows: `%USERPROFILE%\.codex`
- macOS and Linux: `$HOME/.codex`

Resolve the absolute path before writing anything. Never install into a
workspace, repository, system directory, or another user's profile.

### 2. Select Python

Require Python 3.10 or newer.

- On Windows, prefer the `py` launcher with `-3`; otherwise use `python`.
- On macOS and Linux, prefer `python3`; otherwise use `python`.

Run the selected interpreter with `--version`. Stop if it is missing or older
than Python 3.10. Record the exact executable and arguments because the Hook
configuration must use the same command.

### 3. Download the tagged source

Create this directory under the resolved Codex home:

```text
hooks/codex-skill-tracker/
```

Download the tagged source file to:

```text
hooks/codex-skill-tracker/codex_skill_tracker_hook.py
```

Read the downloaded file and confirm it matches the reviewed source. Do not
execute content fetched from any other host or revision.

### 4. Back up and merge Hook configuration

The configuration file is:

```text
<codex-home>/hooks.json
```

If it exists, create a timestamped sibling backup before editing:

```text
hooks.json.codex-skill-tracker.backup-YYYYMMDD-HHMMSS
```

Parse the configuration as JSON. Preserve every existing top-level field,
event, matcher, and Hook entry. Ensure these containers exist:

```json
{
  "hooks": {
    "Stop": []
  }
}
```

Append exactly one Stop entry in this shape:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "<selected-python-command> <absolute-installed-script-path>",
      "timeout": 5,
      "statusMessage": "正在统计本轮使用的 Skill"
    }
  ]
}
```

JSON-escape the command and absolute path correctly for the current operating
system. Quote executable and script paths when they contain spaces.

Before appending, search existing Stop Hook commands for
`codex_skill_tracker_hook.py`. If one already exists, update that entry in
place instead of creating a duplicate. Do not alter sibling entries.

Write valid UTF-8 JSON and parse it again after writing. If validation fails,
restore the timestamped backup and report the error.

### 5. Verify the installed Hook

Run these checks with the selected Python command:

1. Compile the installed script with `python -m py_compile`.
2. Create an empty temporary JSONL transcript.
3. Run the script with:

```text
--transcript <temporary-jsonl-path> --turn-id install-smoke-test
```

4. Parse standard output as JSON.
5. Require this semantic result:

```json
{
  "continue": true,
  "systemMessage": "Skills used · 0 | None"
}
```

Delete only the temporary test transcript. Do not delete the configuration
backup.

### 6. Finish

Tell the user:

- The installed script path
- The configuration path
- The backup path, if one was created
- Which verification checks passed
- That Codex may need to be restarted
- That the user must open `/hooks` and review/trust the new Hook if prompted

Do not claim the installation is fully active until the Hook is trusted and a
new Codex task has completed.

## Upgrade

For an upgrade, read the new tagged installation document first. Replace only
the installed `codex_skill_tracker_hook.py`, keep the existing Hook entry,
repeat all verification checks, and report the old and new versions.

## Uninstall

To uninstall:

1. Back up the current `hooks.json`.
2. Parse it as JSON.
3. Remove only Stop Hook entries whose command contains
   `codex_skill_tracker_hook.py`.
4. Preserve all other configuration and Hooks.
5. Validate and write the resulting JSON.
6. Remove only the resolved
   `<codex-home>/hooks/codex-skill-tracker/` directory after verifying that
   exact path remains inside the Codex home.
7. Report what was removed and the new backup path.

Do not restore an old full-file backup automatically because doing so could
erase unrelated Hook changes made after installation.
