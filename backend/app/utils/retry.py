"""Rate-limit aware retry, ported from the Colab prototype (cell 2).

Understands Groq's "try again in XhYmZs" 429 messages; falls back to
linear backoff for other providers/errors.
"""
import re
import time


def parse_wait(msg: str, default: float) -> float:
    m = re.search(r"try again in\s+(?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", msg)
    if m:
        h, mi, s = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(s) + 1
    return default


def with_retry(fn, retries: int = 7, label: str = "call", max_wait: float = 240.0):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            rate = "429" in msg or "rate_limit" in msg.lower() or "rate limit" in msg.lower()
            fatal = (not rate) and any(
                c in msg[:80] for c in ("Error code: 400", "Error code: 401", "Error code: 404")
            )
            if fatal or attempt == retries - 1:
                raise
            wait = parse_wait(msg, 15 * (attempt + 1)) if rate else 3 * (attempt + 1)
            if rate and wait > max_wait:
                raise RuntimeError(
                    f"[{label}] provider quota exhausted (would need to wait "
                    f"{wait/60:.0f} min). Lower frame budget or retry later.\n{msg}"
                )
            print(f"   [{label}] {'rate limit' if rate else 'error'} - waiting {wait:.0f}s "
                  f"(retry {attempt+1}/{retries-1})")
            time.sleep(wait)
