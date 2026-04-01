"use client";

import { useEffect, useRef } from "react";
import { createSocket } from "@/lib/socket";
import type { JobState } from "@/app/page";

type Props = {
  job: JobState;
  onUpdate: (update: Partial<JobState>) => void;
};

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued...",
  processing: "Processing...",
  done: "Done",
  error: "Error",
};

export default function JobStatus({ job, onUpdate }: Props) {
  const socketRef = useRef<ReturnType<typeof createSocket> | null>(null);

  useEffect(() => {
    if (!job.id) return;

    const socket = createSocket();
    socketRef.current = socket;

    socket.emit("subscribe", { jobId: job.id });

    socket.on("job:progress", (data: { jobId: string; progress: number; status: string }) => {
      if (data.jobId !== job.id) return;
      onUpdate({ progress: data.progress, status: data.status as JobState["status"] });
    });

    socket.on("job:done", (data: { jobId: string; outputUrl: string; subtitleUrl: string; srtUrl: string | null }) => {
      if (data.jobId !== job.id) return;
      onUpdate({ status: "done", outputUrl: data.outputUrl, subtitleUrl: data.subtitleUrl, srtUrl: data.srtUrl, progress: 100 });
    });

    socket.on("job:error", (data: { jobId: string; error: string }) => {
      if (data.jobId !== job.id) return;
      onUpdate({ status: "error", error: data.error });
    });

    return () => {
      socket.disconnect();
    };
  }, [job.id]);

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{STATUS_LABELS[job.status] ?? job.status}</span>
        {job.status === "processing" && (
          <span className="text-sm text-gray-400">{job.progress}%</span>
        )}
      </div>

      {(job.status === "queued" || job.status === "processing") && (
        <div className="w-full bg-gray-700 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${job.progress}%` }}
          />
        </div>
      )}

      {job.status === "error" && (
        <p className="text-red-400 text-sm">{job.error}</p>
      )}

      {job.status === "done" && (job.srtUrl || job.subtitleUrl) && (
        <a
          href={job.srtUrl ?? job.subtitleUrl ?? ""}
          download
          className="inline-block text-sm text-blue-400 hover:text-blue-300 underline"
        >
          Download SRT
        </a>
      )}
    </div>
  );
}
