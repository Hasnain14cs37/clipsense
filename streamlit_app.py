"""ClipSense — Streamlit deployment.

Streamlit Community Cloud runs Python only, so this app skips the React
frontend and imports the backend agents directly (no FastAPI server needed).
Deploy: share.streamlit.io -> this repo -> main file streamlit_app.py,
then add GROQ_API_KEY under app Secrets for real summaries/critic/Q&A.

Cloud limits: captions-only ingestion (no video download), so the vision
agent and ASR fallback stay off here — the full pipeline runs locally.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import streamlit as st

# Streamlit secrets -> env, BEFORE importing backend config
try:
    for key in ("GROQ_API_KEY",):
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass

from app.agents.transcript import TranscriptAgent  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import (  # noqa: E402
    VIDEO_ID_RE, _fallback_summary, _llm_critic, _llm_summary, _oembed_meta, _retrieve)
from app.services.llm import llm_available, llm_json  # noqa: E402
from app.utils.timestamps import fmt_ts  # noqa: E402

st.set_page_config(page_title="ClipSense", page_icon="🎬", layout="wide")

st.markdown(
    """
    <style>
      .stApp { background: #edf0f3; }
      h1, h2, h3 { font-family: Archivo, system-ui, sans-serif; }
      .timecode { font-family: "IBM Plex Mono", monospace; color: #ff4712; }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = get_settings()
ss = st.session_state


def yt_link(video_id: str, sec: float) -> str:
    return f"https://youtu.be/{video_id}?t={int(sec)}"


def run_pipeline(url: str) -> dict:
    m = VIDEO_ID_RE.search(url)
    if not m:
        raise ValueError("Paste a full YouTube link, like youtube.com/watch?v=… or youtu.be/…")
    vid = m.group(1)

    with st.status("Reading your video…", expanded=True) as status:
        st.write("INGEST — checking the link and metadata")
        meta = _oembed_meta(vid)

        st.write("AUDIO — fetching captions")
        transcript = TranscriptAgent().run(video_id=vid, process_seconds=settings.max_process_seconds)
        st.write(f"AUDIO — {len(transcript.segments)} segments ({transcript.source})")

        st.write("TEXT — writing chapters and takeaways")
        if llm_available(settings):
            raw = _llm_summary(settings, transcript)
            from app.main import _parse_mmss
            chapters = [{
                "title": c.get("title", "Chapter"),
                "start": _parse_mmss(c.get("start")),
                "summary": c.get("summary", ""),
                "key_points": c.get("key_points", []),
            } for c in raw.get("chapters", [])]
            summary = {"tldr": raw.get("tldr", ""), "takeaways": raw.get("takeaways", []),
                       "chapters": chapters}
        else:
            summary = _fallback_summary(transcript)

        st.write("CRITIC — checking claims against the transcript")
        critic = (_llm_critic(settings, summary, transcript) if llm_available(settings)
                  else {"faithfulness": 0.0, "checked": 0, "results": []})

        status.update(label="Summary ready", state="complete", expanded=False)

    duration = transcript.segments[-1].end if transcript.segments else 0
    return {"video_id": vid, "meta": meta, "transcript": transcript,
            "summary": summary, "critic": critic, "duration": duration}


# ----------------------------------------------------------------- header

st.title("🎬 ClipSense")
st.markdown("**Don't watch it all. Understand it all.** — paste a YouTube link, get a "
            "verified summary with every claim pinned to a timestamp.")
if not llm_available(settings):
    st.warning("GROQ_API_KEY is not set (app Secrets) — running in transcript-only mode "
               "without LLM summaries, fact-checking, or composed answers.")

with st.form("job"):
    col1, col2 = st.columns([4, 1])
    url = col1.text_input("YouTube link", placeholder="https://www.youtube.com/watch?v=",
                          label_visibility="collapsed")
    go = col2.form_submit_button("Summarize", type="primary", use_container_width=True)

if go and url:
    try:
        ss.result = run_pipeline(url)
        ss.chat = []
        ss.seek = 0
    except Exception as e:
        st.error(f"Could not process that video: {e}")

# ----------------------------------------------------------------- result

if "result" in ss:
    r = ss.result
    meta, summary, critic = r["meta"], r["summary"], r["critic"]

    left, right = st.columns([5, 4], gap="large")

    with left:
        st.header(meta["title"])
        st.caption(f'{meta["channel"]} · {fmt_ts(r["duration"])} · {r["transcript"].source}')
        st.markdown(f'> {summary["tldr"]}')

        st.subheader("Key takeaways")
        for t in summary["takeaways"]:
            st.markdown(f"- {t}")

        st.subheader("Chapters")
        for i, c in enumerate(summary["chapters"]):
            cols = st.columns([1, 6])
            if cols[0].button(f"▶ {fmt_ts(c['start'])}", key=f"ch{i}"):
                ss.seek = int(c["start"])
            cols[1].markdown(f"**{c['title']}**")
            st.markdown(c.get("summary", ""))
            for k in c.get("key_points", []):
                st.caption(f"· {k}")

    with right:
        st.video(f"https://www.youtube.com/watch?v={r['video_id']}", start_time=ss.get("seek", 0))

        tab_critic, tab_chat = st.tabs(
            [f"Fact-check ({critic['checked']})", "Ask the video"])

        with tab_critic:
            if critic["results"]:
                st.metric("Faithfulness", f"{critic['faithfulness'] * 100:.0f}%",
                          help="Share of summary claims the Critic found supported by evidence")
                for res in critic["results"]:
                    icon = "✅" if res.get("supported") else "🚫"
                    with st.expander(f"{icon} {res.get('claim', '')[:80]}"):
                        st.write(res.get("evidence", ""))
            else:
                st.info("Add GROQ_API_KEY in Secrets to enable the Critic agent.")

        with tab_chat:
            for turn in ss.get("chat", []):
                with st.chat_message(turn["role"]):
                    st.write(turn["text"])
            q = st.chat_input("Ask about this video")
            if q:
                ss.chat.append({"role": "user", "text": q})
                hits = _retrieve(r["transcript"], q)
                if llm_available(settings):
                    ctx = "\n".join(f"[{fmt_ts(s.start)}] {s.text}" for s in hits)
                    out = llm_json(settings,
                        'Answer from the evidence only; cite timestamps like [mm:ss]. '
                        'Reply with JSON {"answer": "..."}.\n\n'
                        f"QUESTION: {q}\n\nEVIDENCE:\n{ctx}")
                    answer = out.get("answer", "No answer produced.")
                else:
                    answer = "No API key set — the closest transcript moments:\n\n" + "\n".join(
                        f"- [{fmt_ts(s.start)}]({yt_link(r['video_id'], s.start)}) {s.text[:120]}"
                        for s in hits)
                ss.chat.append({"role": "assistant", "text": answer})
                st.rerun()

    # Markdown export
    md = [f"# {meta['title']}", "", f"## TL;DR", "", summary["tldr"], "", "## Takeaways", ""]
    md += [f"- {t}" for t in summary["takeaways"]] + ["", "## Chapters", ""]
    for c in summary["chapters"]:
        md += [f"### [{fmt_ts(c['start'])}]({yt_link(r['video_id'], c['start'])}) {c['title']}",
               "", c.get("summary", ""), ""]
    st.download_button("Download summary (.md)", "\n".join(md),
                       file_name=f"clipsense-{r['video_id']}.md", mime="text/markdown")
