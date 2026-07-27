"""Backward-compatible entry point for pre-v0.1 installations."""

from codex_skill_tracker_hook import main


if __name__ == "__main__":
    raise SystemExit(main())
