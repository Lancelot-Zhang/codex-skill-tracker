"""Codex Stop hook that reports Skills loaded during the current turn."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any


SKILL_FILE_PATTERN = re.compile(r"(?i)(?:^|[\\/])SKILL\.md\b")
READ_OPERATION_PATTERN = re.compile(
    r"""(?ix)
    \bget-content\b
    |(?:^|[\s;&|"'`])gc(?:\.exe)?(?:\s|$)
    |(?:^|[\s;&|"'`])cat(?:\.exe)?(?:\s|$)
    |(?:^|[\s;&|"'`])sed(?:\.exe)?(?:\s|$)
    |\bread(?:_file|file|text|_text|mcp_resource)?\b
    |\breadfilesync\b
    |\bskills?\.read\b
    |\bskills?_read\b
    |\bload_skill\b
    """
)
EXIT_CODE_PATTERN = re.compile(r"(?im)^\s*Exit code:\s*(?P<code>\d+)")
EXPLICIT_ERROR_FLAG_PATTERN = re.compile(
    r'(?i)"(?:is_error|isError)"\s*:\s*true'
)
FRONTMATTER_PATTERN = re.compile(
    r"(?ms)^[ \t]*---[ \t]*\r?\n(?P<header>.*?)[ \t]*\r?\n---[ \t]*$"
)
FRONTMATTER_NAME_PATTERN = re.compile(
    r"""(?im)^[ \t]*name[ \t]*:[ \t]*["']?(?P<name>[^"'\r\n#]+?)["']?[ \t]*$"""
)
CATALOG_PATTERN = re.compile(
    r"(?m)^-\s+(?P<name>\S+):\s+.*?\(file:\s+(?P<path>[^)\r\n]+SKILL\.md)\)"
)
PATH_PATTERN = re.compile(
    r"""(?ix)
    (?P<path>
        (?:[a-z]:)?[^\s"'`|;<>]*[\\/]
        [^\s"'`|;<>]*SKILL\.md
    )
    """
)
PATH_DERIVED_SKILL_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)
INJECTED_SKILL_PATTERN = re.compile(
    r"(?is)<skill>(?P<body>.*?)</skill>"
)
INJECTED_SKILL_NAME_PATTERN = re.compile(
    r"(?is)<name>\s*(?P<name>[^<\r\n]+?)\s*</name>"
)
INJECTED_SKILL_PATH_PATTERN = re.compile(
    r"(?is)<path>\s*[^<\r\n]*SKILL\.md\s*</path>"
)

TRACKABLE_TOOL_NAMES = {
    "bash",
    "shell_command",
    "exec",
    "exec_command",
    "read_mcp_resource",
    "read_file",
    "read_text_file",
}


def _json_text(value: Any) -> str:
    """Return a searchable representation of a tool input or output."""

    if value is None:
        return ""
    if isinstance(value, str):
        pieces = [value]
        stripped = value.strip()
        if stripped.startswith(("{", "[", '"')):
            try:
                decoded = json.loads(stripped)
            except (json.JSONDecodeError, TypeError):
                pass
            else:
                if decoded != value:
                    pieces.append(_json_text(decoded))
        return "\n".join(piece for piece in pieces if piece)
    if isinstance(value, dict):
        return "\n".join(
            f"{key}\n{_json_text(item)}" for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return "\n".join(_json_text(item) for item in value)
    return str(value)


def _payload_turn_id(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    if isinstance(metadata, dict):
        turn_id = metadata.get("turn_id")
        if isinstance(turn_id, str):
            return turn_id
    return None


def iter_transcript_rows(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as transcript:
        for raw_line in transcript:
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield row


def _catalog_entries(rows: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for row in rows:
        searchable = ""
        if row.get("type") == "session_meta":
            searchable = _json_text(row.get("payload", {}))
        elif row.get("type") == "response_item":
            payload = row.get("payload", {})
            if isinstance(payload, dict) and payload.get("role") in {
                "user",
                "developer",
                "system",
            }:
                searchable = _json_text(payload.get("content"))

        for match in CATALOG_PATTERN.finditer(searchable):
            entry = (match.group("name"), match.group("path"))
            if entry not in seen:
                seen.add(entry)
                entries.append(entry)

    return entries


def _canonical_name(
    raw_name: str,
    tool_input: str,
    catalog: list[tuple[str, str]],
) -> str:
    name = raw_name.strip()
    candidates = [
        (catalog_name, catalog_path)
        for catalog_name, catalog_path in catalog
        if catalog_name == name or catalog_name.endswith(f":{name}")
    ]

    if len(candidates) == 1:
        return candidates[0][0]

    normalized_input = tool_input.replace("\\\\", "\\").replace("\\", "/").lower()
    for catalog_name, catalog_path in candidates:
        prefix = catalog_name.split(":", 1)[0].lower()
        normalized_catalog_path = catalog_path.replace("\\", "/").lower()
        meaningful_parts = [
            part
            for part in normalized_catalog_path.split("/")
            if part and not re.fullmatch(r"r\d+", part)
        ]
        suffix = "/".join(meaningful_parts)
        if prefix in normalized_input or (
            suffix and normalized_input.find(suffix) >= 0
        ):
            return catalog_name

    for catalog_name, _ in candidates:
        if catalog_name == name:
            return name
    return name


def _frontmatter_names(output: str) -> list[str]:
    names: list[str] = []
    for block in FRONTMATTER_PATTERN.finditer(output):
        name_match = FRONTMATTER_NAME_PATTERN.search(block.group("header"))
        if name_match:
            name = name_match.group("name").strip()
            if name and name not in names:
                names.append(name)
    return names


def _path_names(tool_input: str) -> list[str]:
    names: list[str] = []
    normalized = tool_input.replace("\\\\", "\\")
    for match in PATH_PATTERN.finditer(normalized):
        path_text = match.group("path").rstrip("),]")
        parts = re.split(r"[\\/]", path_text)
        if len(parts) < 2:
            continue
        name = parts[-2].strip()
        if (
            PATH_DERIVED_SKILL_NAME_PATTERN.fullmatch(name)
            and name.lower() not in {"skills", ".agents"}
            and name not in names
        ):
            names.append(name)
    return names


def _is_trackable_read(tool_name: str, tool_input: str) -> bool:
    normalized_name = tool_name.lower()
    if normalized_name == "apply_patch":
        return False
    if normalized_name not in TRACKABLE_TOOL_NAMES and "read" not in normalized_name:
        return False
    if not SKILL_FILE_PATTERN.search(tool_input.replace("\\\\", "\\")):
        return False
    return bool(
        READ_OPERATION_PATTERN.search(tool_input)
        or "read" in normalized_name
    )


def _output_succeeded(output: str) -> bool:
    if not output.strip():
        return False
    exit_codes = [
        int(match.group("code")) for match in EXIT_CODE_PATTERN.finditer(output)
    ]
    if exit_codes:
        return all(code == 0 for code in exit_codes)
    return not EXPLICIT_ERROR_FLAG_PATTERN.search(output)


def detect_used_skills(transcript_path: Path, turn_id: str) -> list[str]:
    """Return Skills successfully loaded in one Codex turn, in first-use order."""

    rows = list(iter_transcript_rows(transcript_path))
    catalog = _catalog_entries(rows)
    calls: dict[str, tuple[str, str]] = {}
    outputs: dict[str, str] = {}
    injected: list[tuple[str, str]] = []
    active_turn_id: str | None = None

    for row in rows:
        row_type = row.get("type")
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue

        if row_type == "turn_context":
            context_turn_id = payload.get("turn_id")
            if isinstance(context_turn_id, str):
                active_turn_id = context_turn_id
            continue

        if row_type != "response_item":
            continue

        row_turn_id = _payload_turn_id(payload) or active_turn_id
        if row_turn_id != turn_id:
            continue

        payload_type = payload.get("type")
        if payload_type == "message" and payload.get("role") in {
            "developer",
            "user",
        }:
            message_text = _json_text(payload.get("content"))
            for skill_match in INJECTED_SKILL_PATTERN.finditer(message_text):
                body = skill_match.group("body")
                if not INJECTED_SKILL_PATH_PATTERN.search(body):
                    continue
                tag_name = INJECTED_SKILL_NAME_PATTERN.search(body)
                raw_names = (
                    [tag_name.group("name").strip()]
                    if tag_name
                    else _frontmatter_names(body)
                )
                for raw_name in raw_names:
                    injected.append((raw_name, body))
            continue

        call_id = payload.get("call_id")
        if not isinstance(call_id, str) or not call_id:
            continue

        if payload_type in {"function_call", "custom_tool_call"}:
            tool_name = str(payload.get("name", ""))
            raw_input = payload.get("arguments")
            if raw_input is None:
                raw_input = payload.get("input")
            tool_input = _json_text(raw_input)
            calls[call_id] = (tool_name, tool_input)
        elif payload_type in {"function_call_output", "custom_tool_call_output"}:
            outputs[call_id] = _json_text(payload.get("output"))

    used: list[str] = []
    for raw_name, source_text in injected:
        name = _canonical_name(raw_name, source_text, catalog)
        if name and name not in used:
            used.append(name)

    for call_id, (tool_name, tool_input) in calls.items():
        if not _is_trackable_read(tool_name, tool_input):
            continue
        output = outputs.get(call_id, "")
        if not _output_succeeded(output):
            continue

        raw_names = _frontmatter_names(output) or _path_names(tool_input)
        for raw_name in raw_names:
            name = _canonical_name(raw_name, tool_input, catalog)
            if name and name not in used:
                used.append(name)

    return used


def format_footer(skills: list[str]) -> str:
    if not skills:
        return "Skills used · 0 | None"
    return f"Skills used · {len(skills)} | " + " | ".join(skills)


def _error_footer() -> str:
    return "Skills used · ? | Tracking unavailable"


def build_hook_response(event: dict[str, Any]) -> dict[str, Any]:
    transcript_value = event.get("transcript_path")
    turn_id = event.get("turn_id")
    if not isinstance(transcript_value, str) or not isinstance(turn_id, str):
        footer = _error_footer()
    else:
        transcript_path = Path(transcript_value)
        if not transcript_path.is_file():
            footer = _error_footer()
        else:
            skills = detect_used_skills(transcript_path, turn_id)
            footer = format_footer(skills)

    # Do not return `decision: block` here. A blocked Stop creates a second
    # assistant continuation in Codex Desktop, which moves the real answer
    # into the collapsed "Worked for..." section. `systemMessage` surfaces the
    # hook-generated footer without replacing or hiding the original answer.
    return {"continue": True, "systemMessage": footer}


def _log_error(exc: BaseException) -> None:
    try:
        log_path = (
            Path(tempfile.gettempdir())
            / "codex-skill-tracker-hook-errors.log"
        )
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"{type(exc).__name__}: {exc}\n")
    except OSError:
        pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--turn-id")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.transcript or args.turn_id:
            if not args.transcript or not args.turn_id:
                raise ValueError("--transcript and --turn-id must be used together")
            event = {
                "transcript_path": os.fspath(args.transcript),
                "turn_id": args.turn_id,
            }
        else:
            event = json.load(sys.stdin)
            if not isinstance(event, dict):
                raise TypeError("hook input must be a JSON object")

        response = build_hook_response(event)
    except Exception as exc:  # A hook must never break the Codex turn.
        _log_error(exc)
        response = {"continue": True, "systemMessage": _error_footer()}

    # ASCII-only JSON avoids Windows console code-page corruption. Codex
    # decodes the escaped middle dot before displaying systemMessage.
    json.dump(response, sys.stdout, ensure_ascii=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
