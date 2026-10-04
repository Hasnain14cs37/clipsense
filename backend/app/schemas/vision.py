"""Vision Agent data contract (execution plan §6.2).

VisionEvidence: {timestamp, frame_type, ocr_text, description, confidence}
"""
from typing import Literal

from pydantic import BaseModel, Field

FrameType = Literal["slide", "code", "chart", "talking_head", "other"]

# The prototype's VLM prompt used a richer label set; normalize to the plan's five.
FRAME_TYPE_ALIASES = {
    "slide": "slide",
    "code": "code",
    "code_editor": "code",
    "chart": "chart",
    "whiteboard": "slide",
    "talking_head": "talking_head",
    "talking-head": "talking_head",
    "demo": "other",
    "broll": "other",
    "other": "other",
}


def normalize_frame_type(raw: str) -> FrameType:
    return FRAME_TYPE_ALIASES.get((raw or "").strip().lower().replace(" ", "_"), "other")


class VisionEvidence(BaseModel):
    timestamp: float = Field(ge=0, description="Seconds from video start")
    frame_type: FrameType = "other"
    ocr_text: str = ""
    description: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
