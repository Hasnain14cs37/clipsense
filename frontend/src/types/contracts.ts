/** Data contracts — must mirror the execution plan §6.2 and backend/app/schemas. */

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

export type FrameType = "slide" | "code" | "chart" | "talking_head" | "other";

export interface VisionEvidence {
  timestamp: number;
  frame_type: FrameType;
  ocr_text: string;
  description: string;
  confidence: number;
}

export interface SummaryChapter {
  title: string;
  start: number;
  end: number;
  summary: string;
  key_points: string[];
  evidence_timestamps: number[];
}

export interface CriticResult {
  claim: string;
  supported: boolean;
  evidence: string;
  confidence: number;
  revision_needed: boolean;
}

export interface Citation {
  timestamp: number;
  source_type: "transcript" | "vision" | "summary";
  excerpt: string;
}

export interface QAResponse {
  answer: string;
  citations: Citation[];
  confidence: number;
}

/** Pipeline stages shown on the Progress screen, in order. */
export const STAGES = ["ingesting", "listening", "watching", "summarizing", "verifying"] as const;
export type Stage = (typeof STAGES)[number];

export interface JobStatus {
  job_id: string;
  state: "queued" | "running" | "done" | "error";
  stage: Stage;
  /** 0..1 within the whole job */
  progress: number;
  detail: string;
  error?: string;
}

export type SummaryDepth = "brief" | "standard" | "deep";

export interface VideoResult {
  video_id: string;
  title: string;
  channel: string;
  duration: number;
  transcript_source: "youtube-captions" | "faster-whisper" | "groq-whisper";
  tldr: string;
  takeaways: string[];
  chapters: SummaryChapter[];
  vision: VisionEvidence[];
  critic: {
    faithfulness: number;
    checked: number;
    results: CriticResult[];
  };
}
