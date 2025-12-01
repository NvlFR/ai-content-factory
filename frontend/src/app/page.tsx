"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { Loader2, PlayCircle, CheckCircle, Clock, Film } from "lucide-react";

export default function Dashboard() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>("idle");
  const [resultVideo, setResultVideo] = useState<string[] | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  // State untuk History
  const [history, setHistory] = useState<any[]>([]);

  // Load History saat halaman dibuka
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/v1/videos/");
      setHistory(res.data);
    } catch (err) {
      console.error("Gagal load history", err);
    }
  };

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
            setResultVideo(clips);
            fetchHistory(); // Refresh tabel history
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
        setLoading(false);
      }
    }, 2000);
  };

  const addLog = (msg: string) => setLogs((prev) => [...prev, msg]);

  // Fungsi untuk memuat ulang project dari history
  const loadFromHistory = (clips: any[]) => {
    const paths = clips.map((c) => c.file_path);
    setResultVideo(paths);
    setStatus("completed");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen p-8 max-w-6xl mx-auto pb-20">
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        {/* LOGS */}
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

        {/* PREVIEW */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 flex flex-col items-center min-h-[500px]">
          {status === "completed" && resultVideo ? (
            <div className="w-full">
              <div className="flex items-center gap-2 text-green-600 mb-6 font-medium justify-center bg-green-50 py-2 rounded-lg border border-green-100">
                <CheckCircle className="w-5 h-5" /> Processing Complete:{" "}
                {resultVideo.length} Clips Generated
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {resultVideo.map((clip, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col items-center bg-slate-50 p-3 rounded-xl border border-slate-100"
                  >
                    <div className="relative rounded-lg overflow-hidden shadow-md bg-black w-full aspect-[9/16]">
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
                      </video>
                    </div>
                    <div className="mt-3 w-full text-center">
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
            </div>
          )}
        </div>
      </div>

      {/* --- HISTORY SECTION --- */}
      <div className="mt-12">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5" /> Recent Projects
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
              <tr>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Video Source</th>
                <th className="px-6 py-4">Created At</th>
                <th className="px-6 py-4">Clips</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {history.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-8 text-center text-slate-400"
                  >
                    No history found. Start creating!
                  </td>
                </tr>
              ) : (
                history.map((project) => (
                  <tr key={project.id} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-4">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          project.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : project.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {project.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-700 max-w-xs truncate">
                      <a
                        href={project.youtube_url}
                        target="_blank"
                        className="hover:text-indigo-600 hover:underline flex items-center gap-2"
                      >
                        <Film className="w-4 h-4" /> {project.youtube_url}
                      </a>
                    </td>
                    <td className="px-6 py-4 text-slate-500">
                      {new Date(project.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-700">
                      {project.clips.length} Clips
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => loadFromHistory(project.clips)}
                        disabled={project.clips.length === 0}
                        className="text-indigo-600 font-medium hover:text-indigo-800 disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        View Results
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
