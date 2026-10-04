import { useEffect, useState } from "react";
import { getStatus } from "../services/api";
import type { JobStatus, Stage } from "../types/contracts";
import { STAGES } from "../types/contracts";

const TRACKS: Record<Stage, { track: string; label: string; color: string; bar: string }> = {
  ingesting: { track: "INGEST", label: "Fetching video and audio", color: "text-ingest", bar: "bg-ingest" },
  listening: { track: "AUDIO", label: "Listening — transcript", color: "text-audio", bar: "bg-audio" },
  watching: { track: "VISION", label: "Watching — slides, code, charts", color: "text-vision", bar: "bg-vision" },
  summarizing: { track: "TEXT", label: "Summarizing — chapters and takeaways", color: "text-chapter", bar: "bg-chapter" },
  verifying: { track: "CRITIC", label: "Verifying claims against evidence", color: "text-critic", bar: "bg-critic" },
};

/** The pipeline rendered as editor tracks with a sweeping playhead —
 *  judges watch the agents work like a live edit session. */
export function Progress({
  jobId,
  onDone,
  onError,
}: {
  jobId: string;
  onDone: () => void;
  onError: (msg: string) => void;
}) {
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const s = await getStatus(jobId);
        if (stop) return;
        setStatus(s);
        if (s.state === "done") onDone();
        else if (s.state === "error") onError(s.error ?? "Processing failed");
        else setTimeout(tick, 700);
      } catch (e) {
        if (!stop) onError(e instanceof Error ? e.message : "Lost connection to the backend");
      }
    };
    tick();
    return () => {
      stop = true;
    };
  }, [jobId, onDone, onError]);

  const activeIdx = status ? STAGES.indexOf(status.stage) : 0;
  const pct = Math.round((status?.progress ?? 0) * 100);

  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center px-6 py-16">
      <header className="mb-10 flex items-baseline justify-between gap-4">
        <h1 className="font-display text-3xl font-black tracking-tight">Reading your video</h1>
        <span className="timecode text-sm text-ink-soft">
          <span className="text-playhead blink">●</span> {pct}%
        </span>
      </header>

      <div className="rounded-lg bg-strip p-5 shadow-lg" role="status" aria-live="polite">
        <ol className="flex flex-col gap-1.5">
          {STAGES.map((stage, i) => {
            const meta = TRACKS[stage];
            const state = i < activeIdx ? "done" : i === activeIdx ? "active" : "pending";
            return (
              <li
                key={stage}
                className={`relative flex items-center gap-4 overflow-hidden rounded-sm px-4 py-3
                  ${state === "active" ? "bg-strip-soft" : ""}`}
              >
                {state === "active" && (
                  <span
                    aria-hidden="true"
                    className={`absolute top-0 bottom-0 w-0.5 ${meta.bar}`}
                    style={{ animation: "playhead-sweep 2.4s linear infinite" }}
                  />
                )}
                <span
                  className={`timecode w-16 shrink-0 text-xs tracking-widest
                    ${state === "pending" ? "text-ink-soft/50" : meta.color}`}
                >
                  {meta.track}
                </span>
                <span
                  className={`flex-1 text-sm
                    ${state === "pending" ? "text-ground/35" : state === "done" ? "text-ground/70" : "text-ground"}`}
                >
                  {state === "active" && status ? status.detail : meta.label}
                </span>
                <span className="timecode shrink-0 text-xs">
                  {state === "done" && <span className="text-verified">done</span>}
                  {state === "active" && <span className={`${meta.color} blink`}>rolling</span>}
                  {state === "pending" && <span className="text-ground/30">queued</span>}
                </span>
              </li>
            );
          })}
        </ol>
      </div>

      <p className="mt-6 text-sm text-ink-soft">
        Transcript is required; vision and audio enrich it when the video has visual content. Longer
        videos take longer — the result keeps every claim pinned to its timestamp.
      </p>
    </main>
  );
}
