"use client";

import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";

type Segment = { start: number; end: number; text: string };

type Props = {
  src: string | null;
  subtitleUrl: string | null;
  srtUrl: string | null;
  embedUrl: string | null;
};

// ---------------------------------------------------------------------------
// SRT parser
// ---------------------------------------------------------------------------

function parseSrtTime(t: string): number {
  const [hms, ms] = t.trim().split(",");
  const [h, m, s] = hms.split(":").map(Number);
  return h * 3600 + m * 60 + s + Number(ms) / 1000;
}

function parseSrt(srt: string): Segment[] {
  return srt
    .trim()
    .split(/\n\n+/)
    .flatMap((block) => {
      const lines = block.split("\n");
      const timeLine = lines.find((l) => l.includes("-->"));
      if (!timeLine) return [];
      const [startStr, endStr] = timeLine.split(" --> ");
      const text = lines
        .slice(lines.indexOf(timeLine) + 1)
        .join(" ")
        .trim();
      if (!text) return [];
      return [{ start: parseSrtTime(startStr), end: parseSrtTime(endStr), text }];
    });
}

// ---------------------------------------------------------------------------
// YouTube IFrame player
// ---------------------------------------------------------------------------

declare global {
  interface Window {
    YT: typeof YT;
    onYouTubeIframeAPIReady: () => void;
  }
}

function extractVideoId(url: string): string | null {
  const match = url.match(
    /(?:youtube\.com\/(?:watch\?v=|live\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
  );
  return match ? match[1] : null;
}

function loadYouTubeApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve();
  return new Promise((resolve) => {
    window.onYouTubeIframeAPIReady = resolve;
    if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    }
  });
}

// ---------------------------------------------------------------------------
// YouTube player component
// ---------------------------------------------------------------------------

function YouTubePlayer({ embedUrl, srtUrl }: { embedUrl: string; srtUrl: string | null }) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YT.Player | null>(null);
  const rafRef = useRef<number>(0);
  const [subtitle, setSubtitle] = useState("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Track fullscreen state — intercept if the YouTube iframe steals fullscreen
  useEffect(() => {
    const onChange = () => {
      const el = document.fullscreenElement;
      if (el && el !== wrapperRef.current && wrapperRef.current?.contains(el)) {
        // Iframe went fullscreen inside our wrapper — hand it back to the wrapper
        document.exitFullscreen().then(() => wrapperRef.current?.requestFullscreen());
        return;
      }
      setIsFullscreen(el === wrapperRef.current);
    };
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      wrapperRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }

  // Fetch and parse SRT
  useEffect(() => {
    if (!srtUrl) return;
    fetch(srtUrl)
      .then((r) => r.text())
      .then((text) => setSegments(parseSrt(text)))
      .catch(console.error);
  }, [srtUrl]);

  // Mount YouTube IFrame player
  useEffect(() => {
    const videoId = extractVideoId(embedUrl);
    if (!videoId || !containerRef.current) return;

    const playerId = `yt-${videoId}`;

    loadYouTubeApi().then(() => {
      if (playerRef.current) {
        playerRef.current.destroy();
      }

      // Replace container content with a plain div for the player to attach to
      if (containerRef.current) {
        containerRef.current.innerHTML = `<div id="${playerId}"></div>`;
      }

      playerRef.current = new window.YT.Player(playerId, {
        videoId,
        width: "100%",
        height: "100%",
        playerVars: { rel: 0, modestbranding: 1, fs: 0 },
      });
    });

    return () => {
      cancelAnimationFrame(rafRef.current);
      playerRef.current?.destroy();
      playerRef.current = null;
    };
  }, [embedUrl]);

  // Sync subtitles to player time via rAF
  useEffect(() => {
    if (!segments.length) return;

    const tick = () => {
      const time = playerRef.current?.getCurrentTime?.() ?? 0;
      const active = segments.find((s) => time >= s.start && time < s.end);
      setSubtitle(active?.text ?? "");
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(rafRef.current);
  }, [segments]);

  return (
    <div
      ref={wrapperRef}
      className={`relative overflow-hidden bg-black ${isFullscreen ? "w-screen h-screen" : "rounded-xl aspect-video"}`}
    >
      <div ref={containerRef} className="w-full h-full" />

      {subtitle && (
        <div className="absolute bottom-14 left-0 right-0 flex justify-center pointer-events-none">
          <span className="bg-black/70 text-white text-sm sm:text-base px-3 py-1 rounded max-w-[90%] text-center leading-snug">
            {subtitle}
          </span>
        </div>
      )}

      {/* Custom fullscreen button — sits above YouTube controls */}
      <button
        onClick={toggleFullscreen}
        className="absolute bottom-2 right-2 text-white bg-black/60 hover:bg-black/80 rounded px-2 py-1 text-xs pointer-events-auto z-10"
        title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
      >
        {isFullscreen ? "↙ Exit" : "↗ Fullscreen"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// HTML5 player component (video mode)
// ---------------------------------------------------------------------------

function Html5Player({ src, subtitleUrl }: { src: string; subtitleUrl: string | null }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    hlsRef.current?.destroy();
    hlsRef.current = null;
    while (video.firstChild) video.removeChild(video.firstChild);

    if (src.includes(".m3u8") && Hls.isSupported()) {
      const hls = new Hls();
      hlsRef.current = hls;
      hls.loadSource(src);
      hls.attachMedia(video);
    } else {
      video.src = src;
    }

    if (subtitleUrl) {
      const track = document.createElement("track");
      track.kind = "subtitles";
      track.label = "English";
      track.srclang = "en";
      track.src = subtitleUrl;
      track.default = true;
      video.appendChild(track);
    }

    return () => hlsRef.current?.destroy();
  }, [src, subtitleUrl]);

  return (
    <div className="rounded-xl overflow-hidden bg-black aspect-video">
      <video ref={videoRef} controls className="w-full h-full" crossOrigin="anonymous" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Unified VideoPlayer
// ---------------------------------------------------------------------------

export default function VideoPlayer({ src, subtitleUrl, srtUrl, embedUrl }: Props) {
  if (embedUrl) {
    return <YouTubePlayer embedUrl={embedUrl} srtUrl={srtUrl} />;
  }
  if (src) {
    return <Html5Player src={src} subtitleUrl={subtitleUrl} />;
  }
  return null;
}
