#!/usr/bin/env python3
"""Tests for frames2text: the storage rule, the converters' framing and playback.

Run: python3 -I tools/frames2text/test_frames2text.py
(the chafa, img2txt and tmux tests are skipped when the tool is not installed)
"""

import contextlib
import io
import json
import os
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import frames2text as f2t  # noqa: E402

SCRIPT = os.path.join(HERE, "frames2text.py")
SCENES = os.path.join(HERE, "scenes", "starship_flight15.toml")
COLS, ROWS = 137, 33


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd, "-c", "user.email=t@example.invalid", "-c", "user.name=t",
                    *args], check=True, capture_output=True)


def gradient(cols, height):
    return b"".join(bytes(((x * 255) // cols, (y * 255) // height, 128))
                    for y in range(height) for x in range(cols))


class TempRepo(unittest.TestCase):
    """A temp git repo with a tracked dir, an ignored dir and a second temp root."""

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="f2t-test-"))
        self.repo = os.path.join(self.base, "repo")
        os.makedirs(os.path.join(self.repo, "tracked"))
        git(self.repo, "init", "-q")
        with open(os.path.join(self.repo, ".gitignore"), "w") as f:
            f.write("/ignored/\n")
        with open(os.path.join(self.repo, "tracked", "file.txt"), "w") as f:
            f.write("tracked\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")
        self.outside = os.path.join(self.base, "outside")  # not a repo
        os.makedirs(self.outside)
        self.other_root = os.path.realpath(tempfile.mkdtemp(prefix="f2t-root-"))

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)
        shutil.rmtree(self.other_root, ignore_errors=True)


class StorageRuleTest(TempRepo):
    def test_refuses_tracked_dir(self):
        with self.assertRaises(f2t.DestError):
            f2t.check_dest(os.path.join(self.repo, "tracked"))
        with self.assertRaises(f2t.DestError):
            f2t.check_dest(os.path.join(self.repo, "tracked", "new"))

    def test_refuses_unignored_new_dir(self):
        with self.assertRaises(f2t.DestError):
            f2t.check_dest(os.path.join(self.repo, "scratch"))

    def test_accepts_ignored_dir(self):
        d = os.path.join(self.repo, "ignored", "starship")
        self.assertEqual(f2t.check_dest(d), d)
        w = f2t.SafeWriter()
        w.ensure_dir(d)
        w.write_text(os.path.join(d, "x.ans"), "ok")
        self.assertTrue(os.path.isfile(os.path.join(d, "x.ans")))

    def test_refuses_symlink_from_ignored_into_tracked(self):
        os.makedirs(os.path.join(self.repo, "ignored"))
        link = os.path.join(self.repo, "ignored", "link")
        os.symlink(os.path.join(self.repo, "tracked"), link)
        with self.assertRaises(f2t.DestError):
            f2t.check_dest(link)
        with self.assertRaises(f2t.DestError):
            f2t.SafeWriter().write_text(os.path.join(link, "x.ans"), "leak")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "tracked", "x.ans")))

    def test_refuses_replacing_an_existing_symlink(self):
        d = os.path.join(self.repo, "ignored")
        os.makedirs(d)
        target = os.path.join(self.repo, "tracked", "file.txt")
        os.symlink(target, os.path.join(d, "00000.ans"))
        w = f2t.SafeWriter()
        w.ensure_dir(d)
        with self.assertRaises(f2t.DestError):
            w.write_text(os.path.join(d, "00000.ans"), "leak")
        with open(target) as f:
            self.assertEqual(f.read(), "tracked\n")

    def test_refuses_ignored_dir_holding_a_force_added_file(self):
        d = os.path.join(self.repo, "ignored")
        os.makedirs(d)
        with open(os.path.join(d, "forced.txt"), "w") as f:
            f.write("x")
        git(self.repo, "add", "-f", "ignored/forced.txt")
        with self.assertRaises(f2t.DestError):
            f2t.check_dest(d)

    def test_reused_writer_rechecks_every_write(self):
        # Review finding: a writer must not cache a directory's eligibility.
        d = os.path.join(self.repo, "ignored")
        w = f2t.SafeWriter()
        w.ensure_dir(d)
        path = os.path.join(d, "00000.ans")
        w.write_text(path, "first")
        git(self.repo, "add", "-f", "ignored/00000.ans")
        with self.assertRaises(f2t.DestError):
            w.write_text(path, "second")
        with open(path) as f:
            self.assertEqual(f.read(), "first")
        with self.assertRaises(f2t.DestError):
            w.remove(path)
        self.assertTrue(os.path.exists(path))

    def test_reused_writer_sees_gitignore_changes(self):
        d = os.path.join(self.repo, "ignored")
        w = f2t.SafeWriter()
        w.ensure_dir(d)
        w.write_text(os.path.join(d, "a.ans"), "ok")
        with open(os.path.join(self.repo, ".gitignore"), "w") as f:
            f.write("")  # un-ignore it
        with self.assertRaises(f2t.DestError):
            w.write_text(os.path.join(d, "b.ans"), "no longer ignored")

    def test_refuses_git_dir(self):
        with self.assertRaises(f2t.DestError):
            f2t.check_dest(os.path.join(self.repo, ".git", "frames"))

    def test_accepts_temp_dir_outside_any_repo(self):
        d = os.path.join(self.outside, "frames")
        self.assertEqual(f2t.check_dest(d, temp_root=self.base), d)

    def test_refuses_outside_repo_non_temp_dir(self):
        with self.assertRaises(f2t.DestError):
            f2t.check_dest(os.path.join(self.outside, "frames"), temp_root=self.other_root)

    def test_cli_refuses_tracked_out(self):
        res = subprocess.run([sys.executable, "-I", SCRIPT, "convert", "--out",
                              os.path.join(self.repo, "tracked")], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("refused", res.stderr)


@unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg not installed")
class ExtractConvertTest(TempRepo):
    """End-to-end on a tiny synthetic video, in a temp dir outside any repo."""

    def setUp(self):
        super().setUp()
        self.video = os.path.join(self.outside, "v.mp4")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc=size=160x90:rate=10:duration=4", "-pix_fmt", "yuv420p", self.video],
                       check=True)
        self.out = os.path.join(self.outside, "out")
        self.writer = f2t.SafeWriter(temp_root=self.base)

    def scenes(self, body):
        p = os.path.join(self.outside, "scenes.toml")
        with open(p, "w") as f:
            f.write(body)
        return p

    TWO = ('[[scene]]\nname = "a"\nstart = 0\nend = 1\nspeed = 1\n'
           '[[scene]]\nname = "b"\nstart = 1\nend = 3\nspeed = 2\n')

    def extract(self, scenes, video=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return f2t.extract(video or self.video, scenes, self.out, 8, 4, 10.0, self.writer)

    def convert(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return f2t.convert(self.out, "halfblock", self.writer, jobs=2)

    def manifest(self):
        with open(os.path.join(self.out, f2t.MANIFEST)) as f:
            return json.load(f)

    def files(self):
        return sorted(os.path.relpath(os.path.join(r, n), self.out)
                      for r, _, ns in os.walk(self.out) for n in ns)

    def test_extract_and_convert(self):
        self.extract(self.scenes(self.TWO))
        self.convert()
        m = self.manifest()
        self.assertEqual(m["converter"], "halfblock")
        self.assertEqual([len(s["frames"]) for s in m["scenes"]], [10, 10])
        for _, d, stem in f2t.iter_frames(m):
            with open(os.path.join(self.out, d, stem + ".ans"), encoding="utf-8") as f:
                self.assertEqual(f2t.normalize_frame(f.read(), 4, 8).count("\n"), 3)
        self.assertFalse(any(p.startswith(f2t.STAGING_PREFIX) for p in os.listdir(self.out)))

    def test_failed_extract_keeps_previous_output(self):
        # Review finding: a failed re-extract must not delete the previous frames.
        self.extract(self.scenes(self.TWO))
        self.convert()
        before_files, before_manifest = self.files(), self.manifest()
        bad = os.path.join(self.outside, "bad.mp4")
        with open(bad, "w") as f:
            f.write("not a video")
        with self.assertRaises(ValueError):
            self.extract(self.scenes(self.TWO), video=bad)
        self.assertEqual(self.files(), before_files)
        self.assertEqual(self.manifest(), before_manifest)
        # a scene past the end of the video fails too, after earlier scenes succeeded
        with self.assertRaises(ValueError):
            self.extract(self.scenes(self.TWO + '[[scene]]\nname = "c"\nstart = 60\nend = 61\nspeed = 1\n'))
        self.assertEqual(self.files(), before_files)
        self.assertEqual(self.manifest(), before_manifest)

    def test_reextract_replaces_old_scenes(self):
        self.extract(self.scenes(self.TWO))
        self.convert()
        self.extract(self.scenes('[[scene]]\nname = "only"\nstart = 0\nend = 2\nspeed = 1\n'))
        m = self.manifest()
        self.assertIsNone(m["converter"])
        self.assertEqual([s["dir"] for s in m["scenes"]], ["01_only"])
        self.assertEqual(sorted(os.listdir(self.out)), ["01_only", f2t.MANIFEST])
        self.assertFalse(any(n.endswith(".ans") for n in os.listdir(os.path.join(self.out, "01_only"))))

    def test_failed_convert_leaves_manifest_unconverted(self):
        self.extract(self.scenes(self.TWO))
        self.convert()
        os.unlink(os.path.join(self.out, "02_b", "00005.rgb"))
        with self.assertRaises(ValueError):
            self.convert()
        self.assertIsNone(self.manifest()["converter"])
        res = subprocess.run([sys.executable, "-I", SCRIPT, "play", "--out", self.out],
                             capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("not converted", res.stderr)


class PlayArgsTest(unittest.TestCase):
    def test_cli_rejects_bad_fps_before_drawing(self):
        # Review finding: --fps -10 used to skip almost every frame, --fps 0 used the manifest rate.
        for bad in ("-10", "0", "nan", "inf", "x"):
            with self.subTest(fps=bad):
                res = subprocess.run([sys.executable, "-I", SCRIPT, "play", "--out", tempfile.gettempdir(),
                                      "--fps", bad], capture_output=True)
                self.assertEqual(res.returncode, 2)
                self.assertIn(b"--fps", res.stderr)
                self.assertEqual(res.stdout, b"")  # never entered the alternate screen

    def test_play_rejects_bad_fps(self):
        for bad in (-10, 0, float("nan"), float("inf")):
            with self.subTest(fps=bad), self.assertRaises(ValueError):
                f2t.play(tempfile.gettempdir(), fps=bad)

    def test_cli_rejects_bad_grid_args(self):
        for args in (["--cols", "0"], ["--rows", "-1"], ["--target-fps", "0"], ["--target-fps", "inf"]):
            with self.subTest(args=args):
                res = subprocess.run([sys.executable, "-I", SCRIPT, "extract", "v", "s", *args],
                                     capture_output=True)
                self.assertEqual(res.returncode, 2)


class ScenesTest(TempRepo):
    def write(self, text):
        p = os.path.join(self.outside, "s.toml")
        with open(p, "w") as f:
            f.write(text)
        return p

    def test_valid(self):
        p = self.write('[[scene]]\nname = "a_1"\nstart = 1\nend = 3.5\nspeed = 2\n')
        self.assertEqual(f2t.load_scenes(p), [{"name": "a_1", "start": 1.0, "end": 3.5, "speed": 2.0}])

    def test_invalid(self):
        for body in ('[[scene]]\nname = "a"\nstart = 3\nend = 1\nspeed = 1\n',
                     '[[scene]]\nname = "a"\nstart = 0\nend = 1\nspeed = 0\n',
                     '[[scene]]\nname = "A b"\nstart = 0\nend = 1\nspeed = 1\n',
                     '[[scene]]\nname = "a"\nstart = 0\nend = 1\n',
                     '[[scene]]\nname = "a"\nstart = 0\nend = 1\nspeed = 1\n' * 2,
                     'x = 1\n'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                f2t.load_scenes(self.write(body))

    def test_starship_scene_list_totals_about_60s(self):
        scenes = f2t.load_scenes(SCENES)
        self.assertEqual(len(scenes), 9)
        total = sum((s["end"] - s["start"]) / s["speed"] for s in scenes)
        self.assertTrue(55 <= total <= 65, total)
        for a, b in zip(scenes, scenes[1:]):
            self.assertLessEqual(a["end"], b["start"])


class FramingTest(unittest.TestCase):
    def test_halfblock_2x2(self):
        rgb = bytes([255, 0, 0, 0, 255, 0,      # top row: red, green
                     0, 0, 255, 0, 0, 255])     # bottom row: blue, blue
        self.assertEqual(f2t.halfblock(rgb, 2, 1),
                         "\x1b[38;2;255;0;0;48;2;0;0;255m▀\x1b[38;2;0;255;0m▀\x1b[0m")

    def test_normalize_chafa_like_output(self):
        raw = "\x1b[?25l" + "".join("\x1b[0m\x1b[38;2;1;2;3m" + "▀" * 4 + "\x1b[0m\n" for _ in range(3)) + "\x1b[?25h"
        out = f2t.normalize_frame(raw, 3, 4)
        self.assertFalse(out.endswith("\n"))
        self.assertNotIn("\x1b[?25", out)
        self.assertEqual([f2t.visible_width(r) for r in out.split("\n")], [4, 4, 4])

    def test_normalize_rejects_bad_frames(self):
        with self.assertRaises(ValueError):
            f2t.normalize_frame("ab\nab\n", 3, 2)            # too few rows
        with self.assertRaises(ValueError):
            f2t.normalize_frame("abc\nab\n", 2, 2)           # too wide
        with self.assertRaises(ValueError):
            f2t.normalize_frame("a\x1b[3bb\nab\n", 2, 2)     # REP would hide cells

    def test_encode_png(self):
        w, h = 3, 2
        rgb = bytes(range(w * h * 3))
        png = f2t.encode_png(w, h, rgb)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        pos, chunks = 8, {}
        while pos < len(png):
            (n,) = struct.unpack(">I", png[pos:pos + 4])
            kind, data = png[pos + 4:pos + 8], png[pos + 8:pos + 8 + n]
            (crc,) = struct.unpack(">I", png[pos + 8 + n:pos + 12 + n])
            self.assertEqual(crc, zlib.crc32(kind + data) & 0xFFFFFFFF)
            chunks[kind] = data
            pos += 12 + n
        self.assertEqual(struct.unpack(">IIBBBBB", chunks[b"IHDR"]), (w, h, 8, 2, 0, 0, 0))
        self.assertEqual(zlib.decompress(chunks[b"IDAT"]), b"\x00" + rgb[:9] + b"\x00" + rgb[9:])
        self.assertIn(b"IEND", chunks)

    def _real_converter(self, name, cmd_fn):
        if shutil.which(name) is None:
            self.skipTest(f"{name} not installed")
        with tempfile.TemporaryDirectory() as d:
            png = os.path.join(d, "f.png")
            with open(png, "wb") as f:
                f.write(f2t.encode_png(COLS, ROWS * 2, gradient(COLS, ROWS * 2)))
            res = subprocess.run(cmd_fn(png, COLS, ROWS), capture_output=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            out = f2t.normalize_frame(res.stdout.decode("utf-8"), ROWS, COLS, name)
            rows = out.split("\n")
            self.assertEqual(len(rows), ROWS)
            self.assertTrue(all(f2t.visible_width(r) == COLS for r in rows))
            self.assertFalse(out.endswith("\n"))

    def test_real_chafa(self):
        self._real_converter("chafa", f2t.chafa_cmd)

    def test_real_img2txt(self):
        self._real_converter("img2txt", f2t.img2txt_cmd)

    def test_frame_bytes_never_writes_a_newline(self):
        frame = "\n".join(f"\x1b[38;2;1;2;3m{'x' * COLS}\x1b[0m" for _ in range(ROWS))
        data = f2t.frame_bytes(frame)
        self.assertNotIn(b"\n", data)
        self.assertNotIn(b"\r", data)
        cups = [m.group(0) for m in f2t.CSI_RE.finditer(data.decode()) if m.group(3) == "H"]
        self.assertEqual(cups, [f"\x1b[{r};1H" for r in range(1, ROWS + 1)])


def marker_row(i):
    return f"S{i:02d}" + "." * (COLS - 6) + f"E{i:02d}"


@unittest.skipIf(shutil.which("tmux") is None, "tmux not installed")
class TmuxPlaybackTest(unittest.TestCase):
    """Plays a one-frame animatic inside detached tmux panes of exact sizes."""

    def setUp(self):
        self.dir = os.path.realpath(tempfile.mkdtemp(prefix="f2t-tmux-"))
        self.sock = f"f2t-test-{os.getpid()}"
        self.conf = os.path.join(self.dir, "tmux.conf")
        with open(self.conf, "w") as f:
            f.write("set -g status off\n")
        self.out = os.path.join(self.dir, "out")
        os.makedirs(os.path.join(self.out, "01_markers"))
        frame = "\n".join(f"\x1b[38;2;200;200;200m{marker_row(i)}\x1b[0m" for i in range(1, ROWS + 1))
        with open(os.path.join(self.out, "01_markers", "00000.ans"), "w") as f:
            f.write(frame)
        manifest = {"version": 1, "cols": COLS, "rows": ROWS, "target_fps": 10, "seconds_per_frame": 0.1,
                    "converter": "halfblock",
                    "scenes": [{"name": "markers", "dir": "01_markers", "frames": ["00000"], "seconds": 0.1}]}
        with open(os.path.join(self.out, f2t.MANIFEST), "w") as f:
            json.dump(manifest, f)
        self.env = dict(os.environ, TERM=os.environ.get("TERM") or "xterm-256color")
        self.env.pop("TMUX", None)

    def tearDown(self):
        subprocess.run(["tmux", "-L", self.sock, "kill-server"], capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)

    def tmux(self, *args):
        return subprocess.run(["tmux", "-L", self.sock, "-f", self.conf, *args],
                              capture_output=True, text=True, env=self.env)

    def start(self, name, w, h, shell_cmd):
        res = self.tmux("new-session", "-d", "-s", name, "-x", str(w), "-y", str(h), shell_cmd)
        self.assertEqual(res.returncode, 0, res.stderr)
        size = self.tmux("display", "-p", "-t", name, "#{pane_width}x#{pane_height}").stdout.strip()
        self.assertEqual(size, f"{w}x{h}")

    def capture(self, name):
        return self.tmux("capture-pane", "-p", "-t", name).stdout.split("\n")

    def play_cmd(self, rc_file, err_file):
        play = [sys.executable, "-I", SCRIPT, "play", "--out", self.out, "--once-frames", "1", "--hold", "6"]
        return (f"{shlex.join(play)} 2>{shlex.quote(err_file)}; echo $? >{shlex.quote(rc_file)}; sleep 6")

    def wait_for(self, pred, timeout=8.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if pred():
                return True
            time.sleep(0.1)
        return False

    def test_exact_size_no_scroll_and_intact_right_edge(self):
        rc, err = os.path.join(self.dir, "rc"), os.path.join(self.dir, "err")
        self.start("exact", COLS, ROWS, self.play_cmd(rc, err))
        self.assertTrue(self.wait_for(lambda: self.capture("exact")[0].startswith("S01")),
                        self.capture("exact"))
        lines = self.capture("exact")
        for i in range(1, ROWS + 1):
            self.assertEqual(lines[i - 1], marker_row(i), f"screen line {i}")
            self.assertEqual(lines[i - 1][COLS - 3:COLS], f"E{i:02d}", f"rightmost cells of line {i}")

    def test_undersized_terminal_is_refused(self):
        rc, err = os.path.join(self.dir, "rc"), os.path.join(self.dir, "err")
        self.start("small", 100, 20, self.play_cmd(rc, err))
        def rc_written():
            if not os.path.exists(rc):
                return False
            with open(rc) as f:
                return bool(f.read().strip())
        self.assertTrue(self.wait_for(rc_written))
        with open(rc) as f:
            self.assertEqual(f.read().strip(), "2")
        with open(err) as f:
            self.assertIn("terminal is 100x20, the animatic needs 137x33", f.read())
        self.assertFalse(any("S01" in line or "E01" in line for line in self.capture("small")))


if __name__ == "__main__":
    unittest.main()
