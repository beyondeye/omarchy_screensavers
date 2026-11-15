#!/usr/bin/env python3
"""frames2text: turn a reference video into a coloured-text animatic.

Extracts frames for a list of scenes (time ranges plus a per-scene speed factor),
converts each frame to coloured text at the screensaver's grid (137x33 cells by
default), and plays the text frames back in a terminal at the compressed timing.

Storage rule: every output lives in a git-ignored, untracked directory or in a
temp directory outside any git work tree. The check runs before anything is
written and cannot be turned off. The video is only read, never copied.

Standard library only (Python 3.11+); needs ffmpeg, and optionally chafa or img2txt.
"""

import argparse
import concurrent.futures
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import tomllib
import zlib

DEFAULT_COLS = 137  # 1080p at scale 1: FONT_PX = 24 in omarchy-screensaver/src/raster.rs
DEFAULT_ROWS = 33
DEFAULT_TARGET_FPS = 10.0
DEFAULT_OUT_REL = os.path.join(".refs", "starship")
MANIFEST = "manifest.json"
CONVERTERS = ("auto", "chafa", "halfblock", "img2txt")
SCENE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
SCENE_DIR_RE = re.compile(r"^[0-9]{2}_[a-z0-9][a-z0-9_]*$")
STAGING_PREFIX = ".staging-"

# Any CSI sequence: ESC [ params intermediates final.
CSI_RE = re.compile(r"\x1b\[([0-9;?]*)([ -/]*)([@-~])")
CURSOR_VIS_RE = re.compile(r"\x1b\[\?25[hl]")
RESET = "\x1b[0m"


class DestError(Exception):
    """A destination that the storage rule refuses."""


class TerminalTooSmall(Exception):
    pass


# --------------------------------------------------------------------------
# Storage rule
# --------------------------------------------------------------------------

def _git(args, cwd):
    env = {k: v for k, v in os.environ.items()
           if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True,
                          text=True, env=env)


def _nearest_existing_dir(path):
    p = path
    while not os.path.isdir(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return p


def _is_under(path, root):
    return os.path.commonpath([path, root]) == root


def check_dest(path, temp_root=None, is_dir=True):
    """Return the real path of `path` if the storage rule accepts it, else raise DestError.

    Accepted: (a) inside a git work tree, ignored by git and with no tracked file at
    or under it; (b) outside every git work tree and under the temp root. The real
    path (symlinks followed) is what gets checked. An existing symlink is never
    written through or replaced.
    """
    if os.path.islink(path) and not is_dir:
        raise DestError(f"refusing to write through or replace a symlink: {path}")
    real = os.path.realpath(path)
    probe = _nearest_existing_dir(real if is_dir else os.path.dirname(real))
    if not is_dir:
        # Fast path, one git call: check-ignore exits 0 only for a path that is inside a
        # work tree, ignored, and not tracked (tracked files never count as ignored);
        # 1 means tracked or not ignored; 128 means no work tree here (handled below).
        rc = _git(["check-ignore", "-q", "--", real], probe).returncode
        if rc == 0:
            return real
        if rc == 1:
            raise DestError(f"{real} is tracked by git or not ignored by git; refusing to write it")
    top = _git(["rev-parse", "--show-toplevel"], probe)
    if top.returncode == 0 and top.stdout.strip():
        root = os.path.realpath(top.stdout.strip())
        # A trailing slash lets directory-only patterns (`/.refs/`) match a
        # directory that does not exist yet.
        target = real + os.sep if is_dir else real
        if _git(["check-ignore", "-q", "--", target], root).returncode != 0:
            raise DestError(f"{real} is inside the git work tree {root} but not ignored by git "
                            f"(add it to .gitignore, e.g. /.refs/, or use a temp dir)")
        tracked = _git(["ls-files", "--", real], root)
        if tracked.returncode != 0 or tracked.stdout.strip():
            raise DestError(f"{real} holds files tracked by git; refusing to write there")
        return real
    if _git(["rev-parse", "--git-dir"], probe).returncode == 0:
        raise DestError(f"{real} is inside a git directory; refusing to write there")
    troot = os.path.realpath(temp_root or tempfile.gettempdir())
    if not _is_under(real, troot):
        raise DestError(f"{real} is outside every git work tree and not under the temp "
                        f"directory {troot}; use an ignored dir in a repo or a temp dir")
    return real


class SafeWriter:
    """Every write, replace or removal re-runs the full check_dest on that file first.

    Nothing about eligibility is cached, so a file force-added to git (or a .gitignore
    edit) between two writes is caught on the next one. Files are opened with O_NOFOLLOW,
    so a symlink planted at a file path is refused instead of followed.
    """

    def __init__(self, temp_root=None):
        self.temp_root = temp_root

    def ensure_dir(self, path):
        real = check_dest(path, self.temp_root, is_dir=True)
        os.makedirs(real, exist_ok=True)
        if os.path.realpath(real) != real:
            raise DestError(f"{path} changed while it was created")
        return real

    def _checked_file(self, path):
        return check_dest(path, self.temp_root, is_dir=False)

    def write_bytes(self, path, data):
        real = self._checked_file(path)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC
        fd = os.open(real, flags, 0o644)
        with os.fdopen(fd, "wb") as f:
            f.write(data)

    def write_text(self, path, text):
        self.write_bytes(path, text.encode("utf-8"))

    def remove(self, path):
        real = self._checked_file(path)
        os.unlink(real)

    def replace(self, src, dst):
        """Move src over dst; both ends are checked."""
        real_src = self._checked_file(src)
        real_dst = self._checked_file(dst)
        os.replace(real_src, real_dst)

    def remove_dir(self, path):
        """Remove a directory this tool owns: its files are checked one by one."""
        if os.path.islink(path):
            raise DestError(f"refusing to remove through a symlink: {path}")
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                self.remove(os.path.join(root, name))
            for name in dirs:
                d = os.path.join(root, name)
                if os.path.islink(d):
                    raise DestError(f"refusing to remove through a symlink: {d}")
                os.rmdir(d)
        os.rmdir(path)


# --------------------------------------------------------------------------
# Scenes and manifest
# --------------------------------------------------------------------------

def load_scenes(path):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    scenes = data.get("scene")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError(f"{path}: expected one or more [[scene]] tables")
    seen = set()
    out = []
    for i, s in enumerate(scenes, 1):
        try:
            name, start, end, speed = s["name"], float(s["start"]), float(s["end"]), float(s["speed"])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"{path}: scene {i} needs name, start, end, speed ({e})") from None
        if not isinstance(name, str) or not SCENE_NAME_RE.match(name):
            raise ValueError(f"{path}: scene {i} name {name!r} must match {SCENE_NAME_RE.pattern}")
        if name in seen:
            raise ValueError(f"{path}: duplicate scene name {name!r}")
        if start < 0 or end <= start:
            raise ValueError(f"{path}: scene {name!r} needs 0 <= start < end")
        if speed <= 0:
            raise ValueError(f"{path}: scene {name!r} needs speed > 0")
        seen.add(name)
        out.append({"name": name, "start": start, "end": end, "speed": speed})
    return out


def read_manifest(out_dir):
    path = os.path.join(out_dir, MANIFEST)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"frames2text: no {MANIFEST} in {out_dir}; run `extract` first")


def iter_frames(manifest):
    """Yield (scene, frame_dir_relative, stem) in playback order."""
    for scene in manifest["scenes"]:
        for stem in scene["frames"]:
            yield scene, scene["dir"], stem


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

def encode_png(width, height, rgb):
    """Encode packed RGB8 pixels as a PNG (filter type 0 on every scanline)."""
    stride = width * 3
    if len(rgb) != stride * height:
        raise ValueError("pixel buffer size does not match width*height*3")
    raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(height))

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def _fmt_num(x):
    return f"{x:.6f}".rstrip("0").rstrip(".")


FRAME_EXTS = (".rgb", ".png", ".ans")


def _clear_scene_dir(writer, path):
    """Remove this tool's frame files from a scene dir; remove the dir if it is then empty."""
    if os.path.islink(path) or not os.path.isdir(path):
        return
    for name in os.listdir(path):
        if name.endswith(FRAME_EXTS):
            writer.remove(os.path.join(path, name))
    if not os.listdir(path):
        os.rmdir(path)


def _swap_in(writer, out_dir, stage, manifest):
    """Replace the previous output with the staged one.

    The old manifest goes first, so at no point does a manifest list frames that are
    missing or stale; the new one is written last, once every frame is in place.
    """
    old_path = os.path.join(out_dir, MANIFEST)
    old_dirs = set()
    if os.path.lexists(old_path):
        try:
            with open(old_path, encoding="utf-8") as f:
                old_dirs = {s["dir"] for s in json.load(f).get("scenes", [])
                            if SCENE_DIR_RE.match(str(s.get("dir", "")))}
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        writer.remove(old_path)
    new_dirs = [s["dir"] for s in manifest["scenes"]]
    for d in sorted(old_dirs | set(new_dirs)):
        _clear_scene_dir(writer, os.path.join(out_dir, d))
    for d in new_dirs:
        dst = writer.ensure_dir(os.path.join(out_dir, d))
        src = os.path.join(stage, d)
        for name in sorted(os.listdir(src)):
            writer.replace(os.path.join(src, name), os.path.join(dst, name))
    writer.remove_dir(stage)
    writer.write_text(old_path, json.dumps(manifest, indent=1))


def extract(video, scenes_path, out_dir, cols, rows, target_fps, writer):
    if not os.path.isfile(video):
        sys.exit(f"frames2text: video not found: {video}")
    if shutil.which("ffmpeg") is None:
        sys.exit("frames2text: ffmpeg is not on PATH")
    scenes = load_scenes(scenes_path)
    out_dir = writer.ensure_dir(out_dir)
    height = rows * 2
    frame_size = cols * height * 3
    manifest = {"version": 1, "video": os.path.abspath(video), "scenes_file": os.path.abspath(scenes_path),
                "cols": cols, "rows": rows, "target_fps": target_fps,
                "seconds_per_frame": 1.0 / target_fps, "converter": None, "scenes": []}
    total = 0.0
    # Extract into a staging dir first; the previous output stays untouched (and
    # consistent with its manifest) until every scene has been extracted.
    stage = os.path.join(out_dir, f"{STAGING_PREFIX}{os.getpid()}")
    if os.path.lexists(stage):
        writer.remove_dir(stage)
    stage = writer.ensure_dir(stage)
    try:
        for idx, sc in enumerate(scenes, 1):
            rel = f"{idx:02d}_{sc['name']}"
            sdir = writer.ensure_dir(os.path.join(stage, rel))
            dur = sc["end"] - sc["start"]
            sample = target_fps / sc["speed"]
            cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", _fmt_num(sc["start"]), "-t", _fmt_num(dur),
                   "-i", video, "-vf", f"fps={_fmt_num(sample)},scale={cols}:{height}:flags=area",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            stems = []
            with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:
                while True:
                    buf = proc.stdout.read(frame_size)
                    if len(buf) < frame_size:
                        break  # end of stream; a truncated last frame is dropped
                    stem = f"{len(stems):05d}"
                    writer.write_bytes(os.path.join(sdir, stem + ".rgb"), buf)
                    writer.write_bytes(os.path.join(sdir, stem + ".png"), encode_png(cols, height, buf))
                    stems.append(stem)
            if proc.returncode != 0:
                raise ValueError(f"ffmpeg failed on scene {sc['name']} (exit {proc.returncode}); "
                                 f"the previous output was left as it was")
            if not stems:
                raise ValueError(f"scene {sc['name']} produced no frames (is {sc['start']}s past the "
                                 f"end of the video?); the previous output was left as it was")
            secs = len(stems) / target_fps
            total += secs
            manifest["scenes"].append({**sc, "dir": rel, "frames": stems, "seconds": secs})
            print(f"  {rel:<24} {sc['start']:7.2f}-{sc['end']:7.2f}s  x{sc['speed']:<5g} "
                  f"-> {len(stems):4d} frames, {secs:5.1f}s")
    except BaseException:
        try:
            writer.remove_dir(stage)
        except (OSError, DestError) as e:
            print(f"frames2text: could not remove the staging dir {stage}: {e}", file=sys.stderr)
        raise
    manifest["total_seconds"] = total
    _swap_in(writer, out_dir, stage, manifest)
    print(f"extracted {sum(len(s['frames']) for s in manifest['scenes'])} frames, "
          f"{total:.1f}s of animatic at {cols}x{rows} -> {out_dir}")
    return manifest


# --------------------------------------------------------------------------
# Conversion
# --------------------------------------------------------------------------

def visible_width(row):
    return len(CSI_RE.sub("", row))


def normalize_frame(text, rows, cols, label="frame"):
    """Return the frame as exactly `rows` rows of `cols` cells joined by \\n, no final newline.

    Removes cursor show/hide sequences and carriage returns, drops trailing empty rows
    and ends every row with an SGR reset. Raises ValueError on any other control
    sequence or on a size mismatch, so a converter whose output drifts fails loudly.
    """
    text = CURSOR_VIS_RE.sub("", text).replace("\r", "")
    for m in CSI_RE.finditer(text):
        if m.group(3) != "m" or "?" in m.group(1) or m.group(2):
            raise ValueError(f"{label}: unexpected control sequence {m.group(0)!r}")
    if "\x1b" in CSI_RE.sub("", text):
        raise ValueError(f"{label}: unexpected escape sequence")
    lines = text.split("\n")
    while lines and visible_width(lines[-1]) == 0:
        lines.pop()
    if len(lines) != rows:
        raise ValueError(f"{label}: {len(lines)} rows, expected {rows}")
    out = []
    for i, line in enumerate(lines, 1):
        w = visible_width(line)
        if w != cols:
            raise ValueError(f"{label}: row {i} is {w} cells wide, expected {cols}")
        out.append(line if line.endswith(RESET) else line + RESET)
    return "\n".join(out)


def halfblock(rgb, cols, rows):
    """Each cell is '▀' with fg = top pixel, bg = bottom pixel (truecolor SGR on change)."""
    stride = cols * 3
    out_rows = []
    for r in range(rows):
        top = rgb[2 * r * stride:(2 * r + 1) * stride]
        bot = rgb[(2 * r + 1) * stride:(2 * r + 2) * stride]
        parts = []
        fg = bg = None
        for c in range(cols):
            t = tuple(top[3 * c:3 * c + 3])
            b = tuple(bot[3 * c:3 * c + 3])
            sgr = []
            if t != fg:
                sgr.append("38;2;%d;%d;%d" % t)
                fg = t
            if b != bg:
                sgr.append("48;2;%d;%d;%d" % b)
                bg = b
            if sgr:
                parts.append("\x1b[" + ";".join(sgr) + "m")
            parts.append("▀")
        parts.append(RESET)
        out_rows.append("".join(parts))
    return "\n".join(out_rows)


def chafa_cmd(png, cols, rows):
    return ["chafa", "-f", "symbols", "-c", "full", "-s", f"{cols}x{rows}", "--stretch",
            "--symbols", "block+half", "--animate", "off", png]


def img2txt_cmd(png, cols, rows):
    return ["img2txt", "-W", str(cols), "-H", str(rows), "-f", "utf8", png]


def resolve_converter(name):
    if name == "auto":
        return "chafa" if shutil.which("chafa") else "halfblock"
    if name in ("chafa", "img2txt") and shutil.which(name) is None:
        sys.exit(f"frames2text: {name} is not on PATH")
    return name


def convert_one(converter, frame_base, cols, rows):
    if converter == "halfblock":
        try:
            with open(frame_base + ".rgb", "rb") as f:
                rgb = f.read()
        except OSError as e:
            raise ValueError(f"cannot read {frame_base}.rgb: {e}") from None
        if len(rgb) != cols * rows * 2 * 3:
            raise ValueError(f"{frame_base}.rgb has {len(rgb)} bytes, expected {cols * rows * 6}")
        text = halfblock(rgb, cols, rows)
    else:
        png = frame_base + ".png"
        if not os.path.isfile(png):
            raise ValueError(f"missing frame {png}")
        cmd = (chafa_cmd if converter == "chafa" else img2txt_cmd)(png, cols, rows)
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode != 0:
            raise ValueError(f"{converter} failed on {frame_base}.png (exit {res.returncode}): "
                             f"{res.stderr.decode(errors='replace').strip()}")
        text = res.stdout.decode("utf-8", errors="replace")
    return normalize_frame(text, rows, cols, label=f"{converter} {frame_base}")


def convert(out_dir, converter, writer, jobs=None):
    out_dir = writer.ensure_dir(out_dir)
    manifest = read_manifest(out_dir)
    cols, rows = manifest["cols"], manifest["rows"]
    conv = resolve_converter(converter)
    print(f"converter: {conv}" + (" (auto)" if converter == "auto" else ""))
    bases = [os.path.join(out_dir, d, stem) for _, d, stem in iter_frames(manifest)]
    if not bases:
        sys.exit("frames2text: the manifest lists no frames")
    t0 = time.monotonic()
    manifest_path = os.path.join(out_dir, MANIFEST)
    # Mark the set as unconverted while .ans files are being replaced, so a failure part
    # way leaves a manifest that `play` refuses instead of a mix of old and new frames.
    manifest["converter"] = None
    writer.write_text(manifest_path, json.dumps(manifest, indent=1))
    # Check the first frame alone, so a converter whose output drifts fails at once.
    first = convert_one(conv, bases[0], cols, rows)
    writer.write_text(bases[0] + ".ans", first)
    del first
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs or os.cpu_count() or 4) as pool:
        futures = {pool.submit(convert_one, conv, b, cols, rows): b for b in bases[1:]}
        try:
            for fut in concurrent.futures.as_completed(futures):
                # pop: drop our reference so each frame's text is freed once written
                writer.write_text(futures.pop(fut) + ".ans", fut.result())
                del fut
        except BaseException:
            for fut in futures:
                fut.cancel()
            raise
    elapsed = time.monotonic() - t0
    manifest["converter"] = conv
    writer.write_text(manifest_path, json.dumps(manifest, indent=1))
    print(f"converted {len(bases)} frames in {elapsed:.1f}s ({1000 * elapsed / len(bases):.1f} ms/frame)")
    return manifest


# --------------------------------------------------------------------------
# Playback
# --------------------------------------------------------------------------

def frame_bytes(frame_text):
    """The bytes that draw one frame: every row placed with CUP, never a newline."""
    rows = frame_text.split("\n")
    return "".join(f"\x1b[{i};1H{row}" for i, row in enumerate(rows, 1)).encode("utf-8")


def terminal_size(fd):
    try:
        s = os.get_terminal_size(fd)
        return s.columns, s.lines
    except OSError:
        return None


def _check_size(fd, cols, rows):
    size = terminal_size(fd)
    if size is None:
        raise TerminalTooSmall("play needs a terminal on stdout")
    if size[0] < cols or size[1] < rows:
        raise TerminalTooSmall(f"terminal is {size[0]}x{size[1]}, the animatic needs {cols}x{rows}: "
                               f"enlarge it or re-run extract/convert with --cols/--rows")


def _positive_finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def play(out_dir, fps=None, loop=False, once_frames=None, hold=2.0):
    if fps is not None and not _positive_finite(fps):
        raise ValueError(f"--fps must be a finite number > 0, got {fps}")
    if once_frames is not None and (not isinstance(once_frames, int) or once_frames < 1):
        raise ValueError(f"--once-frames must be >= 1, got {once_frames}")
    if not (math.isfinite(hold) and hold >= 0):
        raise ValueError(f"--hold must be a finite number >= 0, got {hold}")
    manifest = read_manifest(os.path.realpath(out_dir))
    if not manifest.get("converter"):
        sys.exit("frames2text: frames are not converted yet; run `convert` first")
    cols, rows = manifest["cols"], manifest["rows"]
    files = [os.path.join(out_dir, d, stem + ".ans") for _, d, stem in iter_frames(manifest)]
    if once_frames:
        files = files[:once_frames]
    spf = 1.0 / fps if fps is not None else manifest["seconds_per_frame"]
    if not _positive_finite(spf):
        raise ValueError(f"manifest seconds_per_frame must be a finite number > 0, got {spf}")
    out = sys.stdout.buffer
    fd = sys.stdout.fileno()
    try:
        _check_size(fd, cols, rows)
    except TerminalTooSmall as e:
        print(f"frames2text: {e}", file=sys.stderr)
        return 2
    too_small = None
    try:
        out.write(b"\x1b[?1049h\x1b[?25l\x1b[0m\x1b[2J")
        out.flush()
        while True:
            t0 = time.monotonic()
            for i, path in enumerate(files):
                due_next = t0 + (i + 1) * spf
                if time.monotonic() > due_next and i + 1 < len(files):
                    continue  # running late: drop this frame to keep the schedule
                _check_size(fd, cols, rows)
                with open(path, encoding="utf-8") as f:
                    out.write(frame_bytes(f.read()))
                out.flush()
                delay = due_next - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
            if once_frames:
                time.sleep(hold)
            if not loop or once_frames:
                break
    except TerminalTooSmall as e:
        too_small = e
    except KeyboardInterrupt:
        pass
    finally:
        out.write(b"\x1b[0m\x1b[?25h\x1b[?1049l")
        out.flush()
    if too_small:
        print(f"frames2text: {too_small}", file=sys.stderr)
        return 2
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def default_out():
    here = os.path.dirname(os.path.realpath(__file__))
    top = _git(["rev-parse", "--show-toplevel"], here)
    if top.returncode == 0 and top.stdout.strip():
        return os.path.join(top.stdout.strip(), DEFAULT_OUT_REL)
    return None


def _arg_positive_float(s):
    try:
        x = float(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {s!r}") from None
    if not _positive_finite(x):
        raise argparse.ArgumentTypeError(f"must be a finite number > 0, got {s!r}")
    return x


def _arg_nonneg_float(s):
    try:
        x = float(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {s!r}") from None
    if not (math.isfinite(x) and x >= 0):
        raise argparse.ArgumentTypeError(f"must be a finite number >= 0, got {s!r}")
    return x


def _arg_positive_int(s):
    try:
        x = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {s!r}") from None
    if x < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {s!r}")
    return x


def build_parser():
    p = argparse.ArgumentParser(
        prog="frames2text.py",
        description="Turn a reference video into a coloured-text animatic at the screensaver grid "
                    "(extract frames -> convert to text -> play in a terminal). Outputs go only to a "
                    "git-ignored untracked dir (default <repo>/.refs/starship) or a temp dir outside "
                    "any repo; the video is never copied.",
        epilog="Example: frames2text.py all VIDEO tools/frames2text/scenes/starship_flight15.toml")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_out(sp):
        sp.add_argument("--out", help=f"output directory (default <repo>/{DEFAULT_OUT_REL})")

    def add_extract_args(sp):
        sp.add_argument("video", help="the reference video (read only)")
        sp.add_argument("scenes", help="scene list TOML: [[scene]] name/start/end/speed")
        sp.add_argument("--cols", type=_arg_positive_int, default=DEFAULT_COLS,
                        help="grid columns (default %(default)s)")
        sp.add_argument("--rows", type=_arg_positive_int, default=DEFAULT_ROWS,
                        help="grid rows (default %(default)s)")
        sp.add_argument("--target-fps", type=_arg_positive_float, default=DEFAULT_TARGET_FPS,
                        help="animatic frames per second (default %(default)s)")

    def add_convert_args(sp):
        sp.add_argument("--converter", choices=CONVERTERS, default="auto",
                        help="auto = chafa if installed, else halfblock (default %(default)s)")
        sp.add_argument("--jobs", type=_arg_positive_int,
                        help="parallel converter processes (default: CPU count)")

    def add_play_args(sp):
        sp.add_argument("--fps", type=_arg_positive_float,
                        help="override the playback frame rate (a finite number > 0)")
        sp.add_argument("--loop", action="store_true", help="loop until Ctrl-C")
        sp.add_argument("--once-frames", type=_arg_positive_int, help=argparse.SUPPRESS)
        sp.add_argument("--hold", type=_arg_nonneg_float, default=2.0, help=argparse.SUPPRESS)

    sp = sub.add_parser("extract", help="extract scene frames with ffmpeg (raw RGB + PNG)",
                        description="Extract the frames of every scene, scaled to cols x rows*2 pixels.")
    add_extract_args(sp)
    add_out(sp)
    sp = sub.add_parser("convert", help="convert extracted frames to coloured text (.ans)",
                        description="Convert extracted frames to text frames of exactly cols x rows cells.")
    add_convert_args(sp)
    add_out(sp)
    sp = sub.add_parser("play", help="play the text frames in this terminal",
                        description="Play the animatic in the alternate screen at the manifest timing. "
                                    "The terminal must be at least cols x rows.")
    add_play_args(sp)
    add_out(sp)
    sp = sub.add_parser("all", help="extract, convert and play",
                        description="extract + convert + play in one go.")
    add_extract_args(sp)
    add_convert_args(sp)
    add_play_args(sp)
    add_out(sp)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    out = args.out or default_out()
    if not out:
        sys.exit("frames2text: not inside a git repo; pass --out <temp dir>")
    writer = SafeWriter()
    try:
        if args.cmd in ("extract", "all"):
            extract(args.video, args.scenes, out, args.cols, args.rows, args.target_fps, writer)
        if args.cmd in ("convert", "all"):
            convert(out, args.converter, writer, args.jobs)
        if args.cmd in ("play", "all"):
            return play(out, args.fps, args.loop, args.once_frames, args.hold)
    except DestError as e:
        sys.exit(f"frames2text: refused: {e}")
    except ValueError as e:
        sys.exit(f"frames2text: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
