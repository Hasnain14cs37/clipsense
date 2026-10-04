"""Tests for the Transcript Agent's pure logic (no network, no models)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.transcript import regroup
from app.schemas.transcript import TranscriptResult, TranscriptSegment


def seg(start, end, text):
    return {"start": start, "end": end, "text": text}


def test_regroup_merges_tiny_pieces_into_sentences():
    segs = [seg(0, 1, "Hello and"), seg(1, 2, "welcome to this video about"),
            seg(2, 3, "machine learning, let us begin"),
            seg(3, 4, "with the basics of neural networks today.")]
    out = regroup(segs)
    assert len(out) == 1
    assert out[0]["start"] == 0 and out[0]["end"] == 4
    assert out[0]["text"].endswith("today.")


def test_regroup_skips_music_markers_and_empties():
    segs = [seg(0, 1, "[Music]"), seg(1, 2, "  "), seg(2, 3, "Real words here.")]
    out = regroup(segs)
    assert len(out) == 1
    assert out[0]["text"] == "Real words here."


def test_regroup_caps_at_max_words():
    segs = [seg(i, i + 1, "word " * 10) for i in range(10)]  # no sentence punctuation
    out = regroup(segs, min_words=18, max_words=60)
    assert all(len(o["text"].split()) <= 70 for o in out)  # 60 cap + one trailing piece
    assert len(out) > 1


def test_transcript_contract():
    r = TranscriptResult(
        segments=[TranscriptSegment(start=0, end=2.5, text="hi")],
        source="faster-whisper", language="en")
    d = r.model_dump()
    assert d["segments"][0] == {"start": 0.0, "end": 2.5, "text": "hi", "speaker": None}
    assert d["source"] == "faster-whisper"
