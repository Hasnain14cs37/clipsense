"""Generate a synthetic slide-show video for testing the Vision Agent offline.

Creates test_data/slides_test.mp4: 4 distinct "slides" (title, bullets, code,
closing), 8 seconds each. Sampling + pHash dedupe should keep ~4 frames and
EasyOCR should read the slide text back.

Usage:
    python -m scripts.make_test_video
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

W, H, FPS, SLIDE_SECONDS = 960, 540, 2, 8

SLIDES = [
    ("ClipSense", ["Multi-Agent Video Intelligence", "Hackathon Demo 2026"], (16, 38, 70)),
    ("Why ClipSense?", ["Long videos waste time", "Transcripts miss visuals",
                        "Claims need verification"], (30, 30, 30)),
    ("def summarize(video):", ["    evidence = fuse(transcript, frames)",
                               "    summary = map_reduce(evidence)",
                               "    return critic.verify(summary)"], (12, 12, 12)),
    ("Thank You", ["Questions and Answers", "github.com/clipsense"], (70, 16, 40)),
]


def font(size):
    try:
        return ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", size)
    except OSError:
        return ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", size)


def render_slide(title, lines, bg):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.text((60, 70), title, fill="white", font=font(52))
    for i, line in enumerate(lines):
        d.text((60, 200 + i * 70), line, fill=(220, 220, 220), font=font(34))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "test_data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.abspath(os.path.join(out_dir, "slides_test.mp4"))

    vw = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for title, lines, bg in SLIDES:
        frame = render_slide(title, lines, bg)
        for _ in range(FPS * SLIDE_SECONDS):
            vw.write(frame)
    vw.release()
    print(f"Wrote {len(SLIDES) * SLIDE_SECONDS}s test video -> {out_path}")


if __name__ == "__main__":
    main()
