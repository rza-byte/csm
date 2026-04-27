# CSM — Claude Session Manager

A tmux-based CLI for managing multiple [Claude Code](https://claude.ai/code) sessions from a single terminal window.

## Features

- **Live dashboard** — status, project name, age, and CWD for every running session
- **Instant switching** — press a number key to jump between sessions
- **Per-project context** — auto-load kubectl cluster and AWS profile from `.csmrc`
- **Graceful kill** — SIGTERM + 10s wait before SIGKILL; never interrupts mid-write
- **Adopt orphans** — bring Claude sessions started outside CSM under management
- **Log tail** — read any session's transcript in a popup without leaving the dashboard
- **Notifications** — desktop alerts when sessions go idle or need your input
- **Audit log** — every action logged to `~/.local/state/csm/audit.log`

## Install

```bash
git clone https://github.com/rza-byte/csm
cd csm
bash install.sh
```

**Optional dependencies** (strongly recommended):

```bash
sudo apt install fzf inotify-tools libnotify-bin
```

| Package | Benefit |
|---|---|
| `fzf` | Better directory picker |
| `inotify-tools` | Real-time dashboard updates (no polling) |
| `libnotify-bin` | Desktop notifications on idle/waiting |

## Usage

```bash
csm                      # Launch or attach to the dashboard
csm new                  # New Claude session (interactive directory picker)
csm new ~/my/repo        # New Claude session in a specific directory
csm list                 # List all sessions in the terminal
csm kill 2              # Gracefully kill window 2
csm jump paybox          # Switch to the session whose name contains "paybox"
csm log 3                # Tail the transcript for window 3
csm adopt                # Detect and re-manage orphan Claude sessions
csm doctor               # Check dependencies and session health
```

## Dashboard

```
CSM — Claude Session Manager           Mon Apr 27 21:30:00
──────────────────────────────────────────────────────────────────────
  WIN  STATUS    PROJECT                       AGE    CWD
  ───  ────────  ────────────────────────────  ─────  ─────────────────
  [1]  ● busy    AI-IDEAS                      0m     ~/Claude-Code/AI-IDEAS
  [2]  ○ idle    hyp_paybox_service_backend    8h     ~/CreditGuard-SAAS/...
  [3]  ○ idle    ashraitemv_bankproxy          8h     ~/CreditGuard-SAAS/...
  [4]  ○ idle    coralogix                     8h     ~/CreditGuard-SAAS/...
  [5]  ⏳ wait   ashraitunix-cronjobs          3h     ~/CreditGuard-SAAS/...
  [6]  💀 dead   deployment                    ?      ~/CreditGuard-SAAS/...
──────────────────────────────────────────────────────────────────────
  [1-9] Switch  [N] New  [J] Jump by name  [K] Kill
  [L] Log tail  [A] Adopt orphans  [R] Refresh  [Q] Quit/detach
```

### Dashboard key bindings

| Key | Action |
|-----|--------|
| `1`–`9` | Switch to that window |
| `N` | New Claude session (directory picker menu) |
| `J` | Jump to session by name (fuzzy) |
| `K` | Kill session gracefully |
| `L` | Tail session transcript in a popup |
| `A` | Adopt orphan sessions |
| `R` | Force refresh |
| `Q` | Detach from CSM (sessions keep running) |

Standard tmux bindings also work: `prefix + [n]` to switch windows, `prefix + w` for choose-tree.

## Per-project configuration

Create `.csmrc` in your repo root (CSM walks up the tree to find it):

```ini
# .csmrc — auto-applied when opening this project with csm new
kube_context=cgk8s-dev-cluster
aws_profile=hyp-creditguard
```

When you run `csm new ~/your/repo`, CSM will:
1. `kubectl config use-context cgk8s-dev-cluster`
2. `export AWS_PROFILE=hyp-creditguard`
3. Then launch `claude`

Claude's Bash tool calls will inherit these — so `kubectl get pods` and `aws s3 ls` hit the right cluster and account automatically.

## Notifications

To enable desktop notifications when a session finishes or needs input:

```bash
# Start the notifier in the background (add to ~/.zshrc)
csm-notify &
```

On WSL2, install [wsl-notify-send](https://github.com/stuartleeks/wsl-notify-send) for Windows toast notifications. Otherwise `libnotify-bin` is used.

## How it works

- All sessions run inside a single tmux session named `csm`
- Window 0 is always the dashboard
- Windows 1+ are individual Claude Code sessions
- Session state is read live from `~/.claude/sessions/*.json` (written by Claude Code)
- With `inotify-tools` installed, the dashboard refreshes instantly on any state change
- CSM state and audit log live in `~/.local/state/csm/`

## Upgrading

```bash
git pull && bash install.sh
```

## Requirements

- tmux ≥ 3.0
- Python 3.6+
- zsh (or bash 4+)
- Claude Code CLI (`claude`)
- WSL2, Linux, or macOS
