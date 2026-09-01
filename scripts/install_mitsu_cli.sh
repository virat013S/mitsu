#!/usr/bin/env bash
# Install the `mitsu` command for the current macOS/Linux user.
set -e

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
PROJECT_ROOT="$(cd -P "$(dirname "$SOURCE")/.." >/dev/null 2>&1 && pwd)"
INSTALL_DIR="${MITSU_INSTALL_DIR:-$HOME/.local/bin}"
mkdir -p "$INSTALL_DIR"
ln -sfn "$PROJECT_ROOT/scripts/mitsu" "$INSTALL_DIR/mitsu"

PROFILE=""
if [ "$(basename "${SHELL:-}")" = "zsh" ]; then
  PROFILE="$HOME/.zprofile"
elif [ "$(basename "${SHELL:-}")" = "bash" ]; then
  PROFILE="$HOME/.bash_profile"
fi
if [ -n "$PROFILE" ] && ! grep -Fq 'MITSU_INSTALL_DIR' "$PROFILE" 2>/dev/null; then
  if ! printf '\n# MITSU CLI\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$PROFILE" 2>/dev/null; then
    echo "Could not update $PROFILE automatically; add $INSTALL_DIR to PATH manually."
  fi
fi

echo "Installed: $INSTALL_DIR/mitsu"
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  echo "Open a new terminal, or run: export PATH=\"$INSTALL_DIR:\$PATH\""
fi
echo "Then launch MITSU with: mitsu"
