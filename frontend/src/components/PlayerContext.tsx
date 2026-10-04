import { createContext, useCallback, useContext, useRef, type ReactNode } from "react";

/** One shared seek channel: any timestamp in the UI jumps the docked player. */
interface PlayerApi {
  seekTo: (seconds: number) => void;
  registerPlayer: (fn: (seconds: number) => void) => void;
}

const Ctx = createContext<PlayerApi | null>(null);

export function PlayerProvider({ children }: { children: ReactNode }) {
  const playerFn = useRef<((s: number) => void) | null>(null);
  const registerPlayer = useCallback((fn: (s: number) => void) => {
    playerFn.current = fn;
  }, []);
  const seekTo = useCallback((s: number) => {
    playerFn.current?.(s);
  }, []);
  return <Ctx.Provider value={{ seekTo, registerPlayer }}>{children}</Ctx.Provider>;
}

export function usePlayer(): PlayerApi {
  const api = useContext(Ctx);
  if (!api) throw new Error("usePlayer must be used inside PlayerProvider");
  return api;
}
