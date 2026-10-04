"""Schema-level tests for the Vision Agent (no network, no video needed)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.schemas.vision import VisionEvidence, normalize_frame_type
from app.utils.json_utils import safe_json
from app.utils.timestamps import fmt_ts, parse_ts


def test_normalize_frame_type():
    assert normalize_frame_type("code_editor") == "code"
    assert normalize_frame_type("whiteboard") == "slide"
    assert normalize_frame_type("broll") == "other"
    assert normalize_frame_type("Talking Head") == "talking_head"
    assert normalize_frame_type("") == "other"
    assert normalize_frame_type("nonsense") == "other"


def test_vision_evidence_contract():
    e = VisionEvidence(timestamp=12.5, frame_type="slide",
                       ocr_text="Intro", description="Title slide", confidence=0.9)
    d = e.model_dump()
    assert set(d) == {"timestamp", "frame_type", "ocr_text", "description", "confidence"}
    assert d["timestamp"] == 12.5


def test_safe_json_extracts_from_noise():
    assert safe_json('noise {"a": 1} trailing')["a"] == 1
    assert safe_json("") == {}
    assert safe_json("no json here") == {}


def test_timestamps():
    assert fmt_ts(75) == "01:15"
    assert fmt_ts(3675) == "1:01:15"
    assert parse_ts("1:02:03") == 3723.0
    assert parse_ts(42) == 42.0
    assert parse_ts(None) is None
