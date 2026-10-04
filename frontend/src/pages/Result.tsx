import { useEffect, useState } from "react";
import { ChatPanel } from "../components/ChatPanel";
import { PlayerDock } from "../components/PlayerDock";
import { TimestampLink } from "../components/TimestampLink";
import { downloadMarkdown, toMarkdown } from "../lib/markdown";
import { fmtTs } from "../lib/time";
import { getResult } from "../services/api";
import type { VideoResult } from "../types/contracts";

type Tab = "summary" | "evidence" | "chat";

export function Result({ jobId, onReset }: { jobId: string; onReset: () => void }) {
  const [result, setResult] = useState<VideoResult | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("summary");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getResult(jobId)
      .then(setResult)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the result"));
  }, [jobId]);

  if (error) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-xl flex-col items-start justify-center px-6">
        <h1 className="font-display text-2xl font-black">The result didn't load</h1>
        <p className="mt-3 text-ink-soft">{error}</p>
        <button onClick={onReset} className="mt-6 rounded-md bg-ink px-5 py-2.5 font-semibold text-ground hover:bg-playhead">
          Start over
        </button>
      </main>
    );
  }
  if (!result) {
    return (
      <main className="flex min-h-dvh items-center justify-center">
        <p className="timecode text-ink-soft blink">loading result…</p>
      </main>
    );
  }

  const r = result;

  async function copyMarkdown() {
    await navigator.clipboard.writeText(toMarkdown(r));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      {/* header */}
      <header className="no-print mb-6 flex flex-wrap items-center gap-3">
        <button onClick={onReset} className="timecode text-sm text-ink-soft hover:text-playhead">
          ← new video
        </button>
        <span className="timecode ml-auto rounded-sm bg-verified/10 px-2.5 py-1 text-xs text-verified">
          {(r.critic.faithfulness * 100).toFixed(0)}% faithful · {r.critic.checked} claims checked
        </span>
        <button onClick={copyMarkdown} className="rounded-md border border-line bg-card px-3.5 py-1.5 text-sm font-semibold hover:border-ink-soft">
          {copied ? "Copied" : "Copy Markdown"}
        </button>
        <button onClick={() => downloadMarkdown(r)} className="rounded-md border border-line bg-card px-3.5 py-1.5 text-sm font-semibold hover:border-ink-soft">
          Download .md
        </button>
        <button onClick={() => window.print()} className="rounded-md border border-line bg-card px-3.5 py-1.5 text-sm font-semibold hover:border-ink-soft">
          Print / PDF
        </button>
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)]">
        {/* left: the document */}
        <article>
          <h1 className="font-display text-3xl leading-tight font-black tracking-tight sm:text-4xl">
            {r.title}
          </h1>
          <p className="timecode mt-2 text-sm text-ink-soft">
            {r.channel} · {fmtTs(r.duration)} · {r.transcript_source}
          </p>

          <p
            className="mt-6 pl-4 text-lg leading-relaxed"
            style={{
              borderLeft: "4px solid",
              borderImage:
                "linear-gradient(to bottom, var(--color-playhead), var(--color-vision), var(--color-chapter)) 1",
            }}
          >
            {r.tldr}
          </p>

          <h2 className="timecode mt-10 mb-3 text-xs tracking-widest text-ink-soft uppercase">
            Key takeaways
          </h2>
          <ul className="space-y-2">
            {r.takeaways.map((t, i) => {
              const dots = ["bg-playhead", "bg-vision", "bg-chapter", "bg-audio", "bg-critic", "bg-ingest"];
              return (
                <li key={i} className="flex gap-3">
                  <span aria-hidden="true" className={`mt-2 size-1.5 shrink-0 rounded-full ${dots[i % dots.length]}`} />
                  <span>{t}</span>
                </li>
              );
            })}
          </ul>

          <h2 className="timecode mt-10 mb-4 text-xs tracking-widest text-ink-soft uppercase">
            Chapters
          </h2>
          <ol className="space-y-6 border-l border-line">
            {r.chapters.map((c, i) => (
              <li key={i} className="relative pl-6">
                <span aria-hidden="true" className="absolute top-2 -left-[3px] size-1.5 rounded-full bg-chapter" />
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <TimestampLink seconds={c.start} />
                  <h3 className="font-display text-lg font-bold">{c.title}</h3>
                  <span className="timecode text-xs text-ink-soft">→ {fmtTs(c.end)}</span>
                </div>
                <p className="mt-2 leading-relaxed text-ink/90">{c.summary}</p>
                <ul className="mt-2 space-y-1 text-sm text-ink-soft">
                  {c.key_points.map((k, j) => (
                    <li key={j}>· {k}</li>
                  ))}
                </ul>
                {c.evidence_timestamps.length > 0 && (
                  <p className="mt-2 flex flex-wrap items-baseline gap-1.5 text-xs text-ink-soft">
                    <span className="timecode uppercase">evidence</span>
                    {c.evidence_timestamps.map((t) => (
                      <TimestampLink key={t} seconds={t} muted />
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </article>

        {/* right: player + tabs */}
        <aside className="no-print lg:sticky lg:top-8 lg:self-start">
          <PlayerDock videoId={r.video_id} />

          <nav className="mt-5 flex gap-1 border-b border-line" aria-label="Result sections">
            {(
              [
                ["summary", "Fact-check", "border-critic"],
                ["evidence", "On-screen", "border-vision"],
                ["chat", "Ask", "border-chapter"],
              ] as [Tab, string, string][]
            ).map(([key, label, border]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                aria-current={tab === key}
                className={`-mb-px border-b-2 px-4 py-2 text-sm font-semibold transition-colors
                  ${tab === key ? `${border} text-ink` : "border-transparent text-ink-soft hover:text-ink"}`}
              >
                {label}
              </button>
            ))}
          </nav>

          <div className="mt-4 lg:max-h-[46vh] lg:min-h-[320px] lg:overflow-y-auto">
            {tab === "summary" && (
              <ul className="space-y-3">
                {r.critic.results.map((c, i) => (
                  <li key={i} className="rounded-md bg-card p-3.5">
                    <div className="flex items-start gap-2.5">
                      <span
                        className={`timecode mt-0.5 shrink-0 rounded-sm px-1.5 py-0.5 text-[11px]
                          ${c.supported ? "bg-verified/10 text-verified" : "bg-playhead/10 text-playhead"}`}
                      >
                        {c.supported ? "SUPPORTED" : "UNSUPPORTED"}
                      </span>
                      <p className="text-sm font-medium">{c.claim}</p>
                    </div>
                    <p className="mt-2 text-sm text-ink-soft">{c.evidence}</p>
                    {c.revision_needed && (
                      <p className="timecode mt-1.5 text-xs text-caution">revised by the critic</p>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {tab === "evidence" && (
              <ul className="space-y-3">
                {r.vision.map((v, i) => (
                  <li key={i} className="rounded-md bg-card p-3.5">
                    <div className="flex items-baseline gap-2.5">
                      <TimestampLink seconds={v.timestamp} />
                      <span
                        className={`timecode rounded-sm px-1.5 py-0.5 text-[11px] tracking-wider uppercase ${
                          {
                            slide: "bg-vision/10 text-vision",
                            code: "bg-ingest/10 text-ingest",
                            chart: "bg-critic/10 text-critic",
                            talking_head: "bg-line/50 text-ink-soft",
                            other: "bg-line/50 text-ink-soft",
                          }[v.frame_type]
                        }`}
                      >
                        {v.frame_type.replace("_", " ")}
                      </span>
                      <span className="timecode ml-auto text-xs text-ink-soft">
                        {(v.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    {v.ocr_text && (
                      <pre className="mt-2 overflow-x-auto rounded-sm bg-strip px-3 py-2 font-mono text-[13px] text-ground">
                        {v.ocr_text}
                      </pre>
                    )}
                    {v.description && <p className="mt-2 text-sm text-ink-soft">{v.description}</p>}
                  </li>
                ))}
              </ul>
            )}

            {tab === "chat" && <ChatPanel jobId={jobId} />}
          </div>
        </aside>
      </div>
    </main>
  );
}
