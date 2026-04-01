"use client";

import { useEffect, useRef } from "react";
import Hls from "hls.js";

type Props = {
  src: string;
  subtitleUrl: string | null;  // VTT
  srtUrl?: string | null;
};

export default function VideoPlayer({ src, subtitleUrl }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    // Remove any existing tracks
    while (video.firstChild) video.removeChild(video.firstChild);

    const isHls = src.includes(".m3u8");
    if (isHls && Hls.isSupported()) {
      const hls = new Hls();
      hlsRef.current = hls;
      hls.loadSource(src);
      hls.attachMedia(video);
    } else {
      video.src = src;
    }

    // Add subtitle track after src is set so the browser registers it
    if (subtitleUrl) {
      const track = document.createElement("track");
      track.kind = "subtitles";
      track.label = "English";
      track.srclang = "en";
      track.src = subtitleUrl;
      track.default = true;
      video.appendChild(track);
    }

    return () => {
      hlsRef.current?.destroy();
    };
  }, [src, subtitleUrl]);

  return (
    <div className="rounded-xl overflow-hidden bg-black aspect-video">
      <video
        ref={videoRef}
        controls
        className="w-full h-full"
        crossOrigin="anonymous"
      />
    </div>
  );
}
