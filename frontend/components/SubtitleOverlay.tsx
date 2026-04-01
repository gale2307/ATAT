"use client";

type Subtitle = {
  id: string;
  startTime: number;
  endTime: number;
  text: string;
};

type Props = {
  subtitles: Subtitle[];
  currentTime: number;
};

export default function SubtitleOverlay({ subtitles, currentTime }: Props) {
  const active = subtitles.filter(
    (s) => currentTime >= s.startTime && currentTime <= s.endTime
  );

  if (active.length === 0) return null;

  return (
    <div className="absolute bottom-10 left-0 right-0 flex flex-col items-center gap-1 pointer-events-none">
      {active.map((s) => (
        <div
          key={s.id}
          className="bg-black/75 text-white text-lg px-3 py-1 rounded max-w-2xl text-center"
        >
          {s.text}
        </div>
      ))}
    </div>
  );
}
