"""ClipSense API — minimal local backend serving the frontend's job flow.

POST /api/jobs            start processing a YouTube URL
GET  /api/jobs/{id}        poll status (stage + progress for the Progress screen)
GET  /api/jobs/{id}/result final VideoResult (frontend types/contracts.ts shape)
POST /api/jobs/{id}/qa     grounded Q&A over the transcript
GET  /api/health           liveness

Real today: captions ingestion, LLM summarizer/critic/QA when GROQ_API_KEY is
set (degraded transcript-only result without it). Not wired yet: vision agent
(needs video download + CV deps) and ASR fallback for YouTube URLs.
"""
import re
import threading
import time
import urllib.request
import json as _json
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agents.transcript import TranscriptAgent
from .config import get_settings
from .schemas.transcript import TranscriptResult
from .services.llm import llm_available, llm_json
from .utils.timestamps import fmt_ts

app = FastAPI(title="ClipSense API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/)|youtu\.be/)([\w-]{11})")

JOBS: dict[str, dict] = {}
STAGE_PROGRESS = {"ingesting": 0.1, "listening": 0.35, "watching": 0.5,
                  "summarizing": 0.75, "verifying": 0.92}


class JobRequest(BaseModel):
    url: str
    depth: str = "standard"


class QARequest(BaseModel):
    question: str


def _set(job_id: str, stage: str, detail: str) -> None:
    JOBS[job_id].update(stage=stage, detail=detail, progress=STAGE_PROGRESS[stage])


def _oembed_meta(video_id: str) -> dict:
    try:
        url = f"https://www.youtube.com/oembed?url=https://youtu.be/{video_id}&format=json"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = _json.loads(r.read().decode())
        return {"title": data.get("title", video_id), "channel": data.get("author_name", "")}
    except Exception:
        return {"title": f"YouTube video {video_id}", "channel": ""}


# ------------------------------------------------------------- summarization

def _chunks(segments, max_words=2200):
    out, cur, words = [], [], 0
    for s in segments:
        cur.append(s)
        words += len(s.text.split())
        if words >= max_words:
            out.append(cur)
            cur, words = [], 0
    if cur:
        out.append(cur)
    return out


def _llm_summary(settings, t: TranscriptResult) -> dict:
    notes = []
    for ch in _chunks(t.segments):
        text = "\n".join(f"[{fmt_ts(s.start)}] {s.text}" for s in ch)
        out = llm_json(settings,
            "Summarize this video transcript part. Reply with JSON "
            '{"points": [{"ts": "mm:ss", "note": "..."}]} — 3-6 factual points, '
            f"each with the nearest timestamp.\n\n{text}")
        notes.extend(out.get("points", []))
    reduced = llm_json(settings,
        "You write faithful video summaries. From these timestamped notes, reply with JSON "
        '{"tldr": "2-3 sentences", "takeaways": ["..."], '
        '"chapters": [{"title": "...", "start": "mm:ss", "end": "mm:ss", '
        '"summary": "...", "key_points": ["..."], "evidence_ts": ["mm:ss"]}]} '
        "— 3-6 chapters covering the whole video in order.\n\n"
        + "\n".join(f"[{p.get('ts', '0:00')}] {p.get('note', '')}" for p in notes),
        max_tokens=4000)
    return reduced


def _parse_mmss(x) -> float:
    parts = re.findall(r"\d+", str(x or "0"))
    sec = 0
    for p in parts[-3:]:
        sec = sec * 60 + int(p)
    return float(sec)


def _fallback_summary(t: TranscriptResult) -> dict:
    """No LLM key: honest plumbing demo — time-sliced chapters from transcript."""
    segs = t.segments
    n = max(1, min(5, len(segs) // 4))
    size = max(1, len(segs) // n)
    chapters = []
    for i in range(0, len(segs), size):
        block = segs[i:i + size]
        first = block[0].text
        chapters.append({
            "title": (first[:60] + "…") if len(first) > 60 else first,
            "start": block[0].start, "end": block[-1].end,
            "summary": " ".join(s.text for s in block[:2]),
            "key_points": [s.text for s in block[1:3]],
            "evidence_timestamps": [s.start for s in block[:3]],
        })
    return {
        "tldr": "GROQ_API_KEY is not set, so this is the raw transcript sliced into "
                "chapters — add the key to backend/.env for real summaries.",
        "takeaways": [s.text for s in segs[:4]],
        "chapters": chapters,
    }


def _llm_critic(settings, summary: dict, t: TranscriptResult) -> dict:
    claims = (summary.get("takeaways", [])[:5]
              + [c.get("summary", "") for c in summary.get("chapters", [])][:3])
    transcript_text = "\n".join(
        f"[{fmt_ts(s.start)}] {s.text}" for s in t.segments)[:24000]
    out = llm_json(settings,
        "Check each claim against the transcript. Reply with JSON "
        '{"results": [{"claim": "...", "supported": true/false, '
        '"evidence": "[mm:ss] quote or why unsupported", "confidence": 0.0-1.0}]}\n\n'
        "CLAIMS:\n" + "\n".join(f"- {c}" for c in claims if c)
        + "\n\nTRANSCRIPT:\n" + transcript_text,
        max_tokens=3500)
    results = [{**r, "revision_needed": not r.get("supported", True)}
               for r in out.get("results", [])]
    supported = sum(1 for r in results if r.get("supported"))
    return {
        "faithfulness": supported / len(results) if results else 0.0,
        "checked": len(results),
        "results": results,
    }


# ------------------------------------------------------------- pipeline

def run_pipeline(job_id: str, url: str) -> None:
    settings = get_settings()
    job = JOBS[job_id]
    try:
        _set(job_id, "ingesting", "Checking the link")
        m = VIDEO_ID_RE.search(url)
        if not m:
            raise ValueError("Not a recognizable YouTube URL")
        vid = m.group(1)
        meta = _oembed_meta(vid)

        _set(job_id, "listening", "Fetching captions")
        t = TranscriptAgent().run(video_id=vid, process_seconds=settings.max_process_seconds)
        job["transcript"] = t

        _set(job_id, "watching", "Vision agent not wired for YouTube URLs yet — skipping")
        vision = []

        _set(job_id, "summarizing", "Writing chapters and takeaways")
        if llm_available(settings):
            raw = _llm_summary(settings, t)
            chapters = [{
                "title": c.get("title", "Chapter"),
                "start": _parse_mmss(c.get("start")),
                "end": _parse_mmss(c.get("end")),
                "summary": c.get("summary", ""),
                "key_points": c.get("key_points", []),
                "evidence_timestamps": [_parse_mmss(x) for x in c.get("evidence_ts", [])],
            } for c in raw.get("chapters", [])]
            summary = {"tldr": raw.get("tldr", ""),
                       "takeaways": raw.get("takeaways", []), "chapters": chapters}
        else:
            summary = _fallback_summary(t)

        _set(job_id, "verifying", "Checking claims against the transcript")
        critic = (_llm_critic(settings, summary, t) if llm_available(settings)
                  else {"faithfulness": 0.0, "checked": 0, "results": []})

        duration = t.segments[-1].end if t.segments else 0
        job["result"] = {
            "video_id": vid, "title": meta["title"], "channel": meta["channel"],
            "duration": duration, "transcript_source": t.source,
            "tldr": summary["tldr"], "takeaways": summary["takeaways"],
            "chapters": summary["chapters"], "vision": vision, "critic": critic,
        }
        job.update(state="done", progress=1.0, detail="Summary ready")
    except Exception as e:
        job.update(state="error", error=f"{type(e).__name__}: {e}", detail="Failed")


# ------------------------------------------------------------- endpoints

@app.get("/api/health")
def health():
    s = get_settings()
    return {"ok": True, "llm": llm_available(s), "time": time.time()}


@app.post("/api/jobs")
def create_job(req: JobRequest):
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"job_id": job_id, "state": "running", "stage": "ingesting",
                    "progress": 0.0, "detail": "Starting"}
    threading.Thread(target=run_pipeline, args=(job_id, req.url), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job id")
    return {k: job.get(k) for k in ("job_id", "state", "stage", "progress", "detail", "error")}


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job id")
    if "result" not in job:
        raise HTTPException(409, "Job not finished")
    return job["result"]


def _retrieve(t: TranscriptResult, question: str, k: int = 5):
    """Keyword-overlap retrieval (embedding store lands with ChromaDB later)."""
    q = set(re.findall(r"\w+", question.lower())) - {"the", "a", "is", "what", "why", "how"}
    scored = []
    for s in t.segments:
        words = set(re.findall(r"\w+", s.text.lower()))
        score = len(q & words)
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:k]] or list(t.segments[:k])


@app.post("/api/jobs/{job_id}/qa")
def qa(job_id: str, req: QARequest):
    job = JOBS.get(job_id)
    if not job or "transcript" not in job:
        raise HTTPException(409, "Job not ready for questions")
    settings = get_settings()
    t: TranscriptResult = job["transcript"]
    hits = _retrieve(t, req.question)
    citations = [{"timestamp": s.start, "source_type": "transcript",
                  "excerpt": s.text[:140]} for s in hits]
    if not llm_available(settings):
        return {"answer": "GROQ_API_KEY is not set, so here are the most relevant "
                          "transcript moments instead of a composed answer.",
                "citations": citations, "confidence": 0.0}
    ctx = "\n".join(f"[{fmt_ts(s.start)}] {s.text}" for s in hits)
    out = llm_json(settings,
        'Answer from the evidence only; cite timestamps like [mm:ss]. Reply with JSON '
        '{"answer": "...", "confidence": 0.0-1.0}.\n\n'
        f"QUESTION: {req.question}\n\nEVIDENCE:\n{ctx}")
    return {"answer": out.get("answer", "No answer produced."),
            "citations": citations,
            "confidence": float(out.get("confidence", 0.5) or 0.5)}
