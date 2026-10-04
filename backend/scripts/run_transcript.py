"""Standalone runner for the Transcript Agent — test without the FastAPI app.

Usage:
    # YouTube captions (falls back to ASR only if --audio given):
    python -m scripts.run_transcript --video-id dQw4w9WgXcQ

    # Local file / force ASR (faster-whisper by default):
    python -m scripts.run_transcript --audio path/to/audio.mp3 --force-asr

Writes transcript.json next to the audio (or in cwd) and prints a preview.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.transcript import TranscriptAgent
from app.utils.timestamps import fmt_ts


def main():
    ap = argparse.ArgumentParser(description="Run the ClipSense Transcript Agent")
    ap.add_argument("--video-id", help="YouTube video id (for captions)")
    ap.add_argument("--audio", help="Path to extracted audio (ASR input)")
    ap.add_argument("--seconds", type=float, default=None, help="Max seconds to process")
    ap.add_argument("--lang", default=None, help="Language hint, e.g. en, ur")
    ap.add_argument("--force-asr", action="store_true", help="Skip captions, go straight to ASR")
    args = ap.parse_args()

    if not args.video_id and not args.audio:
        ap.error("Give --video-id and/or --audio")

    agent = TranscriptAgent()
    result = agent.run(video_id=args.video_id, audio_path=args.audio,
                       process_seconds=args.seconds, lang_hint=args.lang,
                       force_asr=args.force_asr)

    out_dir = os.path.dirname(os.path.abspath(args.audio)) if args.audio else os.getcwd()
    out_path = os.path.join(out_dir, "transcript.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\nSaved transcript ({result.source}, lang={result.language}) -> {out_path}\n")

    for s in result.segments[:10]:
        print(f"  [{fmt_ts(s.start)}-{fmt_ts(s.end)}] {s.text[:90]}")
    if len(result.segments) > 10:
        print(f"  ... {len(result.segments) - 10} more segments")


if __name__ == "__main__":
    main()
