"""Vision Agent — ClipSense perception pipeline (owner: Husnain).

Ported from the Colab prototype (cell 7) into the hackathon architecture:
  1. Adaptive frame sampling from the video.
  2. Perceptual-hash (pHash) deduplication + grayscale-diff change detection.
  3. EasyOCR text extraction on kept frames (local, free, fast).
  4. Multimodal model (Gemini/Groq, configurable) for frame classification,
     visual description, and hard-to-read text the local OCR misses.
  5. Emits the plan's data contract: VisionEvidence
     {timestamp, frame_type, ocr_text, description, confidence}.

Fixes over the prototype: VLM concurrency is configurable (VISION_WORKERS,
default 1) instead of a hardcoded ThreadPoolExecutor(max_workers=3) that
caused rate-limit storms on the free tier.
"""
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

import cv2
import imagehash
import numpy as np
from PIL import Image

from ..config import Settings, get_settings
from ..schemas.vision import VisionEvidence, normalize_frame_type
from ..services.vision_provider import VisionProvider, get_vision_provider

# dedupe thresholds (tuned in the prototype)
PHASH_NEW_FRAME = 14      # distance to previous frame => scene changed
PHASH_SEEN_BEFORE = 8     # distance to any kept frame => duplicate, skip
GRAY_DIFF_NEW_FRAME = 7.0


class VisionAgent:
    def __init__(self, settings: Settings | None = None, provider: VisionProvider | None = None):
        self.settings = settings or get_settings()
        self.provider = provider or get_vision_provider(self.settings)
        self._ocr_reader = None  # lazy: EasyOCR model load is slow

    # ------------------------------------------------------------------ sampling

    def sample_frames(self, video_path: str, limit_sec: float, interval: float) -> list[dict]:
        """Sample every `interval` seconds, keep only visually-new frames."""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        dur = min(total / fps if total else limit_sec, limit_sec)

        fdir = os.path.join(os.path.dirname(video_path) or ".", "frames")
        shutil.rmtree(fdir, ignore_errors=True)
        os.makedirs(fdir)

        kept, hashes, last_h, last_g, t = [], [], None, None, 0.0
        max_w = self.settings.frame_max_width
        while t < dur:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok:
                break
            pil = Image.fromarray(cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2RGB))
            h = imagehash.phash(pil, hash_size=16)
            g = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY).astype("float32")
            new = True if last_h is None else (
                (h - last_h) >= PHASH_NEW_FRAME or float(np.abs(g - last_g).mean()) >= GRAY_DIFF_NEW_FRAME
            )
            if new and any((h - k) < PHASH_SEEN_BEFORE for k in hashes):
                new = False
            if new:
                fr = frame
                if fr.shape[1] > max_w:
                    fr = cv2.resize(fr, (max_w, int(fr.shape[0] * max_w / fr.shape[1])))
                p = os.path.join(fdir, f"f_{int(t):06d}.jpg")
                cv2.imwrite(p, fr, [cv2.IMWRITE_JPEG_QUALITY, 80])
                kept.append({"timestamp": float(t), "path": p})
                hashes.append(h)
                last_h, last_g = h, g
            t += interval
        cap.release()
        return kept

    # ------------------------------------------------------------------ OCR

    @property
    def ocr_reader(self):
        if self._ocr_reader is None and self.settings.use_easyocr:
            import easyocr
            langs = [s.strip() for s in self.settings.easyocr_languages.split(",") if s.strip()]
            self._ocr_reader = easyocr.Reader(langs, gpu=False, verbose=False)
        return self._ocr_reader

    def ocr_frame(self, path: str) -> tuple[str, float]:
        """EasyOCR pass. Returns (text, mean confidence of kept detections)."""
        if not self.settings.use_easyocr:
            return "", 0.0
        try:
            results = self.ocr_reader.readtext(path)
        except Exception as e:
            print(f"   [vision/ocr] EasyOCR failed on {os.path.basename(path)}: {e}")
            return "", 0.0
        kept = [(text, conf) for _, text, conf in results if conf >= self.settings.ocr_min_confidence]
        if not kept:
            return "", 0.0
        text = "\n".join(t for t, _ in kept)
        conf = float(np.mean([c for _, c in kept]))
        return text.strip(), conf

    # ------------------------------------------------------------------ analysis

    def analyse_frame(self, frame: dict) -> VisionEvidence:
        local_text, local_conf = self.ocr_frame(frame["path"])
        try:
            out = self.provider.analyse_image(frame["path"])
        except Exception as e:
            print(f"   [vision] provider failed on {os.path.basename(frame['path'])}: {str(e)[:200]}")
            out = {}

        vlm_text = (out.get("ocr_text") or "").strip()
        # Local OCR is the primary text source; the VLM covers hard/stylized
        # text EasyOCR misses. Prefer whichever read more.
        if local_text and len(local_text) >= len(vlm_text):
            ocr_text, ocr_conf = local_text, local_conf
        else:
            ocr_text, ocr_conf = vlm_text, 0.6 if vlm_text else 0.0

        try:
            vlm_conf = float(out.get("confidence", 0.5))
        except (TypeError, ValueError):
            vlm_conf = 0.5
        confidence = round(max(ocr_conf, vlm_conf if out else 0.0), 3)

        return VisionEvidence(
            timestamp=frame["timestamp"],
            frame_type=normalize_frame_type(out.get("frame_type", "other")),
            ocr_text=ocr_text,
            description=(out.get("description") or "").strip(),
            confidence=min(max(confidence, 0.0), 1.0),
        )

    # ------------------------------------------------------------------ entrypoint

    def run(self, video_path: str, process_seconds: float | None = None,
            frame_budget: int | None = None, sample_interval: float | None = None) -> list[VisionEvidence]:
        s = self.settings
        limit = process_seconds or s.max_process_seconds
        budget = frame_budget or s.max_vision_frames
        interval = sample_interval or s.frame_sample_interval

        kept = self.sample_frames(video_path, limit, interval)
        print(f"   [vision] {len(kept)} visually-unique frames after dedupe")

        if len(kept) > budget:
            idx = np.linspace(0, len(kept) - 1, budget).round().astype(int)
            kept = [kept[i] for i in sorted(set(idx))]
        print(f"   [vision] analysing {len(kept)} frames "
              f"(provider={s.vision_provider}, workers={s.vision_workers})")

        if s.vision_workers > 1:
            with ThreadPoolExecutor(max_workers=s.vision_workers) as ex:
                evidence = list(ex.map(self.analyse_frame, kept))
        else:
            evidence = [self.analyse_frame(f) for f in kept]

        n_text = sum(1 for e in evidence if e.ocr_text)
        print(f"   [vision] done: {len(evidence)} frames, {n_text} with on-screen text")
        return evidence
