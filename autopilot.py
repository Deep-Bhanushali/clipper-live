"""Autopilot workflow for ClipViral YouTube Channel.

End-to-end automated pipeline:
1. Takes a video URL or live stream
2. Clips high-energy highlights with:
   - 1080p high definition (CRF 18)
   - Dynamic viral top hook banner (e.g. "WAIT TILL THE END 💀")
   - Word-by-word animated yellow pop-up captions
   - "ClipViral" channel watermark
3. Automatically uploads the finished Shorts directly to your ClipViral YouTube channel using the free YouTube Data API v3!

Usage:
  python autopilot.py "https://youtu.be/VIDEO_ID" --max-clips 2
  python autopilot.py "https://youtu.be/VIDEO_ID" --privacy public
  python autopilot.py "https://youtu.be/VIDEO_ID" --privacy private
  python autopilot.py "https://youtu.be/VIDEO_ID" --clip-len 30
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = sys.executable


def run_clip(url, clip_len=30, max_seconds=0, top=2, hook="auto", watermark="ClipViral"):
    """Run clip.py to capture highlights."""
    cmd = [
        PYTHON,
        str(HERE / "clip.py"),
        url,
        "--test",
        "--clip-len", str(clip_len),
        "--top", str(top),
        "--hook", hook,
        "--watermark", watermark,
        "--output-dir", "output",
    ]
    if max_seconds > 0:
        cmd += ["--max-seconds", str(max_seconds)]

    print("\n" + "=" * 60)
    print(f"🎬 Starting highlight detection and clipping for: {url}")
    print(f"🏷️  Watermark: {watermark} | Top Hook: {hook} | Target: 1080p Vertical Shorts")
    print("=" * 60 + "\n")

    res = subprocess.run(cmd)
    return res.returncode == 0


def upload_pending_clips(privacy="public", max_uploads=None):
    """Find un-uploaded clips in output/ and upload them to YouTube."""
    from youtube_direct_upload import upload_clip

    output_dir = HERE / "output"
    if not output_dir.exists():
        print("No output directory found.")
        return

    json_files = sorted(output_dir.glob("gta-*.json"), key=os.path.getmtime)
    uploaded_count = 0

    for meta_path in json_files:
        video_path = meta_path.with_suffix(".mp4")
        if not video_path.exists() or video_path.stat().st_size == 0:
            continue

        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue

        # Skip already uploaded clips
        if meta.get("youtube_video_id"):
            continue

        print("\n" + "-" * 50)
        print(f"🚀 Uploading clip to ClipViral: {video_path.name}")
        print("-" * 50)

        try:
            video_id = upload_clip(video_path, meta_path, privacy_status=privacy)
            uploaded_count += 1
            print(f"✅ Successfully posted to YouTube Shorts! (ID: {video_id})")
        except Exception as e:
            print(f"❌ Upload failed for {video_path.name}: {e}")

        if max_uploads and uploaded_count >= max_uploads:
            break

    print(f"\n🎉 Done! Total clips uploaded in this run: {uploaded_count}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", help="YouTube video or live stream URL to clip")
    parser.add_argument("--clip-len", type=int, default=30, help="Target clip length in seconds (default: 30)")
    parser.add_argument("--max-seconds", type=int, default=0, help="Max source seconds to process (0 = all)")
    parser.add_argument("--top", type=int, default=2, help="Clips per analysis chunk (default: 2)")
    parser.add_argument("--hook", default="auto", help="Top banner hook text or 'auto'")
    parser.add_argument("--watermark", default="ClipViral", help="Channel watermark (default: 'ClipViral')")
    parser.add_argument("--privacy", choices=("public", "unlisted", "private"), default="public",
                        help="Upload privacy status (default: public)")
    parser.add_argument("--upload-only", action="store_true", help="Only upload pending clips from output/")
    args = parser.parse_args()

    if args.upload_only:
        upload_pending_clips(privacy=args.privacy)
        return

    if not args.url:
        # Check if there are already pending clips in output/
        pending = [p for p in (HERE / "output").glob("gta-*.mp4") if p.stat().st_size > 0]
        if pending:
            print(f"Found {len(pending)} existing clip(s) in output/. Use --upload-only to post them, or supply a video URL.")
        else:
            parser.print_help()
        return

    # 1. Run clipping
    success = run_clip(
        args.url,
        clip_len=args.clip_len,
        max_seconds=args.max_seconds,
        top=args.top,
        hook=args.hook,
        watermark=args.watermark,
    )

    if not success:
        print("Clipping step encountered an issue.")

    # 2. Upload generated clips
    upload_pending_clips(privacy=args.privacy)


if __name__ == "__main__":
    main()
