# 王煜全视频本地批量转写工具

把输入目录内的 MP4、MOV、MKV、M4V、TS、MP3、M4A、WAV 媒体文件递归转换到语料库。音视频和逐字稿均保留在本机，不使用云端转写 API。

## 输出

每个媒体文件生成：

- `文件名.raw.txt`：不润色的连续原始逐字稿
- `文件名.srt`：带分段时间戳的字幕
- `文件名.md`：适合大模型读取的元数据和时间戳逐字稿
- `文件名.json`：来源指纹、模型、耗时、语言概率和结构化分段

输入存在子目录时，输出保留相同目录结构，避免同名视频互相覆盖。

## 安装

当前机器已安装 ffmpeg 和 uv。首次安装可双击 `install.command`，或运行：

```bash
cd ~/Documents/本地视频转写工具
uv sync --locked
```

模型在第一次转写时从 Hugging Face 下载。`large-v3` 约3GB；请保持网络和磁盘空间充足。

## 推荐使用顺序

1. 把至少一个视频放入 `~/Documents/王煜全视频`。
2. 双击 `1_测试一个视频.command`，程序自动选择最短文件。
3. 检查四种输出以及专有名词准确率。
4. 测试通过后双击 `2_批量转写全部.command`。

本机首次测试已经通过，也可以用下面的后台方式运行全部视频：

```bash
.venv/bin/python start_background.py
.venv/bin/python status.py
```

后台任务通过 `caffeinate` 防止Mac空闲睡眠，日志写入 `~/Documents/王煜全语料库/_logs/batch.log`。可以双击 `3_查看批量进度.command` 查看进度。合上屏幕、关机或主动睡眠仍会暂停任务。

也可以把任意视频文件或文件夹拖到两个 `.command` 文件上。拖拽只改变本次输入，输出仍进入 `~/Documents/王煜全语料库`。

## 命令行

```bash
# 8GB Mac推荐：large-v3-turbo，失败时降级medium
.venv/bin/python transcribe.py --test-one --model auto

# 强制尝试最高准确率；加载失败则依次降级
.venv/bin/python transcribe.py --test-one --model large-v3

# 测试通过后全量处理
.venv/bin/python transcribe.py --model auto

# 重新转写已经完成的文件
.venv/bin/python transcribe.py --model auto --force
```

## 断点续传

程序只有在 `.raw.txt`、`.srt`、`.md`、`.json` 全部存在，且 JSON 中的源文件大小和修改时间仍匹配时才跳过。源视频发生变化会自动重新转写。

失败记录写入：

```text
~/Documents/王煜全语料库/_logs/failures.jsonl
```

最近一次运行汇总写入 `_logs/last_run.json`。

## 术语维护

直接编辑 `terminology.txt`，每行一个词。术语会同时进入初始提示和 hotwords，但语音模型仍可能识别错误，重要内容需人工抽查。

## 常见错误

- `没有找到媒体文件`：确认视频已经从百度网盘下载到输入目录，而不是仅存在云端。
- `缺少 ffmpeg`：运行 `brew install ffmpeg`。
- 模型下载失败：检查网络后重试；已下载部分会复用缓存。
- 内存不足或非常慢：使用 `--model auto` 或 `--model medium`，关闭其他占内存应用并连接电源。
- 没有音轨：程序会记录 ffmpeg 错误，不会生成成功标记。
- 术语识别错误：补充 `terminology.txt` 后使用 `--force` 重新转写。
- macOS阻止 `.command`：在Finder中右键文件选择“打开”；本工具仅运行本地Python脚本。

## 准确率说明

这台机器是8GB M3 MacBook Air。`faster-whisper` 在macOS使用CPU int8，并不直接使用Apple神经网络引擎。`large-v3`准确率优先但可能很慢；默认 `auto` 使用 `large-v3-turbo`，是更现实的速度和内存平衡。逐字稿不会自动润色，仍建议抽查专业术语、数字和人名。

程序保留真实口语重复，但启用了温度回退、压缩率检查和静音幻觉检测，避免把模型卡住后生成的机械循环误当成原话。
