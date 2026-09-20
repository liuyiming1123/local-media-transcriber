#!/bin/zsh
set -e
TOOL_DIR="${0:A:h}"
INPUT_PATH="${1:-$HOME/Documents/王煜全视频}"
OUTPUT_PATH="$HOME/Documents/王煜全语料库"
cd "$TOOL_DIR"
if [[ ! -x .venv/bin/python ]]; then
  echo "尚未安装，请先双击 install.command"
  read "?按回车关闭..."
  exit 1
fi
.venv/bin/python transcribe.py --input "$INPUT_PATH" --output "$OUTPUT_PATH" --model auto --test-one
echo "测试结束。输出目录：$OUTPUT_PATH"
read "?按回车关闭..."

