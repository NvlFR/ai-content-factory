"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import {
  Loader2,
  PlayCircle,
  CheckCircle,
  Clock,
  Film,
  Scissors,
  Play,
} from "lucide-react";

export default function Dashboard() {
  // --- STATE MANAGEMENT ---
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  // State untuk Editor & Review
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  const [renderingId, setRenderingId] = useState<number | null>(null);

  // State untuk Auto-Refresh (Polling)
  const [isRendering, setIsRendering] = useState(false);

  // --- EFFECTS ---

  // 1. Load History saat pertama kali buka
  useEffect(() => {
    fetchHistory();
  }, []);

  // 2. Auto-Refresh Logic (Hanya jalan jika ada proses rendering)
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRendering) {
      // Cek setiap 3 detik
      interval = setInterval(() => {
        fetchHistory();
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [isRendering]);

  // --- ACTIONS ---

  const fetchHistory = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/v1/videos/");
      setHistory(res.data);

      // LOGIC PENTING: Update data Editor jika sedang terbuka
      // Agar user bisa melihat video muncul secara real-time tanpa tutup-buka modal
      if (selectedProject) {
        const updatedProject = res.data.find(
          (p: any) => p.id === selectedProject.id
        );
        if (updatedProject) {
          setSelectedProject(updatedProject);

          // Cek apakah jumlah klip bertambah? Jika ya, matikan loading di tombol
          if (updatedProject.clips.length > selectedProject.clips.length) {
            // Opsional: Matikan global rendering state jika semua kandidat sudah jadi
            // Tapi untuk sekarang kita biarkan user mematikan manual atau timeout
          }
        }
      }
    } catch (err) {
      console.error("Gagal load history", err);
    }
  };

  const handleProcess = async () => {
    if (!url) return;
    setLoading(true);
    try {
      await axios.post("http://localhost:8000/api/v1/videos/", { url });
      alert("Analysis Started! Check history below in a few minutes.");
      fetchHistory();
      setUrl("");
    } catch (error) {
      alert("Error starting process");
    } finally {
      setLoading(false);
    }
  };

  const handleRender = async (candidateId: number) => {
    setRenderingId(candidateId);
    setIsRendering(true); // Mulai polling otomatis
    try {
      await axios.post(
        `http://localhost:8000/api/v1/videos/render/${candidateId}`
      );
      // Tidak perlu alert, biarkan UI update sendiri
    } catch (err) {
      alert("Render failed");
      setIsRendering(false);
    } finally {
      setRenderingId(null);
    }
  };

  // --- RENDER UI ---

  return (
    <div className="min-h-screen p-8 max-w-6xl mx-auto pb-20">
      <header className="mb-10 flex flex-col items-center text-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          AI Content Factory
        </h1>
        <div className="flex gap-4 mt-4">
          <a
            href="/channels"
            className="text-sm font-medium text-indigo-600 bg-indigo-50 px-4 py-2 rounded-full hover:bg-indigo-100 transition"
          >
            Manage Channels
          </a>
        </div>
      </header>

      {/* INPUT CARD */}
      <div className="bg-white shadow-sm border border-slate-200 rounded-xl p-6 mb-8 max-w-3xl mx-auto">
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Paste YouTube URL manually..."
            className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
          />
          <button
            onClick={handleProcess}
            disabled={loading || !url}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-6 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Scissors className="w-4 h-4" />
            )}
            Analyze
          </button>
        </div>
      </div>

      {/* PROJECT EDITOR MODAL (Jika ada project dipilih) */}
      {selectedProject && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6 mb-12 animate-in fade-in slide-in-from-bottom-4">
          <div className="flex justify-between items-center mb-6 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-800">
                Project Editor
              </h2>
              <p className="text-sm text-slate-500 truncate max-w-md">
                {selectedProject.youtube_url}
              </p>
            </div>
            <button
              onClick={() => {
                setSelectedProject(null);
                setIsRendering(false);
              }}
              className="text-slate-400 hover:text-slate-600"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* KOLOM KIRI: DRAFTS */}
            <div>
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <Scissors className="w-4 h-4" /> AI Suggestions (Drafts)
              </h3>
              <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                {selectedProject.candidates.map((c: any) => (
                  <div
                    key={c.id}
                    className="border border-slate-200 rounded-lg p-4 hover:border-indigo-300 transition bg-slate-50"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-1 rounded">
                        Score: {c.viral_score}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">
                        {c.start_time}s - {c.end_time}s
                      </span>
                    </div>
                    <h4 className="font-bold text-slate-800 mb-1">{c.title}</h4>
                    <p className="text-xs text-slate-600 mb-4 italic">
                      "{c.description}"
                    </p>

                    {c.is_rendered ? (
                      <button
                        disabled
                        className="w-full py-2 bg-green-100 text-green-700 rounded-lg text-xs font-bold flex justify-center gap-2 cursor-default"
                      >
                        <CheckCircle className="w-4 h-4" /> Rendered
                      </button>
                    ) : (
                      <button
                        onClick={() => handleRender(c.id)}
                        disabled={renderingId === c.id}
                        className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold flex justify-center gap-2 disabled:opacity-50"
                      >
                        {renderingId === c.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <PlayCircle className="w-4 h-4" />
                        )}
                        Render This Clip
                      </button>
                    )}
                  </div>
                ))}
                {selectedProject.candidates.length === 0 && (
                  <p className="text-slate-400 text-sm">
                    AI is still analyzing...
                  </p>
                )}
              </div>
            </div>

            {/* KOLOM KANAN: RESULT CLIPS */}
            <div>
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <Film className="w-4 h-4" /> Ready to Post
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {selectedProject.clips.map((clip: any, idx: number) => (
                  <div
                    key={idx}
                    className="relative rounded-lg overflow-hidden bg-black aspect-[9/16] shadow-md group"
                  >
                    <video
                      className="w-full h-full object-cover"
                      controls
                      playsInline
                    >
                      <source
                        src={`http://localhost:8000/${clip.file_path}`}
                        type="video/mp4"
                      />
                    </video>
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2 opacity-0 group-hover:opacity-100 transition">
                      <p className="text-white text-xs font-medium truncate">
                        {clip.title}
                      </p>
                    </div>
                  </div>
                ))}
                {selectedProject.clips.length === 0 && (
                  <div className="col-span-2 h-40 border-2 border-dashed border-slate-200 rounded-lg flex items-center justify-center text-slate-400 text-sm flex-col gap-2">
                    <Film className="w-8 h-8 opacity-20" />
                    <span>No rendered clips yet.</span>
                    {isRendering && (
                      <span className="text-indigo-500 animate-pulse text-xs">
                        Processing in background...
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* HISTORY TABLE */}
      <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
        <Clock className="w-5 h-5" /> Recent Activity
      </h2>
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
            <tr>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Source</th>
              <th className="px-6 py-4">Drafts</th>
              <th className="px-6 py-4">Rendered</th>
              <th className="px-6 py-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {history.map((project) => (
              <tr key={project.id} className="hover:bg-slate-50 transition">
                <td className="px-6 py-4">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-bold ${
                      project.status.includes("completed")
                        ? "bg-green-100 text-green-700"
                        : project.status === "analyzing"
                        ? "bg-blue-100 text-blue-700 animate-pulse"
                        : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {project.status.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-700 max-w-xs truncate">
                  <a
                    href={project.youtube_url}
                    target="_blank"
                    className="hover:underline"
                  >
                    {project.youtube_url}
                  </a>
                </td>
                <td className="px-6 py-4 font-mono text-slate-500">
                  {project.candidates.length}
                </td>
                <td className="px-6 py-4 font-mono text-slate-500">
                  {project.clips.length}
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => setSelectedProject(project)}
                    className="bg-white border border-slate-300 text-slate-700 px-3 py-1 rounded-md hover:bg-slate-50 font-medium transition"
                  >
                    Open Editor
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
