import { useEffect, useRef } from "react";
import { usePlayer } from "./PlayerContext";

declare global {
  interface Window {
    YT?: {
      Player: new (el: HTMLElement, opts: object) => { seekTo: (s: number, a: boolean) => void; playVideo: () => void };
      ready: (cb: () => void) => void;
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

let apiLoading: Promise<void> | null = null;
function loadYouTubeApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve();
  if (!apiLoading) {
    apiLoading = new Promise((resolve) => {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        prev?.();
        resolve();
      };
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    });
  }
  return apiLoading;
}

/** Docked YouTube player inside a dark filmstrip inset. Seeks on any
 *  TimestampLink click via PlayerContext. */
export function PlayerDock({ videoId }: { videoId: string }) {
  const mount = useRef<HTMLDivElement>(null);
  const { registerPlayer } = usePlayer();

  useEffect(() => {
    let player: { seekTo: (s: number, a: boolean) => void; playVideo: () => void } | null = null;
    let cancelled = false;
    loadYouTubeApi().then(() => {
      if (cancelled || !mount.current || !window.YT) return;
      player = new window.YT.Player(mount.current, {
        videoId,
        width: "100%",
        height: "100%",
        playerVars: { rel: 0, modestbranding: 1 },
      });
      registerPlayer((s) => {
        player?.seekTo(s, true);
        player?.playVideo();
      });
    });
    return () => {
      cancelled = true;
      registerPlayer(() => {});
    };
  }, [videoId, registerPlayer]);

  return (
    <div className="rounded-lg bg-strip p-2 shadow-lg">
      <div className="sprockets h-4 rounded-t-sm" aria-hidden="true" />
      <div className="aspect-video overflow-hidden bg-black [&_iframe]:h-full [&_iframe]:w-full">
        <div ref={mount} />
      </div>
      <div className="sprockets h-4 rounded-b-sm" aria-hidden="true" />
    </div>
  );
}
