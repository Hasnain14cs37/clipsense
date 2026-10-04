"""ClipSense backend configuration.

All model IDs and limits are configurable via environment variables / .env
(see .env.example) — per the execution plan, nothing is hard-coded so the
team can switch providers without restructuring the app.
"""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Providers ---
    # "gemini" (plan default) or "groq" (prototype default)
    vision_provider: str = "groq"
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # --- Model IDs (keep configurable; providers retire models) ---
    vision_model_groq: str = "qwen/qwen3.8-27b"
    vision_model_gemini: str = "gemini-2.5-flash"
    llm_model_groq: str = "openai/gpt-oss-120b"

    # --- ASR fallback (used when captions are unavailable) ---
    # "faster_whisper" (plan default, local/free) or "groq" (prototype, API)
    asr_provider: str = "faster_whisper"
    asr_model_groq: str = "whisper-large-v3-turbo"
    faster_whisper_model: str = "small"      # tiny/base/small/medium/large-v3
    faster_whisper_device: str = "auto"      # auto/cpu/cuda
    faster_whisper_compute: str = "int8"     # int8 is fastest on CPU
    asr_chunk_seconds: int = 600             # Groq API path splits audio into chunks

    # --- Vision pipeline limits ---
    max_vision_frames: int = 25          # hard cap on frames sent to the VLM
    vision_workers: int = 1              # parallel VLM calls; keep 1 on free tiers
    frame_sample_interval: float = 4.0   # seconds between sampled frames
    max_process_seconds: int = 600       # cap processed duration (MAX_MINUTES=10)
    frame_max_width: int = 960           # resize kept frames before upload

    # --- OCR ---
    use_easyocr: bool = True
    easyocr_languages: str = "en"        # comma-separated, e.g. "en,ur"
    ocr_min_confidence: float = 0.35     # drop EasyOCR detections below this

    work_dir: str = os.path.join(os.path.dirname(__file__), "..", "work")


@lru_cache
def get_settings() -> Settings:
    return Settings()
