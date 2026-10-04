"""Standalone runner for the Vision Agent — test without the FastAPI app.

Usage:
    python -m scripts.run_vision path/to/video.mp4 [--seconds 600] [--budget 25] [--interval 4]

Writes vision_evidence.json next to the video and prints a summary table.
"""
import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.vision import VisionAgent
from app.utils.timestamps import fmt_ts


def main():
    ap = argparse.ArgumentParser(description="Run the ClipSense Vision Agent on a local video")
    ap.add_argument("video", help="Path to a local video file")
    ap.add_argument("--seconds", type=float, default=None, help="Max seconds to process")
    ap.add_argument("--budget", type=int, default=None, help="Max frames sent to the VLM")
    ap.add_argument("--interval", type=float, default=None, help="Sampling interval in seconds")
    args = ap.parse_args()

    if not os.path.isfile(args.video):
        sys.exit(f"File not found: {args.video}")

    agent = VisionAgent()
    evidence = agent.run(args.video, process_seconds=args.seconds,
                         frame_budget=args.budget, sample_interval=args.interval)

    out_path = os.path.join(os.path.dirname(os.path.abspath(args.video)), "vision_evidence.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([e.model_dump() for e in evidence], f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(evidence)} VisionEvidence records -> {out_path}\n")

    for e in evidence:
        text = (e.ocr_text[:60] + "...") if len(e.ocr_text) > 60 else e.ocr_text
        print(f"  [{fmt_ts(e.timestamp)}] {e.frame_type:<13} conf={e.confidence:.2f}  "
              f"{text or e.description[:60]}")


if __name__ == "__main__":
    main()
