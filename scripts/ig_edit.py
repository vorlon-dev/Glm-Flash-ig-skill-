#!/usr/bin/env python3
"""ig_edit — standalone pro editing (no posting).

  python scripts/ig_edit.py reel-ify  clip.mp4
  python scripts/ig_edit.py post-ify  img.jpg --ratio 4:5
  python scripts/ig_edit.py subtitles clip.mp4 --srt subs.srt
  python scripts/ig_edit.py music     clip.mp4 --track bgm.mp3
  python scripts/ig_edit.py beat-cut  clip.mp4 --every 2.0
  python scripts/ig_edit.py slideshow *.jpg --out out/reel.mp4 --music bgm.mp3
  python scripts/ig_edit.py thumbnail clip.mp4 --at 3
  python scripts/ig_edit.py pipeline  clip.mp4 --subs s.srt --music m.mp3 --watermark "@me"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from igskill.config import load_config  # noqa: E402
from igskill.media import (beat_cut, burn_subtitles, compress, fit_post,  # noqa: E402
                           full_reel_pipeline, slideshow, thumbnail)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="ffmpeg editing factory for IG")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("reel-ify"); s.add_argument("media"); s.add_argument("--out", default=None)
    s = sub.add_parser("post-ify"); s.add_argument("media"); s.add_argument("--ratio", default="1:1", choices=["1:1", "4:5"]); s.add_argument("--out", default=None)
    s = sub.add_parser("subtitles"); s.add_argument("media"); s.add_argument("--srt", required=True); s.add_argument("--out", default=None)
    s = sub.add_parser("music"); s.add_argument("media"); s.add_argument("--track", required=True); s.add_argument("--volume", type=float, default=0.25); s.add_argument("--out", default=None)
    s = sub.add_parser("beat-cut"); s.add_argument("media"); s.add_argument("--every", type=float, default=2.0); s.add_argument("--out", default=None)
    s = sub.add_parser("slideshow"); s.add_argument("photos", nargs="+"); s.add_argument("--per", type=float, default=2.2); s.add_argument("--music", default=None); s.add_argument("--out", default="workspace/slideshow_reel.mp4")
    s = sub.add_parser("thumbnail"); s.add_argument("media"); s.add_argument("--at", type=float, default=1.0); s.add_argument("--out", default=None)
    s = sub.add_parser("compress"); s.add_argument("media"); s.add_argument("--max-mb", type=float, default=90); s.add_argument("--out", default=None)
    s = sub.add_parser("pipeline"); s.add_argument("media"); s.add_argument("--subs"); s.add_argument("--music"); s.add_argument("--watermark"); s.add_argument("--beat", type=float); s.add_argument("--out-dir", default=None)

    a = p.parse_args()
    cfg = load_config()
    wd = cfg.workdir

    if a.cmd == "reel-ify":
        from igskill.media import fit_reels
        out = fit_reels(a.media, a.out or wd / "reelified.mp4")
    elif a.cmd == "post-ify":
        out = fit_post(a.media, a.out or wd / "postified.jpg", ratio=a.ratio)
    elif a.cmd == "subtitles":
        out = burn_subtitles(a.media, a.srt, a.out or wd / "subbed.mp4")
    elif a.cmd == "music":
        from igskill.media import add_music
        out = add_music(a.media, a.track, a.out or wd / "music.mp4", a.volume)
    elif a.cmd == "beat-cut":
        out = beat_cut(a.media, a.out or wd / "cut.mp4", every=a.every)
    elif a.cmd == "slideshow":
        out = slideshow(a.photos, a.out, per_photo=a.per, music=a.music)
    elif a.cmd == "thumbnail":
        out = thumbnail(a.media, a.out or wd / "cover.jpg", at=a.at)
    elif a.cmd == "compress":
        out = compress(a.media, a.out or wd / "compressed.mp4", max_mb=a.max_mb)
    elif a.cmd == "pipeline":
        out = full_reel_pipeline(a.media, a.out_dir or wd, srt=a.subs,
                                 music=a.music, watermark_text=a.watermark or "",
                                 beat_every=a.beat)
    print(f"[done] {out}")


if __name__ == "__main__":
    main()
