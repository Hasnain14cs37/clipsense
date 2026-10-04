# ClipSense

*Don't watch it all. Understand it all.*

ClipSense is a multimodal, multi-agent AI system that turns long YouTube videos into
verified, timestamped knowledge: chapters, key takeaways, on-screen text (OCR), a
fact-checked summary, and a Q&A chat where every answer cites the exact moment in the video.

## How it works

```
URL → Ingestion → ┬ Transcript (captions → faster-whisper fallback)
                  ├ Vision     (frame sampling → pHash dedupe → EasyOCR + VLM)
                  └ Audio      (emphasis detection)
                        ↓
                  Fusion (one timeline) → Summarizer (map-reduce)
                        ↓
                  Critic (claims checked against evidence) → Q&A (RAG)
```

## Repo layout

| Path | What it is |
|---|---|
| `backend/` | FastAPI app + agents (Python). See `backend/requirements.txt`. |
| `frontend/` | React + Vite + Tailwind judge-facing UI. |
| `ClipSense_Colab_Groq_Complete_Backend.ipynb` | Original working prototype (Colab + Groq). |
| `CLIPSENSE_HANDOUT.md` | Project context handout (architecture + team plan). |

## Quick start

**Backend** (Python 3.12):

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env   # add GROQ_API_KEY for real summaries/critic/QA
python -m uvicorn app.main:app --port 8000
```

Without an API key the backend runs in a degraded transcript-only mode.
ffmpeg is required on PATH for the Groq ASR path and ingestion.

**Frontend** (Node 18+):

```bash
cd frontend
npm install
npm run dev              # demo mode with a simulated pipeline
```

Create `frontend/.env.local` with `VITE_API_BASE=proxy` to use the local backend
through the dev proxy, or set a full URL for a deployed backend.

**Standalone agent runners** (no server needed):

```bash
cd backend
python -m scripts.make_test_video                                  # synthetic slide video
python -m scripts.run_vision test_data/slides_test.mp4            # sampling+dedupe+OCR
python -m scripts.run_transcript --video-id jNQXAC9IVRw           # captions path
python -m scripts.run_transcript --audio test_data/speech_sample.wav --force-asr  # faster-whisper
```

## Configuration

Everything is environment-driven (`backend/.env.example`): provider choice
(`VISION_PROVIDER=groq|gemini|none`, `ASR_PROVIDER=faster_whisper|groq`), model IDs,
frame budgets and worker counts. Models are configurable because providers retire them.

## Team

Talha (Lead / Backend & Agents) · Husnain (CV & Perception) · Gul (Research & Docs) ·
Maheen (UI/UX) · Tooba (Pitch, QA & Submission)
