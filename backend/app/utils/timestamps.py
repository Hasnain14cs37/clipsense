"""Timestamp helpers (ported from prototype cell 2)."""
import re


def fmt_ts(sec: float) -> str:
    sec = int(max(0, sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_ts(x):
    """'12:34' or '1:02:03' or number -> seconds. Returns None if unparseable."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    parts = re.findall(r"\d+", str(x))
    if not parts:
        return None
    parts = [int(p) for p in parts][-3:]
    sec = 0
    for p in parts:
        sec = sec * 60 + p
    return float(sec)
