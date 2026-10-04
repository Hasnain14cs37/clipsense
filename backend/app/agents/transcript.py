"""Transcript Agent — captions first, ASR fallback (plan §6.1).

Ported from the Colab prototype (cell 6):
  1. For YouTube videos, try official captions (youtube-transcript-api).
  2. On failure (or for local files / force_asr), fall back to the configured
     ASR provider — faster-whisper locally (plan default) or Groq Whisper API.
  3. regroup() merges tiny caption/ASR pieces into sentence-like segments.

Emits the plan's data contract: TranscriptSegment {start, end, text, speaker?}.
"""
import re
from typing import Optional

from ..config import Settings, get_settings
from ..schemas.transcript import TranscriptResult, TranscriptSegment
from ..services.asr_provider import ASRProvider, get_asr_provider

CAPTION_LANG_PRIORITY = ["en", "en-US", "en-GB", "hi", "ur"]


def regroup(segs: list[dict], min_words: int = 18, max_words: int = 60) -> list[dict]:
    """Merge tiny caption/ASR pieces into sentence-like segments."""
    out, cur = [], None
    for s in segs:
        t = re.sub(r"\s+", " ", s["text"]).strip()
        if not t or re.fullmatch(r"\[.*?\]", t):  # skip [Music], [Applause], ...
            continue
        if cur is None:
            cur = {"start": s["start"], "end": s["end"], "text": t}
        else:
            cur["text"] += " " + t
            cur["end"] = s["end"]
        n = len(cur["text"].split())
        if (n >= min_words and re.search(r"[.!?]$", cur["text"])) or n >= max_words:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return out


class TranscriptAgent:
    def __init__(self, settings: Settings | None = None, asr: ASRProvider | None = None):
        self.settings = settings or get_settings()
        self._asr = asr  # lazy via property: don't load whisper if captions work

    @property
    def asr(self) -> ASRProvider:
        if self._asr is None:
            self._asr = get_asr_provider(self.settings)
        return self._asr

    def fetch_captions(self, video_id: str, lang_hint: Optional[str] = None,
                       limit: Optional[float] = None) -> list[dict]:
        from youtube_transcript_api import YouTubeTranscriptApi
        langs = ([lang_hint] if lang_hint else []) + CAPTION_LANG_PRIORITY
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):  # new-style API (>= 1.0)
            tr = api.fetch(video_id, languages=langs)
            raw = [{"start": s.start, "end": s.start + s.duration, "text": s.text} for s in tr]
        else:
            tr = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
            raw = [{"start": s["start"], "end": s["start"] + s["duration"], "text": s["text"]}
                   for s in tr]
        if limit:
            raw = [s for s in raw if s["start"] < limit]
        return raw

    def run(self, video_id: Optional[str] = None, audio_path: Optional[str] = None,
            process_seconds: Optional[float] = None, lang_hint: Optional[str] = None,
            force_asr: bool = False) -> TranscriptResult:
        """Captions for YouTube ids; ASR for local files or when captions fail.

        video_id:   YouTube id (None / "local_*" skips the caption attempt)
        audio_path: 16kHz mono audio from the Ingestion Agent (ASR input)
        """
        limit = process_seconds or self.settings.max_process_seconds
        raw, source, lang = None, None, lang_hint

        if not force_asr and video_id and not video_id.startswith("local_"):
            try:
                raw = self.fetch_captions(video_id, lang_hint, limit)
                source = "youtube-captions"
                print(f"   [transcript] using official captions ({len(raw)} lines)")
            except Exception as e:
                print(f"   [transcript] no usable captions ({type(e).__name__}) "
                      f"-> falling back to {self.settings.asr_provider}")

        if not raw:
            if not audio_path:
                raise ValueError("Captions unavailable and no audio_path given for ASR fallback.")
            raw, detected = self.asr.transcribe(audio_path, lang_hint)
            source = self.asr.source_name
            lang = detected or lang

        segs = regroup(raw)
        if not segs:
            raise RuntimeError("Transcript is empty (no speech found?).")

        result = TranscriptResult(
            segments=[TranscriptSegment(**s) for s in segs], source=source, language=lang)
        words = sum(len(s.text.split()) for s in result.segments)
        print(f"   [transcript] ready: {len(result.segments)} segments, {words} words ({source})")
        return result
