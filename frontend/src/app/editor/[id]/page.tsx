"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { useParams } from "next/navigation";
import { Loader2, Play, Pause, Download, Type, Palette } from "lucide-react";

export default function EditorPage() {
  const params = useParams();
  const candidateId = params.id;

  const [candidate, setCandidate] = useState<any>(null);
  const [transcript, setTranscript] = useState<any[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Style State
  const [fontSize, setFontSize] = useState(24);
  const [fontColor, setFontColor] = useState("#FFFFFF");

  useEffect(() => {
    fetchEditorData();
  }, []);

const fetchEditorData = async () => {
  try {
    // 1. Ambil detail kandidat (termasuk path video draft & json transkrip)
    const res = await axios.get(
      `http://localhost:8000/api/v1/videos/candidates/${candidateId}`
    );
    setCandidate(res.data);

    // Jika transkrip sudah ada di DB, load ke state
    if (res.data.transcript_data) {
      setTranscript(res.data.transcript_data);
    } else {
      // Jika belum ada, panggil API prepare (Trigger Worker)
      // Note: Di real app, kita harus polling statusnya.
      // Untuk MVP ini, kita minta user klik tombol "Prepare Editor" dulu nanti.
    }
  } catch (err) {
    console.error(err);
  }
};

  // KITA BUTUH ENDPOINT GET CANDIDATE DETAIL DULU DI BACKEND!
  // Tahan dulu frontend ini. Kita balik ke Backend sebentar.

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 flex gap-6">
      {/* KIRI: STYLING */}
      <div className="w-1/4 bg-slate-800 rounded-xl p-6">
        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
          <Palette /> Styles
        </h2>

        <div className="mb-6">
          <label className="block text-xs uppercase text-slate-400 mb-2">
            Font Size
          </label>
          <input
            type="range"
            min="12"
            max="60"
            value={fontSize}
            onChange={(e) => setFontSize(parseInt(e.target.value))}
            className="w-full accent-indigo-500"
          />
        </div>

        <div className="mb-6">
          <label className="block text-xs uppercase text-slate-400 mb-2">
            Color
          </label>
          <div className="flex gap-2">
            {["#FFFFFF", "#FFFF00", "#00FFFF", "#FF00FF"].map((c) => (
              <button
                key={c}
                onClick={() => setFontColor(c)}
                className={`w-8 h-8 rounded-full border-2 ${
                  fontColor === c ? "border-white" : "border-transparent"
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* TENGAH: PREVIEW STAGE */}
      <div className="flex-1 flex flex-col items-center justify-center bg-black rounded-xl relative">
        <div className="relative aspect-[9/16] h-[80vh] bg-gray-900 rounded-lg overflow-hidden shadow-2xl border border-slate-700">
          {/* LAYER 1: VIDEO POLOS */}
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            src={
              candidate?.draft_video_path
                ? `http://localhost:8000/${candidate.draft_video_path}`
                : ""
            }
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          />

          {/* LAYER 2: SUBTITLE OVERLAY (HTML) */}
          <div className="absolute inset-0 pointer-events-none flex flex-col justify-end items-center pb-20 p-6 text-center">
            {transcript.map((word, idx) => {
              // Cek apakah kata ini sedang diucapkan?
              // Logika karaoke sederhana
              const isActive =
                currentTime >= word.start && currentTime <= word.end;
              if (!isActive) return null;

              return (
                <span
                  key={idx}
                  style={{
                    fontSize: `${fontSize}px`,
                    color: fontColor,
                    textShadow: "2px 2px 0 #000",
                    fontFamily: "sans-serif",
                    fontWeight: "bold",
                    backgroundColor: "rgba(0,0,0,0.5)",
                    padding: "4px 8px",
                    borderRadius: "4px",
                  }}
                  className="animate-in fade-in zoom-in duration-75"
                >
                  {word.word}
                </span>
              );
            })}
          </div>

          {/* CONTROLS */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-4 bg-slate-800/80 p-2 rounded-full backdrop-blur-md">
            <button
              onClick={() => {
                if (videoRef.current) {
                  if (isPlaying) videoRef.current.pause();
                  else videoRef.current.play();
                  setIsPlaying(!isPlaying);
                }
              }}
            >
              {isPlaying ? (
                <Pause className="w-6 h-6" />
              ) : (
                <Play className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* KANAN: TRANSCRIPT EDITOR */}
      <div className="w-1/4 bg-slate-800 rounded-xl p-6 overflow-y-auto">
        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
          <Type /> Transcript
        </h2>
        <div className="space-y-2">
          {transcript.map((item, idx) => (
            <div
              key={idx}
              className={`p-2 rounded text-sm cursor-pointer hover:bg-slate-700 transition ${
                currentTime >= item.start && currentTime <= item.end
                  ? "bg-indigo-600"
                  : "bg-slate-900"
              }`}
              onClick={() => {
                if (videoRef.current) {
                  videoRef.current.currentTime = item.start;
                  videoRef.current.play();
                  setIsPlaying(true);
                }
              }}
            >
              <span className="text-xs text-slate-400 block mb-1">
                {item.start.toFixed(2)}s
              </span>
              <input
                className="bg-transparent w-full outline-none text-white"
                value={item.word}
                onChange={(e) => {
                  const newT = [...transcript];
                  newT[idx].word = e.target.value;
                  setTranscript(newT);
                }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
