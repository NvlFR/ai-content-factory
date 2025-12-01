"use client";

import { useState } from "react";
import axios from "axios";
import { Loader2, PlayCircle, CheckCircle } from "lucide-react";
import dynamic from "next/dynamic";

// FIX 1: Gunakan Dynamic Import dengan ssr: false
const ReactPlayer = dynamic(() => import("react-player"), {
  ssr: false,
}) as any;

export default function Dashboard() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [resultVideo, setResultVideo] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const handleProcess = async () => {
    if (!url) return;
    setLoading(true);
    setStatus("processing");
    setLogs(["🚀 Initializing job..."]);
    setResultVideo(null);

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

        if (state === "SUCCESS") {
          clearInterval(interval);
          setStatus("completed");
          setLoading(false);
          addLog("✅ Process completed successfully!");

          const clips = res.data.result.generated_clips;
          if (clips && clips.length > 0) {
            setResultVideo(clips[0]);
          }
        } else if (state === "FAILURE") {
          clearInterval(interval);
          setStatus("failed");
          setLoading(false);
          addLog("❌ Job failed.");
        } else {
          addLog(`⏳ Status: ${state}...`);
        }
      } catch (err) {
        clearInterval(interval);
        setStatus("failed");
      }
    }, 2000);
  };

  const addLog = (msg: string) => {
    setLogs((prev) => [...prev, msg]);
  };

  return (
    <div className="min-h-screen p-8 max-w-5xl mx-auto">
      <header className="mb-10 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          AI Content Factory
        </h1>
        <p className="text-slate-500 mt-2">
          Turn long YouTube videos into viral shorts automatically.
        </p>
      </header>

      <div className="bg-white shadow-sm border border-slate-200 rounded-xl p-6 mb-8">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* LOGS */}
        <div className="bg-slate-50 rounded-xl p-6 border border-slate-200 h-96 overflow-y-auto font-mono text-sm">
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
                className="text-slate-600 border-l-2 border-slate-300 pl-3 py-1"
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

        {/* PREVIEW */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col items-center justify-center min-h-[400px]">
          {status === "completed" && resultVideo ? (
            <div className="w-full flex flex-col items-center animate-in fade-in duration-500">
              <div className="flex items-center gap-2 text-green-600 mb-4 font-medium">
                <CheckCircle className="w-5 h-5" /> Clip Ready
              </div>

             {/* FIX 3: Ganti ReactPlayer dengan Native HTML5 Video */}
               <div className="relative rounded-xl overflow-hidden shadow-2xl border-4 border-slate-900 bg-black w-[250px] aspect-[9/16]">
                  <video 
                    key={resultVideo} // PENTING: Agar React me-reset player saat video baru jadi
                    className="w-full h-full object-cover"
                    controls 
                    autoPlay 
                    muted 
                    loop
                    playsInline
                  >
                    <source src={`http://localhost:8000/${resultVideo}`} type="video/mp4" />
                    Your browser does not support the video tag.
                  </video>
               </div>
              <div className="mt-6 text-center">
                <p className="text-xs text-slate-400 mb-2">
                  Original Path: {resultVideo}
                </p>
                <button
                  onClick={() =>
                    window.open(
                      `http://localhost:8000/${resultVideo}`,
                      "_blank"
                    )
                  }
                  className="text-indigo-600 hover:text-indigo-800 text-sm font-medium hover:underline"
                >
                  Download .MP4
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center text-slate-400">
              <div className="bg-slate-50 w-24 h-40 mx-auto rounded mb-3 border border-slate-200 flex items-center justify-center">
                <PlayCircle className="w-8 h-8 opacity-20" />
              </div>
              <p>Output preview will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
