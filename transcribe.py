#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".m4v", ".ts", ".mp3", ".m4a", ".wav"}
DEFAULT_INPUT = Path.home() / "Documents" / "王煜全视频"
DEFAULT_OUTPUT = Path.home() / "Documents" / "王煜全语料库"
TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_TERMINOLOGY = TOOL_DIR / "terminology.txt"
MODEL_FALLBACKS = {
    "auto": ["large-v3-turbo", "medium"],
    "large-v3": ["large-v3", "large-v3-turbo", "medium"],
    "large-v3-turbo": ["large-v3-turbo", "medium"],
    "medium": ["medium"],
}


@dataclass
class TranscriptSegment:
    id: int
    start: float
    end: float
    text: str
    avg_logprob: float | None
    no_speech_prob: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="递归批量生成中文逐字稿、SRT、Markdown和JSON")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="输入文件或目录")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="输出目录")
    parser.add_argument("--model", choices=MODEL_FALLBACKS, default="auto", help="模型；auto适合8GB Mac")
    parser.add_argument("--test-one", action="store_true", help="只处理时长最短的一个文件")
    parser.add_argument("--force", action="store_true", help="忽略成功标记并重新转写")
    parser.add_argument("--terminology", type=Path, default=DEFAULT_TERMINOLOGY, help="术语词表")
    parser.add_argument("--cpu-threads", type=int, default=6, help="CPU线程数")
    parser.add_argument("--beam-size", type=int, default=5, help="束搜索大小；越大通常越准但越慢")
    return parser.parse_args()


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def require_commands() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"缺少命令：{', '.join(missing)}。请先运行 brew install ffmpeg")


def scan_media(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path.resolve()] if input_path.suffix.lower() in SUPPORTED_EXTENSIONS else []
    if not input_path.exists():
        return []
    return sorted(
        (path.resolve() for path in input_path.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda path: str(path).lower(),
    )


def probe_duration(path: Path) -> float:
    result = run_command([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(result.stdout.strip())


def format_clock(seconds: float, srt: bool = False) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    separator = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def format_duration(seconds: float) -> str:
    total = max(0, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def read_terminology(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def relative_source_path(source: Path, input_path: Path) -> Path:
    if input_path.is_file():
        return Path(source.name)
    return source.relative_to(input_path.resolve())


def output_paths(source: Path, input_path: Path, output_root: Path) -> dict[str, Path]:
    relative = relative_source_path(source, input_path)
    base = output_root / relative.parent / relative.stem
    return {
        "raw": Path(f"{base}.raw.txt"),
        "srt": Path(f"{base}.srt"),
        "markdown": Path(f"{base}.md"),
        "metadata": Path(f"{base}.json"),
    }


def source_fingerprint(source: Path) -> dict[str, int | str]:
    stat = source.stat()
    return {"path": str(source), "size_bytes": stat.st_size, "modified_ns": stat.st_mtime_ns}


def is_complete(paths: dict[str, Path], source: Path) -> bool:
    if not all(path.exists() and path.stat().st_size > 0 for path in paths.values()):
        return False
    try:
        metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return metadata.get("status") == "success" and metadata.get("source") == source_fingerprint(source)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def extract_audio(source: Path, target: Path) -> None:
    run_command([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", str(target),
    ])


def load_model(requested: str, cpu_threads: int):
    from faster_whisper import WhisperModel

    errors: list[str] = []
    for model_name in MODEL_FALLBACKS[requested]:
        try:
            print(f"  正在加载模型：{model_name}（CPU int8）", flush=True)
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                cpu_threads=max(1, cpu_threads),
                num_workers=1,
            )
            return model, model_name
        except Exception as error:
            errors.append(f"{model_name}: {type(error).__name__}: {error}")
            print(f"  模型加载失败，尝试降级：{errors[-1]}", file=sys.stderr, flush=True)
    raise RuntimeError("所有模型均加载失败；" + " | ".join(errors))


def transcribe_audio(model, audio_path: Path, terms: list[str], beam_size: int):
    vocabulary = "、".join(terms)
    prompt = f"以下是王煜全关于科技、投资和产业创新的中文演讲。请准确识别专有名词：{vocabulary}" if vocabulary else None
    segment_iterator, info = model.transcribe(
        str(audio_path),
        language="zh",
        task="transcribe",
        beam_size=max(1, beam_size),
        best_of=max(1, beam_size),
        temperature=[0.0, 0.2, 0.4, 0.6],
        compression_ratio_threshold=2.2,
        repetition_penalty=1.05,
        initial_prompt=prompt,
        hotwords=vocabulary or None,
        condition_on_previous_text=False,
        vad_filter=False,
        word_timestamps=True,
        hallucination_silence_threshold=2.0,
    )
    segments = [
        TranscriptSegment(
            id=index,
            start=float(segment.start),
            end=float(segment.end),
            text=segment.text,
            avg_logprob=float(segment.avg_logprob) if segment.avg_logprob is not None else None,
            no_speech_prob=float(segment.no_speech_prob) if segment.no_speech_prob is not None else None,
        )
        for index, segment in enumerate(segment_iterator, start=1)
    ]
    return segments, info


def raw_text(segments: list[TranscriptSegment]) -> str:
    return "".join(segment.text for segment in segments).strip() + "\n"


def srt_text(segments: list[TranscriptSegment]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(f"{index}\n{format_clock(segment.start, True)} --> {format_clock(segment.end, True)}\n{segment.text.strip()}")
    return "\n\n".join(blocks) + "\n"


def markdown_text(source: Path, duration: float, transcribed_at: str, model_name: str, segments: list[TranscriptSegment]) -> str:
    lines = [
        f"# {source.stem}", "",
        f"- 视频标题：{source.stem}",
        f"- 原始文件名：{source.name}",
        f"- 视频时长：{format_duration(duration)}",
        f"- 转写日期：{transcribed_at}",
        f"- 使用模型：{model_name}",
        "- 语言：中文", "",
        "## 带时间戳逐字稿", "",
    ]
    lines.extend(f"[{format_clock(segment.start)} --> {format_clock(segment.end)}] {segment.text}" for segment in segments)
    return "\n".join(lines).rstrip() + "\n"


def append_json_line(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


def process_file(source: Path, input_path: Path, output_root: Path, model, model_name: str, terms: list[str], beam_size: int) -> dict:
    paths = output_paths(source, input_path, output_root)
    started = time.monotonic()
    duration = probe_duration(source)
    with tempfile.TemporaryDirectory(prefix="wang-yuquan-transcribe-") as temporary_dir:
        audio_path = Path(temporary_dir) / "audio.flac"
        extract_audio(source, audio_path)
        segments, info = transcribe_audio(model, audio_path, terms, beam_size)
    if not segments:
        raise RuntimeError("未识别到任何语音片段")
    transcribed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    metadata = {
        "status": "success",
        "title": source.stem,
        "source": source_fingerprint(source),
        "duration_seconds": duration,
        "transcribed_at": transcribed_at,
        "model": model_name,
        "device": "cpu",
        "compute_type": "int8",
        "language": getattr(info, "language", "zh"),
        "language_probability": getattr(info, "language_probability", None),
        "segment_count": len(segments),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "terminology": terms,
        "segments": [asdict(segment) for segment in segments],
    }
    atomic_write(paths["raw"], raw_text(segments))
    atomic_write(paths["srt"], srt_text(segments))
    atomic_write(paths["markdown"], markdown_text(source, duration, transcribed_at, model_name, segments))
    atomic_write(paths["metadata"], json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return metadata


def shortest_first(files: Iterable[Path]) -> list[Path]:
    measured = []
    for path in files:
        try:
            measured.append((probe_duration(path), path))
        except Exception:
            measured.append((float("inf"), path))
    return [path for _, path in sorted(measured, key=lambda item: (item[0], str(item[1])))]


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_root = args.output.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    logs_dir = output_root / "_logs"
    failures_path = logs_dir / "failures.jsonl"
    require_commands()
    files = scan_media(input_path)
    if not files:
        print(f"没有找到媒体文件：{input_path}", file=sys.stderr)
        print("支持：mp4、mov、mkv、m4v、ts、mp3、m4a、wav", file=sys.stderr)
        return 2
    if args.test_one:
        files = shortest_first(files)[:1]
        print(f"测试模式：选择最短文件 {files[0].name}")
    pending = []
    for source in files:
        paths = output_paths(source, input_path, output_root)
        if not args.force and is_complete(paths, source):
            print(f"跳过已完成：{source}")
        else:
            pending.append(source)
    if not pending:
        print("全部文件已经成功转写，无需重复处理。")
        return 0
    terms = read_terminology(args.terminology.expanduser())
    model, model_name = load_model(args.model, args.cpu_threads)
    succeeded = 0
    failed = 0
    print(f"待处理 {len(pending)} 个文件；模型 {model_name}；术语 {len(terms)} 个")
    for index, source in enumerate(pending, start=1):
        print(f"[{index}/{len(pending)}] {source}", flush=True)
        try:
            result = process_file(source, input_path, output_root, model, model_name, terms, args.beam_size)
            succeeded += 1
            print(f"  完成：{result['segment_count']} 段，用时 {result['elapsed_seconds']} 秒", flush=True)
        except Exception as error:
            failed += 1
            failure = {
                "status": "failed",
                "source": str(source),
                "failed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "model": model_name,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
            append_json_line(failures_path, failure)
            print(f"  失败：{type(error).__name__}: {error}", file=sys.stderr, flush=True)
    summary = {
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "input": str(input_path),
        "output": str(output_root),
        "model": model_name,
        "total_pending": len(pending),
        "succeeded": succeeded,
        "failed": failed,
        "python": platform.python_version(),
    }
    atomic_write(logs_dir / "last_run.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"本次完成：成功 {succeeded}，失败 {failed}。输出：{output_root}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
