"use client";

import { useState } from "react";

type Props = {
  onSubmit: (url: string) => void;
  disabled: boolean;
};

export default function UrlInput({ onSubmit, disabled }: Props) {
  const [url, setUrl] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    onSubmit(url.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Paste YouTube URL..."
        disabled={disabled}
        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
        required
      />
      <button
        type="submit"
        disabled={disabled || !url.trim()}
        className="px-5 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Transcribe
      </button>
    </form>
  );
}
