"""ASR provider abstraction for the Transcript Agent.

The execution plan assigns Husnain the faster-whisper fallback (local, free,
no API quota). The Colab prototype used Groq's Whisper API; both are kept
behind one interface, switchable via ASR_PROVIDER.
"""
import math
import os
from abc import ABC, abstractmethod
from typing import Optional

from ..config import Settings
from ..utils.media import cut_audio_chunk, ffprobe_duration
from ..utils.retry import with_retry


class ASRProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, lang: Optional[str] = None) -> tuple[list[dict], Optional[str]]:
        """Return ([{start, end, text}, ...], detected_language)."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Value for TranscriptResult.source."""


class FasterWhisperASR(ASRProvider):
    """Local ASR — no API key, no rate limits. Handles long files natively."""

    source_name = "faster-whisper"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None  # lazy: model download/load is slow

    @property
    def model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            s = self.settings
            self._model = WhisperModel(
                s.faster_whisper_model,
                device=s.faster_whisper_device,
                compute_type=s.faster_whisper_compute,
            )
        return self._model

    def transcribe(self, audio_path, lang=None):
        segments, info = self.model.transcribe(
            audio_path, language=lang, vad_filter=True, beam_size=5)
        segs = []
        for s in segments:  # generator — transcription happens as we iterate
            text = s.text.strip()
            if text:
                segs.append({"start": float(s.start), "end": float(s.end), "text": text})
        return segs, getattr(info, "language", None) or lang


class GroqWhisperASR(ASRProvider):
    """Groq Whisper API — ported from prototype cell 6, 600s lossless chunks."""

    source_name = "groq-whisper"

    def __init__(self, settings: Settings):
        from groq import Groq
        self.client = Groq(api_key=settings.groq_api_key, max_retries=0)
        self.model = settings.asr_model_groq
        self.chunk = settings.asr_chunk_seconds

    def transcribe(self, audio_path, lang=None):
        d = os.path.dirname(audio_path) or "."
        dur = ffprobe_duration(audio_path)
        n, segs, detected = max(1, math.ceil(dur / self.chunk)), [], None
        for i in range(n):
            off = i * self.chunk
            part = os.path.join(d, f"part_{i:03d}.mp3")
            cut_audio_chunk(audio_path, part, off, self.chunk)

            def go():
                with open(part, "rb") as f:
                    kw = dict(file=(os.path.basename(part), f.read()), model=self.model,
                              response_format="verbose_json", temperature=0.0,
                              timestamp_granularities=["segment"])
                    if lang:
                        kw["language"] = lang
                    return self.client.audio.transcriptions.create(**kw)

            r = with_retry(go, label=f"whisper {i+1}/{n}")
            data = r if isinstance(r, dict) else (r.model_dump() if hasattr(r, "model_dump") else dict(vars(r)))
            detected = detected or data.get("language")
            got = data.get("segments") or []
            for s in got:
                if s.get("no_speech_prob", 0) > 0.9:
                    continue
                segs.append({"start": off + float(s["start"]),
                             "end": off + float(s["end"]), "text": s["text"]})
            if not got and data.get("text"):
                segs.append({"start": off, "end": off + self.chunk, "text": data["text"]})
            print(f"   [asr] whisper chunk {i+1}/{n} done")
        return segs, detected


def get_asr_provider(settings: Settings) -> ASRProvider:
    name = settings.asr_provider.lower().replace("-", "_")
    if name == "faster_whisper":
        return FasterWhisperASR(settings)
    if name == "groq":
        return GroqWhisperASR(settings)
    raise ValueError(f"Unknown ASR_PROVIDER: {settings.asr_provider!r} (use 'faster_whisper' or 'groq')")
