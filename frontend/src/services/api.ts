import type { JobStatus, QAResponse, Stage, SummaryDepth, VideoResult } from "../types/contracts";
import { STAGES } from "../types/contracts";
import { MOCK_QA, MOCK_RESULT, MOCK_STAGE_DETAIL } from "./mockData";

/** Backend base URL. Unset -> demo mode (simulated pipeline + sample result).
 *  "proxy" -> relative /api through the vite dev proxy; any URL -> that host. */
const RAW_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
export const DEMO_MODE = RAW_BASE === "";
const API_BASE: string = RAW_BASE === "proxy" ? "" : RAW_BASE.replace(/\/+$/, "");

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return (await r.json()) as T;
}

// ---------------------------------------------------------------- real client

async function realCreateJob(url: string, depth: SummaryDepth): Promise<{ job_id: string }> {
  return http("/api/jobs", { method: "POST", body: JSON.stringify({ url, depth }) });
}
async function realGetStatus(jobId: string): Promise<JobStatus> {
  return http(`/api/jobs/${jobId}`);
}
async function realGetResult(jobId: string): Promise<VideoResult> {
  return http(`/api/jobs/${jobId}/result`);
}
async function realAsk(jobId: string, question: string): Promise<QAResponse> {
  return http(`/api/jobs/${jobId}/qa`, { method: "POST", body: JSON.stringify({ question }) });
}

// ---------------------------------------------------------------- demo client

const STAGE_SECONDS: Record<Stage, number> = {
  ingesting: 3,
  listening: 4,
  watching: 6,
  summarizing: 5,
  verifying: 4,
};
const TOTAL_SECONDS = Object.values(STAGE_SECONDS).reduce((a, b) => a + b, 0);

const demoJobs = new Map<string, { startedAt: number; videoId: string }>();

function demoCreateJob(url: string): { job_id: string } {
  const id = `demo-${Date.now()}`;
  demoJobs.set(id, { startedAt: Date.now(), videoId: url });
  return { job_id: id };
}

function demoGetStatus(jobId: string): JobStatus {
  let job = demoJobs.get(jobId);
  if (!job) {
    // e.g. ?screen=progress preview links — start the clock on first poll
    job = { startedAt: Date.now(), videoId: jobId };
    demoJobs.set(jobId, job);
  }
  const elapsed = (Date.now() - job.startedAt) / 1000;
  let acc = 0;
  for (const stage of STAGES) {
    const dur = STAGE_SECONDS[stage];
    if (elapsed < acc + dur) {
      const within = (elapsed - acc) / dur;
      const lines = MOCK_STAGE_DETAIL[stage];
      const detail = lines[Math.min(lines.length - 1, Math.floor(within * lines.length))];
      return {
        job_id: jobId,
        state: "running",
        stage,
        progress: Math.min(0.99, elapsed / TOTAL_SECONDS),
        detail,
      };
    }
    acc += dur;
  }
  return { job_id: jobId, state: "done", stage: "verifying", progress: 1, detail: "Summary verified" };
}

// ---------------------------------------------------------------- public API

export async function createJob(url: string, depth: SummaryDepth): Promise<{ job_id: string }> {
  return DEMO_MODE ? demoCreateJob(url) : realCreateJob(url, depth);
}

export async function getStatus(jobId: string): Promise<JobStatus> {
  return DEMO_MODE ? demoGetStatus(jobId) : realGetStatus(jobId);
}

export async function getResult(jobId: string): Promise<VideoResult> {
  return DEMO_MODE ? MOCK_RESULT : realGetResult(jobId);
}

export async function askQuestion(jobId: string, question: string): Promise<QAResponse> {
  if (!DEMO_MODE) return realAsk(jobId, question);
  await new Promise((r) => setTimeout(r, 1200));
  return MOCK_QA.default;
}
