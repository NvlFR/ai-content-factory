"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import axios from "axios"
import {
  Loader2,
  PlayCircle,
  CheckCircle,
  Clock,
  Film,
  Scissors,
  LogOut,
  Settings,
  User,
} from "lucide-react"
import { useAuth } from "@/hooks/use-auth"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

export default function DashboardPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth()

  const [url, setUrl] = useState("")
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<any[]>([])
  const [selectedProject, setSelectedProject] = useState<any | null>(null)
  const [renderingId, setRenderingId] = useState<number | null>(null)
  const [isRendering, setIsRendering] = useState(false)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login")
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (isAuthenticated) {
      fetchHistory()
    }
  }, [isAuthenticated])

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isRendering) {
      interval = setInterval(() => {
        fetchHistory()
      }, 3000)
    }
    return () => clearInterval(interval)
  }, [isRendering])

  const fetchHistory = async () => {
    try {
      const res = await api.get("/api/v1/videos/")
      setHistory(res.data)

      if (selectedProject) {
        const updatedProject = res.data.find(
          (p: any) => p.id === selectedProject.id
        )
        if (updatedProject) {
          setSelectedProject(updatedProject)
        }
      }
    } catch (err) {
      console.error("Failed to load history", err)
    }
  }

  const handleProcess = async () => {
    if (!url) return
    setLoading(true)
    try {
      await api.post("/api/v1/videos/", { url })
      alert("Analysis Started! Check history below in a few minutes.")
      fetchHistory()
      setUrl("")
    } catch (error) {
      alert("Error starting process")
    } finally {
      setLoading(false)
    }
  }

  const handleRender = async (candidateId: number) => {
    setRenderingId(candidateId)
    setIsRendering(true)
    try {
      await api.post(`/api/v1/videos/render/${candidateId}`)
    } catch (err) {
      alert("Render failed")
      setIsRendering(false)
    } finally {
      setRenderingId(null)
    }
  }

  const handleLogout = () => {
    logout()
    router.push("/login")
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* HEADER */}
      <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center">
              <Film className="w-5 h-5 text-neutral-900" />
            </div>
            <span className="font-bold text-lg">AI Content Factory</span>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="/channels"
              className="text-sm text-neutral-400 hover:text-white transition"
            >
              Channels
            </a>
            <a
              href="/settings"
              className="text-sm text-neutral-400 hover:text-white transition"
            >
              <Settings className="w-4 h-4" />
            </a>

            <div className="flex items-center gap-3 pl-4 border-l border-neutral-700">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium">{user?.name || "User"}</p>
                <p className="text-xs text-neutral-500">{user?.credits_balance || 0} credits</p>
              </div>
              <Avatar className="h-8 w-8">
                <AvatarImage src={user?.picture || ""} alt={user?.name || ""} />
                <AvatarFallback>
                  <User className="w-4 h-4" />
                </AvatarFallback>
              </Avatar>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-neutral-400 hover:text-white"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* INPUT CARD */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 mb-8 max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold mb-4">Create New Content</h2>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Paste YouTube URL..."
              className="flex-1 px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-white focus:border-transparent outline-none text-white placeholder-neutral-500"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
            />
            <Button
              onClick={handleProcess}
              disabled={loading || !url}
              className="bg-white hover:bg-neutral-200 text-neutral-900"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Scissors className="w-4 h-4 mr-2" />
              )}
              Analyze
            </Button>
          </div>
        </div>

        {/* PROJECT EDITOR MODAL */}
        {selectedProject && (
          <div className="bg-neutral-900 rounded-xl border border-neutral-800 p-6 mb-12">
            <div className="flex justify-between items-center mb-6 border-b border-neutral-800 pb-4">
              <div>
                <h2 className="text-xl font-bold">Project Editor</h2>
                <p className="text-sm text-neutral-500 truncate max-w-md">
                  {selectedProject.youtube_url}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedProject(null)
                  setIsRendering(false)
                }}
                className="text-neutral-400 hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* DRAFTS */}
              <div>
                <h3 className="font-semibold text-neutral-300 mb-4 flex items-center gap-2">
                  <Scissors className="w-4 h-4" /> AI Suggestions
                </h3>
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                  {selectedProject.candidates.map((c: any) => (
                    <div
                      key={c.id}
                      className="border border-neutral-700 rounded-lg p-4 hover:border-neutral-500 transition bg-neutral-800/50"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="bg-white/10 text-white text-xs font-bold px-2 py-1 rounded">
                          Score: {c.viral_score}
                        </span>
                        <span className="text-xs text-neutral-500 font-mono">
                          {c.start_time}s - {c.end_time}s
                        </span>
                      </div>
                      <h4 className="font-bold mb-1">{c.title}</h4>
                      <p className="text-xs text-neutral-400 mb-4 italic">
                        "{c.description}"
                      </p>

                      {c.is_rendered ? (
                        <button
                          disabled
                          className="w-full py-2 bg-neutral-700 text-neutral-300 rounded-lg text-xs font-bold flex justify-center gap-2 cursor-default"
                        >
                          <CheckCircle className="w-4 h-4" /> Rendered
                        </button>
                      ) : (
                        <button
                          onClick={() => handleRender(c.id)}
                          disabled={renderingId === c.id}
                          className="w-full py-2 bg-white hover:bg-neutral-200 text-neutral-900 rounded-lg text-xs font-bold flex justify-center gap-2 disabled:opacity-50"
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
                    <p className="text-neutral-500 text-sm">
                      AI is still analyzing...
                    </p>
                  )}
                </div>
              </div>

              {/* RESULT CLIPS */}
              <div>
                <h3 className="font-semibold text-neutral-300 mb-4 flex items-center gap-2">
                  <Film className="w-4 h-4" /> Ready to Post
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {selectedProject.clips.map((clip: any, idx: number) => (
                    <div
                      key={idx}
                      className="relative rounded-lg overflow-hidden bg-black aspect-[9/16] group"
                    >
                      <video
                        className="w-full h-full object-cover"
                        controls
                        playsInline
                      >
                        <source
                          src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/${clip.file_path}`}
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
                    <div className="col-span-2 h-40 border-2 border-dashed border-neutral-700 rounded-lg flex items-center justify-center text-neutral-500 text-sm flex-col gap-2">
                      <Film className="w-8 h-8 opacity-20" />
                      <span>No rendered clips yet.</span>
                      {isRendering && (
                        <span className="text-neutral-400 animate-pulse text-xs">
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
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5" /> Recent Activity
        </h2>
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-neutral-800/50 text-neutral-400 font-medium border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Source</th>
                <th className="px-6 py-4">Drafts</th>
                <th className="px-6 py-4">Rendered</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {history.map((project) => (
                <tr key={project.id} className="hover:bg-neutral-800/50 transition">
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-bold ${
                        project.status.includes("completed")
                          ? "bg-white/10 text-white"
                          : project.status === "analyzing"
                          ? "bg-neutral-700 text-neutral-300 animate-pulse"
                          : "bg-neutral-800 text-neutral-400"
                      }`}
                    >
                      {project.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-neutral-300 max-w-xs truncate">
                    <a
                      href={project.youtube_url}
                      target="_blank"
                      className="hover:underline"
                    >
                      {project.youtube_url}
                    </a>
                  </td>
                  <td className="px-6 py-4 font-mono text-neutral-500">
                    {project.candidates.length}
                  </td>
                  <td className="px-6 py-4 font-mono text-neutral-500">
                    {project.clips.length}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedProject(project)}
                      className="border-neutral-700 text-neutral-300 hover:bg-neutral-800"
                    >
                      Open Editor
                    </Button>
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-neutral-500">
                    No projects yet. Paste a YouTube URL above to get started!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
