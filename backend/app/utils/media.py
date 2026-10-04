"""ffmpeg/ffprobe helpers shared by ingestion and ASR."""
import json
import subprocess


def ffprobe_duration(path: str) -> float:
    """Media duration in seconds via ffprobe (required on PATH)."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        check=True, capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def cut_audio_chunk(src: str, dst: str, offset: float, length: float) -> None:
    """Lossless (-c copy) audio chunk extraction for API-based ASR."""
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(offset), "-t", str(length), "-i", src, "-c", "copy", dst],
        check=True, capture_output=True)
