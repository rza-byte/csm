#!/usr/bin/env python3
"""CSM status helper — session data, transcript access, schema validation."""

import json
import os
import sys
import time
import subprocess
from pathlib import Path

CLAUDE_SESSIONS = Path.home() / ".claude" / "sessions"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
CSM_SESSION = "csm"

EXPECTED_FIELDS = {"pid", "sessionId", "cwd", "status", "startedAt", "updatedAt"}


def _read_json_safe(path):
    """Read JSON with one retry on write-race."""
    for attempt in range(3):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            if attempt < 2:
                time.sleep(0.05)
    return None


def load_sessions():
    """Return list of session dicts from ~/.claude/sessions/*.json."""
    sessions = []
    if not CLAUDE_SESSIONS.exists():
        return sessions

    for path in sorted(CLAUDE_SESSIONS.glob("*.json")):
        data = _read_json_safe(path)
        if not data:
            continue

        pid = data.get("pid")
        alive = bool(pid and Path(f"/proc/{pid}").exists())
        started_ms = data.get("startedAt", 0) or 0
        age_min = int((time.time() * 1000 - started_ms) / 60_000) if started_ms else 0
        cwd = data.get("cwd", "")
        project = Path(cwd).name if cwd else "unknown"
        status = data.get("status", "unknown")

        sessions.append({
            "pid": str(pid or "?"),
            "alive": str(alive),
            "status": status,
            "cwd": cwd,
            "project": project,
            "age_min": str(age_min),
            "session_id": data.get("sessionId", ""),
            "_path": str(path),
        })

    return sessions


def cmd_sessions():
    """Print TSV: pid\talive\tstatus\tcwd\tproject\tage_min"""
    for s in load_sessions():
        print(f"{s['pid']}\t{s['alive']}\t{s['status']}\t{s['cwd']}\t{s['project']}\t{s['age_min']}")


def cmd_recent_dirs():
    """Print unique recent project directories (most recent first)."""
    seen = set()
    # From live sessions first
    for s in sorted(load_sessions(), key=lambda x: x["age_min"]):
        d = s["cwd"]
        if d and os.path.isdir(d) and d not in seen:
            seen.add(d)
            print(d)
    # Then from Claude projects folder (decoded from encoded path names)
    if CLAUDE_PROJECTS.exists():
        for entry in sorted(CLAUDE_PROJECTS.iterdir(),
                             key=lambda p: p.stat().st_mtime, reverse=True):
            # Claude encodes /home/user/foo/bar as -home-user-foo-bar
            # Heuristic decode: strip leading -, replace - with /
            # This is approximate; skip if path doesn't exist
            name = entry.name
            if name.startswith("-"):
                candidate = "/" + name[1:].replace("-", "/")
                # Walk up to find the longest matching real dir
                parts = candidate.split("/")
                for i in range(len(parts), 1, -1):
                    attempt = "/".join(parts[:i])
                    if os.path.isdir(attempt) and attempt not in seen:
                        seen.add(attempt)
                        print(attempt)
                        break


def cmd_log(win_str):
    """Show recent transcript messages for the Claude session in tmux window WIN."""
    try:
        win = int(win_str)
    except (ValueError, TypeError):
        print(f"Invalid window number: {win_str}")
        return

    # Get cwd from tmux pane
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-t", f"{CSM_SESSION}:{win}",
             "-p", "#{pane_current_path}"],
            capture_output=True, text=True, timeout=5
        )
        cwd = result.stdout.strip()
    except Exception as e:
        print(f"Could not query tmux: {e}")
        return

    if not cwd:
        # Fall back to matching session by window name
        print("No active pane found at that window.")
        return

    # Find the matching project transcript
    # Claude encodes cwd as -home-user-... (leading dash, slashes become dashes)
    encoded = "-" + cwd.lstrip("/").replace("/", "-")
    transcript_path = None

    if CLAUDE_PROJECTS.exists():
        for proj_dir in sorted(CLAUDE_PROJECTS.iterdir(),
                                key=lambda p: p.stat().st_mtime, reverse=True):
            if proj_dir.name == encoded:
                jsonl_files = sorted(proj_dir.glob("*.jsonl"),
                                     key=lambda p: p.stat().st_mtime, reverse=True)
                if jsonl_files:
                    transcript_path = jsonl_files[0]
                    break

    if not transcript_path:
        print(f"No transcript found for: {cwd}")
        print(f"(looked for project key: {encoded})")
        return

    print(f"Session: {Path(cwd).name}")
    print(f"CWD:     {cwd}")
    print(f"File:    {transcript_path}")
    print("─" * 70)

    messages = []
    with open(transcript_path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = msg.get("role", "")
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        content = block["text"]
                        break
            if isinstance(content, str) and content.strip():
                messages.append((role, content.strip()))

    for role, text in messages[-40:]:
        prefix = "[user]     " if role == "user" else "[assistant]"
        # Wrap long lines
        lines = text.replace("\n", " ").strip()
        print(f"{prefix} {lines[:200]}")


def cmd_schema_check():
    """Validate that Claude's session JSON schema matches expectations."""
    paths = list(CLAUDE_SESSIONS.glob("*.json")) if CLAUDE_SESSIONS.exists() else []
    if not paths:
        print("  No session files to check.")
        return

    data = _read_json_safe(paths[0])
    if not data:
        print("  Could not read session file.")
        return

    actual = set(data.keys())
    missing = EXPECTED_FIELDS - actual
    extra = actual - EXPECTED_FIELDS

    if missing:
        print(f"  ⚠  Schema drift — missing expected fields: {missing}")
    if extra:
        print(f"  ℹ  Extra fields (new in this Claude version): {extra}")
    if not missing:
        print("  ✓ Session schema looks correct.")


COMMANDS = {
    "sessions":     cmd_sessions,
    "recent-dirs":  cmd_recent_dirs,
    "log":          cmd_log,
    "schema-check": cmd_schema_check,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sessions"
    args = sys.argv[2:]
    fn = COMMANDS.get(cmd)
    if fn:
        fn(*args)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
