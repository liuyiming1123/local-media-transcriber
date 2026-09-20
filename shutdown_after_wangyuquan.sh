#!/bin/zsh

set -u

OUTPUT_BASE="/Users/macsg/Downloads/王煜全语料库/王昱全/【第7季-第9期】国产算力产业链扫描"
NOTIFY_DIR="/Users/macsg/Documents/Codex任务通知"
WATCH_LOG="/Users/macsg/Downloads/王煜全语料库/_logs/shutdown_after_wangyuquan.log"

while true; do
  if [[ -s "$OUTPUT_BASE.raw.txt" && -s "$OUTPUT_BASE.srt" && -s "$OUTPUT_BASE.md" && -s "$OUTPUT_BASE.json" ]]; then
    if /usr/bin/grep -q '"status": "success"' "$OUTPUT_BASE.json"; then
      break
    fi
  fi
  /bin/sleep 30
done

cd "$NOTIFY_DIR"
node task-notify.mjs complete \
  --task "王昱全视频拆解后自动关机" \
  --detail "转写四项产物已验证完成，电脑将在60秒后自动关机" \
  --path "/Users/macsg/Downloads/王煜全语料库/王昱全" >>"$WATCH_LOG" 2>&1

/bin/sleep 60
/usr/bin/osascript -e 'tell application "System Events" to shut down' >>"$WATCH_LOG" 2>&1
