#!/bin/zsh
set -e
TOOL_DIR="${0:A:h}"
cd "$TOOL_DIR"
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "缺少 ffmpeg，请先安装 Homebrew 后运行：brew install ffmpeg"
  read "?按回车关闭..."
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "缺少 uv，请运行：brew install uv"
  read "?按回车关闭..."
  exit 1
fi
uv sync --locked
echo "安装完成。"
read "?按回车关闭..."
