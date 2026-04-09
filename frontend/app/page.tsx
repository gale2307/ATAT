"use client";

import { useState } from "react";
import UrlInput from "@/components/UrlInput";
import ModelSelector from "@/components/ModelSelector";
import JobStatus from "@/components/JobStatus";
import VideoPlayer from "@/components/VideoPlayer";
import { submitJob } from "@/lib/api";

export type JobState = {
  id: string | null;
  status: "idle" | "queued" | "processing" | "done" | "error";
  progress: number;
  outputUrl: string | null;   // local video file (video mode)
  subtitleUrl: string | null; // VTT for native <track> (video mode)
  srtUrl: string | null;      // SRT for download + YouTube overlay
  embedUrl: string | null;    // original YouTube URL (audio_only mode)
  error: string | null;
};

export type ModelConfig = {
  sttModel: string;
  translationEngine: string;
  domain: string;
  srcLang: string;
  tgtLang: string;
  downloadMode: string;
};

export default function Home() {
  const [job, setJob] = useState<JobState>({
    id: null,
    status: "idle",
    progress: 0,
    outputUrl: null,
    subtitleUrl: null,
    srtUrl: null,
    embedUrl: null,
    error: null,
  });

  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    sttModel: "whisper-large-v3",
    translationEngine: "qwen-mt",
    domain: "general",
    srcLang: "ko",
    tgtLang: "en",
    downloadMode: "audio_only",
  });

  async function handleSubmit(url: string) {
    setJob({ id: null, status: "queued", progress: 0, outputUrl: null, subtitleUrl: null, srtUrl: null, embedUrl: null, error: null });
    try {
      const { jobId } = await submitJob(url, modelConfig);
      setJob((prev) => ({ ...prev, id: jobId }));
    } catch (err) {
      setJob((prev) => ({ ...prev, status: "error", error: String(err) }));
    }
  }

  const showPlayer = job.status === "done" && (job.outputUrl || job.embedUrl);

  return (
    <main className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-white">ATAT</h1>
        <p className="text-gray-400 mt-1">Auto Transcribe &amp; Translate — subtitle any video</p>
      </header>

      <UrlInput onSubmit={handleSubmit} disabled={job.status === "queued" || job.status === "processing"} />
      <ModelSelector config={modelConfig} onChange={setModelConfig} />

      {job.status !== "idle" && (
        <JobStatus
          job={job}
          onUpdate={(update) => setJob((prev) => ({ ...prev, ...update }))}
        />
      )}

      {showPlayer && (
        <VideoPlayer
          src={job.outputUrl}
          subtitleUrl={job.subtitleUrl}
          srtUrl={job.srtUrl}
          embedUrl={job.embedUrl}
        />
      )}
    </main>
  );
}
