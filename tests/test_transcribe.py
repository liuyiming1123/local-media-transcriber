import json
import tempfile
import unittest
from pathlib import Path

from transcribe import format_clock, is_complete, output_paths, scan_media, source_fingerprint


class TranscriberTests(unittest.TestCase):
    def test_timestamp_formats(self):
        self.assertEqual(format_clock(3661.234, srt=False), "01:01:01.234")
        self.assertEqual(format_clock(3661.234, srt=True), "01:01:01,234")

    def test_recursive_scan_and_supported_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sub").mkdir()
            (root / "a.MP4").write_bytes(b"x")
            (root / "sub" / "b.m4a").write_bytes(b"x")
            (root / "ignore.txt").write_bytes(b"x")
            self.assertEqual([path.name for path in scan_media(root)], ["a.MP4", "b.m4a"])

    def test_relative_outputs_prevent_same_name_collision(self):
        root = Path("/input")
        first = output_paths(root / "one" / "lesson.v1.mp4", root, Path("/output"))
        second = output_paths(root / "two" / "lesson.mp4", root, Path("/output"))
        self.assertNotEqual(first["metadata"], second["metadata"])
        self.assertEqual(first["raw"].name, "lesson.v1.raw.txt")

    def test_completion_requires_all_outputs_and_matching_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "video.mp4"
            source.write_bytes(b"video")
            output = root / "output"
            paths = output_paths(source, source, output)
            for key, path in paths.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                if key == "metadata":
                    path.write_text(json.dumps({"status": "success", "source": source_fingerprint(source)}), encoding="utf-8")
                else:
                    path.write_text("ok", encoding="utf-8")
            self.assertTrue(is_complete(paths, source))
            source.write_bytes(b"changed")
            self.assertFalse(is_complete(paths, source))


if __name__ == "__main__":
    unittest.main()
