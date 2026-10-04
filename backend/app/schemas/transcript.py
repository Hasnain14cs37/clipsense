"""Transcript data contract (execution plan §6.2).

TranscriptSegment: {start, end, text, speaker?}
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str
    speaker: Optional[str] = None  # filled only if diarization is added later


class TranscriptResult(BaseModel):
    segments: list[TranscriptSegment]
    source: Literal["youtube-captions", "faster-whisper", "groq-whisper"]
    language: Optional[str] = None
