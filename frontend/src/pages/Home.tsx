import { useState, type FormEvent } from "react";
import { DEMO_MODE } from "../services/api";
import { extractVideoId } from "../lib/time";
import type { SummaryDepth } from "../types/contracts";

const DEPTHS: { value: SummaryDepth; label: string; hint: string }[] = [
  { value: "brief", label: "Brief", hint: "TL;DR + takeaways" },
  { value: "standard", label: "Standard", hint: "Chapters + evidence" },
  { value: "deep", label: "Deep", hint: "Everything + fact-check detail" },
];

export function Home({ onSubmit }: { onSubmit: (url: string, depth: SummaryDepth) => void }) {
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState<SummaryDepth>("standard");
  const [error, setError] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!extractVideoId(url)) {
      setError("Paste a full YouTube link, like youtube.com/watch?v=… or youtu.be/…");
      return;
    }
    setError("");
    onSubmit(url, depth);
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-4xl flex-col justify-center px-6 py-16">
      <header className="mb-14">
        <p className="timecode mb-6 text-sm text-ink-soft">
          <span className="text-playhead">REC</span> · multi-agent video intelligence
        </p>
        <h1 className="font-display text-[clamp(2.6rem,7vw,5.2rem)] leading-[0.98] font-black tracking-tight">
          Don't watch it all.
          <br />
          <span className="text-playhead">Understand</span> it all.
        </h1>
        <p className="mt-6 max-w-xl text-lg text-ink-soft">
          ClipSense reads a long video for you — <span className="font-semibold text-audio">the speech</span>,{" "}
          <span className="font-semibold text-vision">the slides</span>,{" "}
          <span className="font-semibold text-ingest">the code on screen</span> — and returns a{" "}
          <span className="font-semibold text-critic">verified summary</span> you can question, with
          every claim pinned to a <span className="font-semibold text-chapter">timestamp</span>.
        </p>
        <div className="mt-8 flex max-w-xl items-center gap-0.5" aria-hidden="true">
          {(
            [
              ["INGEST", "bg-ingest", "flex-[1]"],
              ["AUDIO", "bg-audio", "flex-[2]"],
              ["VISION", "bg-vision", "flex-[3]"],
              ["TEXT", "bg-chapter", "flex-[2.5]"],
              ["CRITIC", "bg-critic", "flex-[1.5]"],
            ] as const
          ).map(([label, bg, grow]) => (
            <span key={label} className={`${grow} min-w-0`}>
              <span className={`block h-1.5 rounded-full ${bg}`} />
              <span className="timecode mt-1.5 block truncate text-[10px] tracking-wider text-ink-soft">
                {label}
              </span>
            </span>
          ))}
        </div>
      </header>

      <form onSubmit={handleSubmit} aria-label="Summarize a video">
        <label htmlFor="yt-url" className="timecode mb-2 block text-xs tracking-widest text-ink-soft uppercase">
          YouTube link
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="yt-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v="
            className="timecode min-w-0 flex-1 rounded-md border border-line bg-card px-4 py-3.5
              text-[15px] placeholder:text-ink-soft/50"
          />
          <button
            type="submit"
            className="rounded-md bg-ink px-7 py-3.5 font-display font-bold text-ground
              transition-colors hover:bg-playhead"
          >
            Summarize
          </button>
        </div>
        {error && (
          <p role="alert" className="mt-2 text-sm text-playhead">
            {error}
          </p>
        )}

        <fieldset className="mt-6">
          <legend className="timecode mb-2 text-xs tracking-widest text-ink-soft uppercase">
            Summary depth
          </legend>
          <div className="flex flex-wrap gap-2">
            {DEPTHS.map((d) => (
              <label
                key={d.value}
                className={`cursor-pointer rounded-md border px-4 py-2.5 transition-colors
                  ${depth === d.value ? "border-ink bg-ink text-ground" : "border-line bg-card hover:border-ink-soft"}`}
              >
                <input
                  type="radio"
                  name="depth"
                  value={d.value}
                  checked={depth === d.value}
                  onChange={() => setDepth(d.value)}
                  className="sr-only"
                />
                <span className="font-semibold">{d.label}</span>
                <span className={`ml-2 text-sm ${depth === d.value ? "text-ground/70" : "text-ink-soft"}`}>
                  {d.hint}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      </form>

      <footer className="mt-16 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink-soft">
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="size-2 rounded-full bg-vision" />
          Transcript + slides + on-screen code
        </span>
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="size-2 rounded-full bg-critic" />
          Every claim checked against evidence
        </span>
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="size-2 rounded-full bg-chapter" />
          Ask questions, get timestamped answers
        </span>
        {DEMO_MODE && (
          <span className="timecode ml-auto rounded-sm bg-caution/15 px-2 py-0.5 text-xs text-caution">
            demo mode — sample video
          </span>
        )}
      </footer>
    </main>
  );
}
