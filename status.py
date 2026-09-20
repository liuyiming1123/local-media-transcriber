#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

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
    pid = 0
    if PID_PATH.exists():
        try:
            pid = int(PID_PATH.read_text(encoding="utf-8").strip())
        except ValueError:
            pass
    completed = []
    for path in OUTPUT_DIR.rglob("*.json"):
        if LOG_DIR in path.parents:
            continue
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("status") == "success":
                completed.append(path)
        except Exception:
            continue
    print(f"运行状态：{'运行中' if pid and is_running(pid) else '未运行'}")
    print(f"PID：{pid or '—'}")
    print(f"成功文件：{len(completed)} / 8")
    print(f"输出目录：{OUTPUT_DIR}")
    if LOG_PATH.exists():
        print("\n最近日志：")
        print("".join(LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)[-20:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
