#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
INPUT_DIR = Path.home() / "Documents" / "王煜全视频"
OUTPUT_DIR = Path.home() / "Documents" / "王煜全语料库"
LOG_DIR = OUTPUT_DIR / "_logs"
PID_PATH = LOG_DIR / "batch.pid"
LOG_PATH = LOG_DIR / "batch.log"


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if PID_PATH.exists():
        try:
            old_pid = int(PID_PATH.read_text(encoding="utf-8").strip())
        except ValueError:
            old_pid = 0
        if old_pid and is_running(old_pid):
            print(f"批量任务已经运行，PID {old_pid}")
            print(f"日志：{LOG_PATH}")
            return 0
    python = TOOL_DIR / ".venv" / "bin" / "python"
    command = [
        "/usr/bin/caffeinate", "-i", str(python), str(TOOL_DIR / "transcribe.py"),
        "--input", str(INPUT_DIR), "--output", str(OUTPUT_DIR), "--model", "auto",
    ]
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(f"\n=== 启动 {datetime.now().astimezone().isoformat(timespec='seconds')} ===\n")
        log.flush()
        process = subprocess.Popen(
            command,
            cwd=TOOL_DIR,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PID_PATH.write_text(str(process.pid), encoding="utf-8")
    state = {"pid": process.pid, "started_at": datetime.now().astimezone().isoformat(timespec="seconds"), "command": command, "log": str(LOG_PATH)}
    (LOG_DIR / "batch_start.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"批量任务已启动，PID {process.pid}")
    print(f"日志：{LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
