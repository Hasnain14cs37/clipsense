import { useRef, useState, type FormEvent } from "react";
import { askQuestion } from "../services/api";
import type { QAResponse } from "../types/contracts";
import { TimestampLink } from "./TimestampLink";

interface Turn {
  question: string;
  response?: QAResponse;
}

export function ChatPanel({ jobId }: { jobId: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  async function handleAsk(e: FormEvent) {
    e.preventDefault();
    const q = draft.trim();
    if (!q || busy) return;
    setDraft("");
    setBusy(true);
    setTurns((t) => [...t, { question: q }]);
    requestAnimationFrame(() => logRef.current?.scrollTo({ top: 1e6 }));
    try {
      const r = await askQuestion(jobId, q);
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, response: r } : turn)));
    } catch {
      setTurns((t) =>
        t.map((turn, i) =>
          i === t.length - 1
            ? {
                ...turn,
                response: {
                  answer: "The backend didn't respond. Check it's running, then ask again.",
                  citations: [],
                  confidence: 0,
                },
              }
            : turn,
        ),
      );
    } finally {
      setBusy(false);
      requestAnimationFrame(() => logRef.current?.scrollTo({ top: 1e6, behavior: "smooth" }));
    }
  }

  return (
    <section aria-label="Ask about this video" className="flex h-full flex-col">
      <div ref={logRef} className="min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        {turns.length === 0 && (
          <p className="text-sm text-ink-soft">
            Ask anything about this video — answers cite the exact moment, so you can jump there and
            check. Try “why is the sigmoid used?”
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i}>
            <p className="mb-2 font-semibold">{t.question}</p>
            {!t.response ? (
              <p className="timecode text-sm text-ink-soft blink">searching the timeline…</p>
            ) : (
              <div className="rounded-md bg-card p-3.5 text-[15px] leading-relaxed">
                <p>{t.response.answer}</p>
                {t.response.citations.length > 0 && (
                  <ul className="mt-3 space-y-1.5 border-t border-line pt-2.5">
                    {t.response.citations.map((c, j) => (
                      <li key={j} className="flex items-baseline gap-2 text-sm text-ink-soft">
                        <TimestampLink seconds={c.timestamp} />
                        <span className="timecode shrink-0 text-xs uppercase">{c.source_type}</span>
                        <span className="min-w-0 truncate">“{c.excerpt}”</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      <form onSubmit={handleAsk} className="mt-4 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about this video"
          aria-label="Your question"
          className="min-w-0 flex-1 rounded-md border border-line bg-card px-3.5 py-2.5 text-[15px]
            placeholder:text-ink-soft/50"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-ink px-5 py-2.5 font-semibold text-ground transition-colors
            hover:bg-playhead disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </section>
  );
}
