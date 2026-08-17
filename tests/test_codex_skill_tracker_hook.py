from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.codex_skill_tracker_hook import (
    build_hook_response,
    detect_used_skills,
    format_footer,
)


TURN_ID = "turn-current"
OTHER_TURN_ID = "turn-other"


def response_item(payload: dict, turn_id: str = TURN_ID) -> dict:
    payload = dict(payload)
    payload["internal_chat_message_metadata_passthrough"] = {"turn_id": turn_id}
    return {"type": "response_item", "payload": payload}


def function_call(
    call_id: str,
    command: str,
    *,
    turn_id: str = TURN_ID,
    name: str = "shell_command",
) -> dict:
    return response_item(
        {
            "type": "function_call",
            "name": name,
            "arguments": json.dumps({"command": command}),
            "call_id": call_id,
        },
        turn_id,
    )


def function_output(
    call_id: str,
    output: str,
    *,
    turn_id: str = TURN_ID,
) -> dict:
    return response_item(
        {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
        },
        turn_id,
    )


def custom_tool_call(
    call_id: str,
    code: str,
    *,
    turn_id: str = TURN_ID,
    name: str = "exec",
) -> dict:
    return response_item(
        {
            "type": "custom_tool_call",
            "name": name,
            "input": code,
            "call_id": call_id,
        },
        turn_id,
    )


def custom_tool_output(
    call_id: str,
    output: object,
    *,
    turn_id: str = TURN_ID,
) -> dict:
    return response_item(
        {
            "type": "custom_tool_call_output",
            "call_id": call_id,
            "output": output,
        },
        turn_id,
    )


class CodexSkillTrackerHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.transcript = Path(self.temp_dir.name) / "rollout.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_rows(self, rows: list[dict]) -> None:
        with self.transcript.open("w", encoding="utf-8") as output:
            for row in rows:
                output.write(json.dumps(row, ensure_ascii=False) + "\n")

    def detect(self) -> list[str]:
        return detect_used_skills(self.transcript, TURN_ID)

    def test_available_catalog_does_not_count_as_usage(self) -> None:
        self.write_rows(
            [
                {
                    "type": "session_meta",
                    "payload": {
                        "base_instructions": {
                            "text": (
                                "- openai-docs: Official docs "
                                "(file: r0/openai-docs/SKILL.md)"
                            )
                        }
                    },
                }
            ]
        )
        self.assertEqual(self.detect(), [])

    def test_platform_injected_skill_is_reported_without_tool_call(self) -> None:
        self.write_rows(
            [
                response_item(
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "<skill>\n"
                                    "<name>openai-docs</name>\n"
                                    "<path>C:\\skills\\openai-docs\\SKILL.md</path>\n"
                                    "---\n"
                                    "name: openai-docs\n"
                                    "description: docs\n"
                                    "---\n"
                                    "Body\n"
                                    "</skill>"
                                ),
                            }
                        ],
                    }
                )
            ]
        )
        self.assertEqual(self.detect(), ["openai-docs"])

    def test_user_pasted_skill_block_without_platform_path_is_not_usage(self) -> None:
        self.write_rows(
            [
                response_item(
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "<skill>\n"
                                    "---\n"
                                    "name: shared-example\n"
                                    "description: pasted for review\n"
                                    "---\n"
                                    "Body\n"
                                    "</skill>"
                                ),
                            }
                        ],
                    }
                )
            ]
        )
        self.assertEqual(self.detect(), [])

    def test_available_skills_wrapper_is_not_injected_usage(self) -> None:
        self.write_rows(
            [
                response_item(
                    {
                        "type": "message",
                        "role": "developer",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "<skills_instructions>\n"
                                    "- openai-docs: docs "
                                    "(file: r0/openai-docs/SKILL.md)\n"
                                    "</skills_instructions>"
                                ),
                            }
                        ],
                    }
                )
            ]
        )
        self.assertEqual(self.detect(), [])

    def test_successful_skill_read_is_reported(self) -> None:
        self.write_rows(
            [
                function_call(
                    "call-1",
                    "Get-Content -Raw -LiteralPath "
                    "'C:\\Users\\me\\.codex\\skills\\openai-docs\\SKILL.md'",
                ),
                function_output(
                    "call-1",
                    "Exit code: 0\nOutput:\n"
                    "---\nname: \"openai-docs\"\ndescription: docs\n---\nBody",
                ),
            ]
        )
        self.assertEqual(self.detect(), ["openai-docs"])

    def test_code_mode_exec_sed_skill_read_is_reported(self) -> None:
        self.write_rows(
            [
                custom_tool_call(
                    "call-1",
                    "const result = await tools.exec_command({"
                    "cmd: \"sed -n '1,240p' "
                    "/Users/me/.codex/skills/openai-docs/SKILL.md\""
                    "}); text(result.output);",
                ),
                custom_tool_output(
                    "call-1",
                    [
                        {
                            "type": "text",
                            "text": (
                                "---\nname: openai-docs\n"
                                "description: docs\n---\nBody"
                            ),
                        }
                    ],
                ),
            ]
        )
        self.assertEqual(self.detect(), ["openai-docs"])

    def test_glob_skill_paths_are_not_reported(self) -> None:
        for pattern in ("*/SKILL.md", "**/SKILL.md"):
            with self.subTest(pattern=pattern):
                self.write_rows(
                    [
                        custom_tool_call(
                            "call-1",
                            "const result = await tools.exec_command({"
                            f"cmd: \"sed -n '1,20p' "
                            f"/Users/me/.codex/skills/{pattern}\""
                            "}); text(result.output);",
                        ),
                        custom_tool_output(
                            "call-1",
                            [{"type": "text", "text": "Skill files found"}],
                        ),
                    ]
                )
                self.assertEqual(self.detect(), [])

    def test_failed_read_is_not_reported(self) -> None:
        self.write_rows(
            [
                function_call(
                    "call-1",
                    "Get-Content -Raw 'C:\\missing\\example\\SKILL.md'",
                ),
                function_output(
                    "call-1",
                    "Exit code: 1\nOutput:\nGet-Content: file not found",
                ),
            ]
        )
        self.assertEqual(self.detect(), [])

    def test_skill_content_may_document_an_error_name(self) -> None:
        self.write_rows(
            [
                function_call(
                    "call-1",
                    "Get-Content -Raw 'C:\\skills\\debugging\\SKILL.md'",
                ),
                function_output(
                    "call-1",
                    "Exit code: 0\nOutput:\n"
                    "---\nname: debugging\ndescription: test\n---\n"
                    "This Skill explains how to diagnose ParserError.",
                ),
            ]
        )
        self.assertEqual(self.detect(), ["debugging"])

    def test_other_turn_is_ignored(self) -> None:
        self.write_rows(
            [
                function_call(
                    "call-1",
                    "Get-Content -Raw 'C:\\skills\\playwright\\SKILL.md'",
                    turn_id=OTHER_TURN_ID,
                ),
                function_output(
                    "call-1",
                    "Exit code: 0\nOutput:\n"
                    "---\nname: playwright\ndescription: browser\n---\nBody",
                    turn_id=OTHER_TURN_ID,
                ),
            ]
        )
        self.assertEqual(self.detect(), [])

    def test_duplicate_reads_are_deduplicated_in_order(self) -> None:
        rows: list[dict] = []
        for call_id, name in (
            ("call-1", "openai-docs"),
            ("call-2", "playwright"),
            ("call-3", "openai-docs"),
        ):
            rows.extend(
                [
                    function_call(
                        call_id,
                        f"Get-Content -Raw 'C:\\skills\\{name}\\SKILL.md'",
                    ),
                    function_output(
                        call_id,
                        "Exit code: 0\nOutput:\n"
                        f"---\nname: {name}\ndescription: test\n---\nBody",
                    ),
                ]
            )
        self.write_rows(rows)
        self.assertEqual(self.detect(), ["openai-docs", "playwright"])

    def test_path_mention_without_read_operation_is_not_reported(self) -> None:
        self.write_rows(
            [
                function_call(
                    "call-1",
                    "Test-Path 'C:\\skills\\playwright\\SKILL.md'",
                ),
                function_output("call-1", "Exit code: 0\nOutput:\nTrue"),
            ]
        )
        self.assertEqual(self.detect(), [])

    def test_apply_patch_with_skill_text_is_not_reported(self) -> None:
        self.write_rows(
            [
                function_call(
                    "call-1",
                    "Get-Content C:\\skills\\fake\\SKILL.md",
                    name="apply_patch",
                ),
                function_output(
                    "call-1",
                    "Exit code: 0\nOutput:\n"
                    "---\nname: fake\ndescription: fake\n---\nBody",
                ),
            ]
        )
        self.assertEqual(self.detect(), [])

    def test_catalog_restores_plugin_namespace(self) -> None:
        self.write_rows(
            [
                {
                    "type": "session_meta",
                    "payload": {
                        "base_instructions": {
                            "text": (
                                "- product-design:index: Router "
                                "(file: r10/index/SKILL.md)"
                            )
                        }
                    },
                },
                function_call(
                    "call-1",
                    "Get-Content -Raw "
                    "'C:\\plugins\\product-design\\skills\\index\\SKILL.md'",
                ),
                function_output(
                    "call-1",
                    "Exit code: 0\nOutput:\n"
                    "---\nname: index\ndescription: router\n---\nBody",
                ),
            ]
        )
        self.assertEqual(self.detect(), ["product-design:index"])

    def test_first_stop_surfaces_exact_zero_footer_without_continuation(
        self,
    ) -> None:
        self.write_rows([])
        response = build_hook_response(
            {
                "transcript_path": str(self.transcript),
                "turn_id": TURN_ID,
                "stop_hook_active": False,
                "last_assistant_message": "Normal answer",
            }
        )
        self.assertEqual(
            response,
            {"continue": True, "systemMessage": "Skills used · 0 | None"},
        )

    def test_missing_transcript_is_distinct_from_zero(self) -> None:
        response = build_hook_response(
            {
                "transcript_path": str(self.transcript.with_name("missing.jsonl")),
                "turn_id": TURN_ID,
                "stop_hook_active": False,
                "last_assistant_message": "Normal answer",
            }
        )
        self.assertEqual(
            response,
            {
                "continue": True,
                "systemMessage": "Skills used · ? | Tracking unavailable",
            },
        )

    def test_active_stop_never_creates_a_continuation(self) -> None:
        self.write_rows([])
        response = build_hook_response(
            {
                "transcript_path": str(self.transcript),
                "turn_id": TURN_ID,
                "stop_hook_active": True,
                "last_assistant_message": "Normal answer",
            }
        )
        self.assertEqual(
            response,
            {"continue": True, "systemMessage": "Skills used · 0 | None"},
        )

    def test_footer_format(self) -> None:
        self.assertEqual(format_footer([]), "Skills used · 0 | None")
        self.assertEqual(
            format_footer(["openai-docs", "playwright"]),
            "Skills used · 2 | openai-docs | playwright",
        )


if __name__ == "__main__":
    unittest.main()
