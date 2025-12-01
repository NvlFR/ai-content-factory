"use client";

import { useState } from "react";
import axios from "axios";
import { Loader2, PlayCircle, CheckCircle } from "lucide-react";

export default function Dashboard() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");

  // Update: Tipe datanya sekarang Array of Strings (string[]) karena klipnya banyak
  const [resultVideo, setResultVideo] = useState<string[] | null>(null);

  const [logs, setLogs] = useState<string[]>([]);

  const handleProcess = async () => {
    if (!url) return;
    setLoading(true);
    setStatus("processing");
    setLogs(["🚀 Initializing job..."]);
    setResultVideo(null); // Reset hasil sebelumnya

    try {
      const res = await axios.post("http://localhost:8000/api/v1/videos/", {
        url,
      });
      const id = res.data.task_id;
      setTaskId(id);
      addLog(`Job ID: ${id} created.`);
      pollStatus(id);
    } catch (error) {
      console.error(error);
      setStatus("failed");
      addLog("❌ Error connecting to server.");
      setLoading(false);
    }
  };

  const pollStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(
          `http://localhost:8000/api/v1/videos/${id}`
        );
        const state = res.data.status;

        // Update Log jika ada progress info
        if (res.data.progress && typeof res.data.progress === "object") {
          // Bisa tambah logika update log detail disini jika perlu
        }

        if (state === "SUCCESS") {
          clearInterval(interval);
          setStatus("completed");
          setLoading(false);
          addLog("✅ Process completed successfully!");

          const clips = res.data.result.generated_clips;
          // Pastikan clips ada isinya
          if (clips && clips.length > 0) {
            setResultVideo(clips); // Simpan Array Video
          }
        } else if (state === "FAILURE") {
          clearInterval(interval);
          setStatus("failed");
          setLoading(false);
          addLog("❌ Job failed.");
        } else {
          // Status polling biasa
          addLog(`⏳ Status: ${state}...`);
        }
      } catch (err) {
        clearInterval(interval);
        setStatus("failed");
        setLoading(false);
      }
    }, 2000);
  };

  const addLog = (msg: string) => {
    // Tampilkan 5 log terakhir saja biar rapi, atau semua juga boleh
    setLogs((prev) => [...prev, msg]);
  };

  return (
    <div className="min-h-screen p-8 max-w-6xl mx-auto">
      <header className="mb-10 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          AI Content Factory
        </h1>
        <p className="text-slate-500 mt-2">
          Turn long YouTube videos into viral shorts automatically.
        </p>
      </header>

      {/* INPUT SECTION */}
      <div className="bg-white shadow-sm border border-slate-200 rounded-xl p-6 mb-8 max-w-3xl mx-auto">
        <label className="block text-sm font-medium text-slate-700 mb-2">
          YouTube Video URL
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="https://www.youtube.com/watch?v=..."
            className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none transition"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
          />
          <button
            onClick={handleProcess}
            disabled={loading || !url}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-6 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50 transition"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <PlayCircle className="w-4 h-4" />
            )}
            Process Video
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* KOLOM KIRI: LOGS (Lebar 1 kolom) */}
        <div className="lg:col-span-1 bg-slate-50 rounded-xl p-6 border border-slate-200 h-[500px] overflow-y-auto font-mono text-sm shadow-inner">
          <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Loader2 className="w-4 h-4" /> System Logs
          </h3>
          <div className="space-y-2">
            {logs.length === 0 && (
              <span className="text-slate-400 italic">
                Waiting for input...
              </span>
            )}
            {logs.map((log, idx) => (
              <div
                key={idx}
                className="text-slate-600 border-l-2 border-slate-300 pl-3 py-1 text-xs break-words"
              >
                {log}
              </div>
            ))}
            {status === "completed" && (
              <div className="text-green-600 font-bold border-l-2 border-green-500 pl-3 py-1">
                🎉 All Done!
              </div>
            )}
          </div>
        </div>

        {/* KOLOM KANAN: PREVIEW GRID (Lebar 2 kolom) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 flex flex-col items-center min-h-[500px]">
          {status === "completed" && resultVideo ? (
            <div className="w-full">
              <div className="flex items-center gap-2 text-green-600 mb-6 font-medium justify-center bg-green-50 py-2 rounded-lg border border-green-100">
                <CheckCircle className="w-5 h-5" /> Processing Complete:{" "}
                {resultVideo.length} Clips Generated
              </div>

              {/* GRID VIDEO: Tampilkan semua klip */}

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {resultVideo.map((clip, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col items-center bg-slate-50 p-3 rounded-xl border border-slate-100"
                  >
                    <div className="relative rounded-lg overflow-hidden shadow-md bg-black w-full aspect-[9/16]">
                      {/* NATIVE HTML5 VIDEO TAG */}
                      <video
                        className="w-full h-full object-cover"
                        controls
                        playsInline
                        preload="metadata"
                      >
                        <source
                          src={`http://localhost:8000/${clip}`}
                          type="video/mp4"
                        />
                        Your browser does not support the video tag.
                      </video>
                    </div>

                    <div className="mt-3 w-full text-center">
                      <span className="block text-xs font-bold text-slate-700 mb-1">
                        Clip #{idx + 1}
                      </span>
                      <a
                        href={`http://localhost:8000/${clip}`}
                        target="_blank"
                        className="text-xs bg-white border border-slate-300 px-3 py-1 rounded-full text-indigo-600 hover:bg-indigo-50 transition block w-full"
                      >
                        Download MP4
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
              <div className="bg-slate-50 w-24 h-40 mx-auto rounded-lg mb-4 border border-slate-200 flex items-center justify-center shadow-sm">
                <PlayCircle className="w-10 h-10 opacity-20" />
              </div>
              <p>Output preview will appear here</p>
              {loading && (
                <p className="text-xs mt-2 animate-pulse text-indigo-400">
                  Processing video...
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
