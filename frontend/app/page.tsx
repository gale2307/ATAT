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
  outputUrl: string | null;
  subtitleUrl: string | null;  // VTT — for browser <track>
  srtUrl: string | null;       // SRT — for download
  error: string | null;
};

export type ModelConfig = {
  sttModel: string;
  translationEngine: string;
  domain: string;
  srcLang: string;
  tgtLang: string;
};

export default function Home() {
  const [job, setJob] = useState<JobState>({
    id: null,
    status: "idle",
    progress: 0,
    outputUrl: null,
    subtitleUrl: null,
    srtUrl: null,
    error: null,
  });

  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    sttModel: "whisper-large-v3",
    translationEngine: "qwen-mt",
    domain: "general",
    srcLang: "ko",
    tgtLang: "en",
  });

  async function handleSubmit(url: string) {
    setJob({ id: null, status: "queued", progress: 0, outputUrl: null, subtitleUrl: null, error: null });
    try {
      const { jobId } = await submitJob(url, modelConfig);
      setJob((prev) => ({ ...prev, id: jobId }));
    } catch (err) {
      setJob((prev) => ({ ...prev, status: "error", error: String(err) }));
    }
  }

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

      {job.outputUrl && <VideoPlayer src={job.outputUrl} subtitleUrl={job.subtitleUrl} srtUrl={job.srtUrl} />}
    </main>
  );
}
