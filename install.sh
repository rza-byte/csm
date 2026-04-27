#!/usr/bin/env bash
# CSM installer
set -euo pipefail

INSTALL_BIN="${HOME}/.local/bin"
INSTALL_LIB="${HOME}/.local/share/csm/lib"
GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; GREY=$'\033[0;90m'; RESET=$'\033[0m'; BOLD=$'\033[1m'

echo
echo "${BOLD}Installing CSM — Claude Session Manager${RESET}"
echo

mkdir -p "$INSTALL_BIN" "$INSTALL_LIB"

install -m 755 csm "$INSTALL_BIN/csm"
echo "  ${GREEN}✓${RESET} csm  →  $INSTALL_BIN/csm"

for f in lib/*.py lib/*.sh; do
    [[ -f "$f" ]] || continue
    install -m 755 "$f" "$INSTALL_LIB/"
    echo "  ${GREEN}✓${RESET} $(basename "$f")  →  $INSTALL_LIB/"
done

# PATH check
if ! echo ":${PATH}:" | grep -q ":${INSTALL_BIN}:"; then
    echo
    echo "  ${YELLOW}⚠${RESET}  $INSTALL_BIN is not in your PATH."
    echo "     Add to ~/.zshrc:  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo
echo "  ${BOLD}Optional dependencies:${RESET}"
for dep in fzf inotifywait notify-send; do
    if command -v "$dep" &>/dev/null; then
        printf "  ${GREEN}✓${RESET} %-16s installed\n" "$dep"
    else
        printf "  ${GREY}-${RESET} %-16s not installed\n" "$dep"
    fi
done

echo
echo "  Install all optionals:  sudo apt install fzf inotify-tools libnotify-bin"
echo
echo "  ${GREEN}Done!${RESET}  Run: ${BOLD}csm${RESET}"
echo
