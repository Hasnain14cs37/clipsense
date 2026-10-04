import { useCallback, useState } from "react";
import { PlayerProvider } from "./components/PlayerContext";
import { Home } from "./pages/Home";
import { Progress } from "./pages/Progress";
import { Result } from "./pages/Result";
import { createJob } from "./services/api";
import type { SummaryDepth } from "./types/contracts";

/** The app is the job's state machine: home -> processing -> result.
 *  No router needed for the demo flow. */
type Screen =
  | { name: "home"; error?: string }
  | { name: "processing"; jobId: string }
  | { name: "result"; jobId: string };

/** Demo-mode deep links for design review: ?screen=progress / ?screen=result */
function initialScreen(): Screen {
  const preview = new URLSearchParams(window.location.search).get("screen");
  if (preview === "progress") return { name: "processing", jobId: `preview-${Date.now()}` };
  if (preview === "result") return { name: "result", jobId: "preview" };
  return { name: "home" };
}

export default function App() {
  const [screen, setScreen] = useState<Screen>(initialScreen);

  const submit = useCallback(async (url: string, depth: SummaryDepth) => {
    try {
      const { job_id } = await createJob(url, depth);
      setScreen({ name: "processing", jobId: job_id });
    } catch (e) {
      setScreen({
        name: "home",
        error: e instanceof Error ? e.message : "Could not reach the backend",
      });
    }
  }, []);

  return (
    <PlayerProvider>
      {screen.name === "home" && (
        <>
          {screen.error && (
            <div role="alert" className="bg-playhead px-6 py-2.5 text-center text-sm font-semibold text-white">
              {screen.error} — check the backend is running, then try again.
            </div>
          )}
          <Home onSubmit={submit} />
        </>
      )}
      {screen.name === "processing" && (
        <Progress
          jobId={screen.jobId}
          onDone={() => setScreen({ name: "result", jobId: screen.jobId })}
          onError={(msg) => setScreen({ name: "home", error: msg })}
        />
      )}
      {screen.name === "result" && (
        <Result jobId={screen.jobId} onReset={() => setScreen({ name: "home" })} />
      )}
    </PlayerProvider>
  );
}
