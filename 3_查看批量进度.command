#!/bin/zsh
TOOL_DIR="${0:A:h}"
cd "$TOOL_DIR"
.venv/bin/python status.py
read "?按回车关闭..."

