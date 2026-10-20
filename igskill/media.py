"""ffmpeg pro-editing pipeline for Instagram.

All heavy lifting is ffmpeg via subprocess (robust, no heavy python deps).
Functions are chunked: each returns the output path and prints a one-line log.

Capabilities:
  fit_reels / fit_post  — auto-ratio with blurred padding
  compress              — H.264 + AAC under IG limits
  burn_subtitles        — style .srt/.ass onto video
  add_watermark         — text or PNG overlay
  add_music             — mix background track with voice ducking
  beat_cut              — rhythm-cut video at N-second beats
  slideshow             — photos -> zoompan reel with music
  thumbnail             — cover frame extraction
  intro_outro           — concat branding clips
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REELS_W, REELS_H = 1080, 1920
POST_SQUARE = (1080, 1080)
POST_PORTRAIT = (1080, 1350)  # 4:5


class MediaError(RuntimeError):
    pass


def ensure_ffmpeg() -> None:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise MediaError(
            "ffmpeg/ffprobe not found on PATH. Install:\n"
            "  Ubuntu/Debian: sudo apt install -y ffmpeg\n"
            "  macOS: brew install ffmpeg\n"
            "  Windows: winget install Gyan.FFmpeg"
        )


def _run(args: list[str]) -> None:
    ensure_ffmpeg()
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-6:])
        raise MediaError(f"ffmpeg failed:\n{tail}")


def _log(msg: str) -> None:
    print(f"[media] {msg}")


def probe(path: str | Path) -> dict:
    ensure_ffmpeg()
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise MediaError(f"ffprobe failed on {path}")
    return json.loads(proc.stdout)


def is_video(path: str | Path) -> bool:
    return Path(path).suffix.lower() in {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}


# ------------------------------------------------------------------ fitting --

def _blur_pad_filter(w: int, h: int) -> str:
    return (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"gblur=sigma=28,boxblur=6:2[bg];"
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
    )


def fit_reels(src: str | Path, out: str | Path) -> Path:
    """Any video -> 1080x1920 9:16 with blurred background fill."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-i", str(src),
          "-filter_complex", _blur_pad_filter(REELS_W, REELS_H),
          "-map", "[v]", "-map", "0:a?",
          "-c:v", "libx264", "-preset", "medium", "-crf", "20",
          "-c:a", "aac", "-b:a", "128k", "-r", "30",
          "-movflags", "+faststart", str(out)])
    _log(f"reel-ified -> {out.name} (1080x1920)")
    return out


def fit_post(src: str | Path, out: str | Path, ratio: str = "1:1") -> Path:
    """Any image/video -> square 1:1 or portrait 4:5 post with blur fill."""
    w, h = POST_SQUARE if ratio == "1:1" else POST_PORTRAIT
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    if is_video(src):
        _run(["ffmpeg", "-y", "-i", str(src),
              "-filter_complex", _blur_pad_filter(w, h),
              "-map", "[v]", "-map", "0:a?",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20",
              "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
    else:
        _run(["ffmpeg", "-y", "-i", str(src),
              "-filter_complex", _blur_pad_filter(w, h),
              "-map", "[v]", "-frames:v", "1", "-q:v", "2", str(out)])
    _log(f"post-ified -> {out.name} ({w}x{h})")
    return out


def compress(src: str | Path, out: str | Path, max_mb: float = 90) -> Path:
    """H.264/AAC compress, tries CRF ladder until under size limit."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    for crf in (23, 26, 29, 32):
        _run(["ffmpeg", "-y", "-i", str(src),
              "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
              "-pix_fmt", "yuv420p", "-profile:v", "high",
              "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
        size_mb = out.stat().st_size / 1_048_576
        if size_mb <= max_mb:
            _log(f"compressed -> {out.name} ({size_mb:.1f} MB @ crf{crf})")
            return out
        _log(f"crf{crf} gave {size_mb:.1f} MB, retrying smaller")
    raise MediaError("could not reach target size — trim the video length")


# ------------------------------------------------------------------- styles --

def burn_subtitles(src: str | Path, srt: str | Path, out: str | Path,
                   style: str = "FontName=Noto Sans,FontSize=15,PrimaryColour=&H00FFFFFF,"
                                "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
                                "MarginV=38,Bold=1") -> Path:
    """Burn an .srt/.ass file onto the video (styled like top creators)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    sub = str(Path(srt).resolve()).replace("\\", "/").replace(":", r"\:")
    _run(["ffmpeg", "-y", "-i", str(src),
          "-vf", f"subtitles={sub}:force_style='{style}'",
          "-c:v", "libx264", "-preset", "medium", "-crf", "20",
          "-c:a", "copy", "-movflags", "+faststart", str(out)])
    _log(f"subtitles burned -> {out.name}")
    return out


def add_watermark(src: str | Path, out: str | Path,
                  text: str = "", png: str | Path | None = None,
                  position: str = "top-right") -> Path:
    """Overlay @handle text or PNG logo. position: top-right|bottom-right|top-left|bottom-left."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    margin = 36
    pos = {
        "top-right": f"w-tw-{margin}:{margin}",
        "bottom-right": f"w-tw-{margin}:h-th-{margin}",
        "top-left": f"{margin}:{margin}",
        "bottom-left": f"{margin}:h-th-{margin}",
    }[position]
    if png:
        _run(["ffmpeg", "-y", "-i", str(src), "-i", str(png),
              "-filter_complex",
              f"[1:v]scale=iw*0.18:-1[wm];[0:v][wm]overlay={pos}",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20",
              "-c:a", "copy", "-movflags", "+faststart", str(out)])
    else:
        safe = (text or "@instagram").replace(":", r"\:").replace("'", r"\'")
        _run(["ffmpeg", "-y", "-i", str(src),
              "-vf", f"drawtext=text='{safe}':fontsize=40:fontcolor=white@0.75:"
                     f"borderw=2:bordercolor=black:x={pos.split(':')[0]}:y={pos.split(':')[1]}",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20",
              "-c:a", "copy", "-movflags", "+faststart", str(out)])
    _log(f"watermark added -> {out.name}")
    return out


def add_music(src: str | Path, music: str | Path, out: str | Path,
              music_volume: float = 0.25, duck_voice: bool = True) -> Path:
    """Mix background music under the original audio (sidechain ducking)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    music_vol = f"volume={music_volume}"
    if duck_voice:
        filt = (
            f"[1:a]{music_vol},asplit=2[bg1][bg2];"
            f"[0:a][bg1]sidechaincompress="
            f"threshold=0.05:ratio=8:attack=5:release=300[duck];"
            f"[duck][bg2]amix=inputs=2:duration=first:dropout_transition=2,"
            f"alimiter=limit=0.95[a]"
        )
    else:
        filt = f"[1:a]{music_vol}[bg];[0:a][bg]amix=inputs=2:duration=first[a]"
    _run(["ffmpeg", "-y", "-i", str(src), "-i", str(music),
          "-filter_complex", filt, "-map", "0:v", "-map", "[a]",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
          "-shortest", "-movflags", "+faststart", str(out)])
    _log(f"music mixed -> {out.name}")
    return out


def beat_cut(src: str | Path, out: str | Path, every: float = 2.0) -> Path:
    """Rhythm-cut: keep `every` seconds of each beat segment (snappier watch-time)."""
    info = probe(src)
    dur = float(info["format"]["duration"])
    seg_dir = Path(out).parent / ".beat_segs"
    seg_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    t, i = 0.0, 0
    while t < dur - 0.4:
        seg = seg_dir / f"seg{i:03d}.mp4"
        _run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(src), "-t", f"{every:.2f}",
              "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac",
              "-avoid_negative_ts", "make_zero", str(seg)])
        parts.append(seg)
        t += every * 2  # skip half — creates jump-cut energy
        i += 1
    concat_list = seg_dir / "list.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
          "-c", "copy", "-movflags", "+faststart", str(out)])
    shutil.rmtree(seg_dir, ignore_errors=True)
    _log(f"beat-cut {i} segments -> {out.name}")
    return out


def slideshow(photos: list[str | Path], out: str | Path, per_photo: float = 2.2,
              music: str | Path | None = None) -> Path:
    """Photos -> 9:16 zoompan reel (Ken Burns), optional music track."""
    if not photos:
        raise MediaError("slideshow needs at least one photo")
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    inputs, filters, zooms = [], [], []
    for i, p in enumerate(photos):
        inputs += ["-loop", "1", "-t", f"{per_photo:.2f}", "-i", str(p)]
        fps = 30
        frames = int(per_photo * fps)
        filters.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0015,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps={fps},setsar=1[v{i}]")
        zooms.append(f"[v{i}]")
    chain = "".join(zooms) + f"concat=n={len(photos)}:v=1:a=0[vout]"
    args = ["ffmpeg", "-y", *inputs]
    if music:
        args += ["-i", str(music)]  # inputs BEFORE any output options
    args += ["-filter_complex", ";".join(filters + [chain]), "-map", "[vout]"]
    if music:
        args += ["-map", f"{len(photos)}:a", "-c:a", "aac", "-b:a", "160k",
                 "-shortest"]
    args += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    _run(args)
    _log(f"slideshow reel ({len(photos)} photos) -> {out.name}")
    return out


def thumbnail(src: str | Path, out: str | Path, at: float = 1.0) -> Path:
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-ss", f"{max(0.0, at):.2f}", "-i", str(src),
          "-frames:v", "1", "-q:v", "2", str(out)])
    _log(f"thumbnail -> {out.name}")
    return out


def intro_outro(main: str | Path, intro: str | Path | None,
                outro: str | Path | None, out: str | Path) -> Path:
    """Concat branding clips around the main video (same codec re-encode)."""
    pieces = [p for p in (intro, main, outro) if p]
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    seg_dir = out.parent / ".concat_segs"
    seg_dir.mkdir(parents=True, exist_ok=True)
    norm = []
    for i, p in enumerate(pieces):
        n = seg_dir / f"n{i}.mp4"
        _run(["ffmpeg", "-y", "-i", str(p), "-c:v", "libx264", "-preset", "fast",
              "-crf", "20", "-r", "30", "-vf", "scale=1080:1920:force_original_aspect_ratio="
              "decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
              "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", str(n)])
        norm.append(n)
    concat_list = seg_dir / "list.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in norm), encoding="utf-8")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
          "-c", "copy", "-movflags", "+faststart", str(out)])
    shutil.rmtree(seg_dir, ignore_errors=True)
    _log(f"assembled {len(pieces)} clips -> {out.name}")
    return out


def full_reel_pipeline(src: str | Path, out_dir: str | Path, *,
                       srt: str | Path | None = None,
                       music: str | Path | None = None,
                       watermark_text: str = "",
                       watermark_png: str | Path | None = None,
                       beat_every: float | None = None,
                       intro: str | Path | None = None,
                       outro: str | Path | None = None) -> Path:
    """The whole factory: ratio -> beat cut -> subs -> music -> watermark -> compress."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(src).stem
    cur = fit_reels(src, out_dir / f"{stem}_169.mp4")
    if beat_every:
        cur = beat_cut(cur, out_dir / f"{stem}_cut.mp4", every=beat_every)
    if intro or outro:
        cur = intro_outro(cur, intro, outro, out_dir / f"{stem}_branded.mp4")
    if srt and Path(srt).exists():
        cur = burn_subtitles(cur, srt, out_dir / f"{stem}_sub.mp4")
    if music and Path(music).exists():
        cur = add_music(cur, music, out_dir / f"{stem}_music.mp4")
    if watermark_png or watermark_text:
        cur = add_watermark(cur, out_dir / f"{stem}_wm.mp4",
                            text=watermark_text, png=watermark_png)
    cur = compress(cur, out_dir / f"{stem}_final.mp4")
    thumbnail(cur, out_dir / f"{stem}_cover.jpg", at=min(1.5, 3.0))
    return cur
