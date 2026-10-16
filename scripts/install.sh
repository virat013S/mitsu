#!/bin/sh
# Runs in ANY shell (bash/zsh/fish/POSIX sh). The real installer is python:
exec python3 "$(dirname "$0")/install.py" "$@"
