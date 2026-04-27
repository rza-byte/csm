#!/usr/bin/env bash
# csm-notify — watch ~/.claude/sessions/ and alert on state changes
# Run in background: csm-notify &
# Or add to your shell startup to auto-launch with CSM.

set -euo pipefail

CLAUDE_SESSIONS="${HOME}/.claude/sessions"
CSM_LIB_DIR="${CSM_LIB_DIR:-$HOME/.local/share/csm/lib}"

# Send a notification through the best available channel
_notify() {
    local title="$1" body="$2"
    if command -v wsl-notify-send &>/dev/null; then
        # Windows toast via wsl-notify-send (https://github.com/stuartleeks/wsl-notify-send)
        wsl-notify-send -a "CSM" "${title}: ${body}" 2>/dev/null || true
    elif command -v notify-send &>/dev/null; then
        notify-send "CSM: $title" "$body" -t 6000 -i terminal 2>/dev/null || true
    elif [[ -n "${TMUX:-}" ]]; then
        # Fallback: show in tmux status area for 4 seconds
        tmux display-message -d 4000 "CSM ▸ ${title}: ${body}" 2>/dev/null || true
    fi
}

# Check sessions and emit notifications for status transitions
declare -A _prev_status

_check_changes() {
    while IFS=$'\t' read -r pid alive st _cwd project _age; do
        [[ "$alive" != "True" ]] && continue
        local prev="${_prev_status[$pid]:-}"
        if [[ -n "$prev" ]] && [[ "$prev" != "$st" ]]; then
            case "$st" in
                idle)
                    _notify "$project" "finished — now idle" ;;
                waiting)
                    _notify "$project" "waiting for your input" ;;
                busy)
                    : ;; # don't alert on busy
            esac
        fi
        _prev_status["$pid"]="$st"
    done < <(python3 "$CSM_LIB_DIR/csm-status.py" sessions 2>/dev/null)
}

# Initial snapshot (no notifications, just populate prev state)
while IFS=$'\t' read -r pid alive st _; do
    [[ "$alive" == "True" ]] && _prev_status["$pid"]="$st"
done < <(python3 "$CSM_LIB_DIR/csm-status.py" sessions 2>/dev/null)

echo "csm-notify: watching ${CLAUDE_SESSIONS}"

if command -v inotifywait &>/dev/null; then
    inotifywait -m "$CLAUDE_SESSIONS" -e modify,create,delete -q --format '%f' 2>/dev/null | \
    while read -r _changed_file; do
        _check_changes
    done
else
    echo "csm-notify: inotifywait not found, falling back to 5s polling"
    echo "           Install for real-time alerts: sudo apt install inotify-tools"
    while true; do
        sleep 5
        _check_changes
    done
fi
