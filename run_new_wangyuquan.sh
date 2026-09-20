#!/bin/zsh

set -u

TASK_NAME="王昱全视频拆解（新增4个文件）"
TOOL_DIR="/Users/macsg/Documents/本地视频转写工具"
INPUT_DIR="/Users/macsg/Downloads/王昱全"
OUTPUT_DIR="/Users/macsg/Downloads/王煜全语料库/王昱全"
NOTIFY_DIR="/Users/macsg/Documents/Codex任务通知"
LOG_DIR="/Users/macsg/Downloads/王煜全语料库/_logs"
LOG_PATH="$LOG_DIR/new_wangyuquan_20260727.log"

mkdir -p "$LOG_DIR"

/usr/bin/caffeinate -i "$TOOL_DIR/.venv/bin/python" "$TOOL_DIR/transcribe.py" \
  --input "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --model auto \
  >>"$LOG_PATH" 2>&1
STATUS=$?

if [[ $STATUS -eq 0 ]]; then
  cd "$NOTIFY_DIR"
  node task-notify.mjs complete \
    --task "$TASK_NAME" \
    --detail "本次已到位视频转写完成，已生成 raw.txt、srt、md、json" \
    --path "$OUTPUT_DIR" >>"$LOG_PATH" 2>&1
else
  cd "$NOTIFY_DIR"
  node task-notify.mjs blocked \
    --task "$TASK_NAME" \
    --detail "本地转写失败，请查看日志：$LOG_PATH" >>"$LOG_PATH" 2>&1
fi

exit $STATUS
