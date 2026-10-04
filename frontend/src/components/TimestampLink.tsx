import { fmtTs } from "../lib/time";
import { usePlayer } from "./PlayerContext";

/** The atom of ClipSense: a monospace timecode that jumps the player. */
export function TimestampLink({ seconds, muted = false }: { seconds: number; muted?: boolean }) {
  const { seekTo } = usePlayer();
  return (
    <button
      type="button"
      onClick={() => seekTo(seconds)}
      title={`Jump to ${fmtTs(seconds)}`}
      className={`timecode inline-block rounded-xs px-1 text-[0.8em] leading-none align-baseline
        transition-colors hover:bg-playhead hover:text-white
        ${muted ? "text-ink-soft bg-line/40" : "text-playhead bg-playhead/10"}`}
    >
      {fmtTs(seconds)}
    </button>
  );
}
