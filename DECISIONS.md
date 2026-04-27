# Architecture Decisions

## Why tmux as the foundation?

tmux is the right choice because:
- Already installed, battle-tested PTY manager and process supervisor
- `prefix+[n]` window switching is instant with zero extra code
- `display-popup` and `display-menu` provide modal UIs without a TUI framework
- Sessions survive terminal disconnects — closing Windows Terminal doesn't kill Claude
- Fully scriptable via `send-keys`, `display-message`, `list-windows`, etc.

Alternatives rejected:
- **screen** — strictly worse than tmux in every dimension
- **Zellij** — better default UI, but no `display-menu` equivalent; smaller ecosystem; extra hard dependency
- **Custom TUI (bubbletea/ratatui)** — would require reimplementing PTY handling and process supervision; 10× the work for marginal UX gain
- **VS Code terminal tabs + extension** — no headless/SSH story; ties the tool to an editor

## Why the dashboard is a tmux window, not the status bar?

The status bar approach (`status-interval` + `status-right`) is compact but limited:
- Can't show more than ~80 chars of session data without mangling layout
- Can't accept keyboard input for switching/creating sessions
- Clutters every window in the session

A dedicated window 0 means you visit the dashboard only when you want the overview. The rest of the time you're in your Claude window with full screen real estate.

## Why `read -s -n1 -t3` for the input loop?

This handles both refresh timing and key input in a single blocking call:
- If a key is pressed within 3s: handle it immediately (no perceived lag)
- If no key in 3s: fall through and redraw the dashboard

Limitation: multi-byte escape sequences (arrow keys = ESC+`[`+letter) need special handling. The current implementation ignores arrow keys rather than misinterpreting them.

Roadmap: replace with tmux-native key bindings (`bind-key -T prefix`) for zero-latency response.

## Why Python for JSON, not jq?

Both are available. Python wins for this workload because:
- Multi-file aggregation + liveness checks + age calculation is 20 lines in Python vs 60+ in jq+bash
- Retry-on-parse-failure (write races) is clean in Python
- All logic lives in one file (`csm-status.py`) — one edit point when Claude's schema changes
- The project directory encoding/decoding (`-home-user-foo` → `/home/user/foo`) is string manipulation that jq handles awkwardly

## Why a graceful kill sequence?

`tmux kill-window` sends SIGHUP immediately. Claude Code may be mid-tool-execution: writing a file, running a database migration, making an API call. Abrupt termination can leave partial writes.

The `_safe_kill_claude` sequence:
1. Sends SIGTERM to the Claude process (not the shell)
2. Waits up to 10 seconds for clean exit
3. Sends SIGKILL only if the process hasn't exited
4. Then closes the tmux window

## Why per-project `.csmrc` instead of a central config?

A central `~/.config/csm/projects.toml` requires manual maintenance as you clone new repos. A `.csmrc` file in the repo root:
- Lives with the code — committing it means teammates get the same context automatically
- Discovered by walking up the directory tree, so monorepos work naturally
- Contains only two fields (`kube_context`, `aws_profile`) — simple enough to not need a format spec

## Why not require fzf?

fzf makes the directory picker and session jumper significantly better, but:
- Many servers and minimal WSL installs don't have it
- `tmux display-menu` provides adequate navigation without it
- `apt install fzf` is recommended but not blocked on

CSM uses `display-menu` as the baseline. Future versions may prefer fzf when available.

## Why inotify over polling?

Polling `~/.claude/sessions/` every 3 seconds wastes CPU and adds latency. `inotifywait` from `inotify-tools` fires the moment Claude writes a status update — typically when it transitions between idle/busy/waiting. Dashboard refresh then happens in under 100ms of the actual state change.

CSM degrades gracefully: if `inotify-tools` is not installed, the 3-second `read` timeout drives refresh instead.
