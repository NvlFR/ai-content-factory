"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import WaveSurfer from "wavesurfer.js"
import {
  Loader2,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Type,
  Palette,
  ArrowLeft,
  Download,
  Send,
  RefreshCw,
  Check,
} from "lucide-react"
import { api, distributionApi } from "@/lib/api"
import { Button } from "@/components/ui/button"

export default function EditorPage() {
  const params = useParams()
  const router = useRouter()
  const candidateId = params.id

  // Data State
  const [candidate, setCandidate] = useState<any>(null)
  const [transcript, setTranscript] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState("")

  // Playback State
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)

  // Refs
  const originalVideoRef = useRef<HTMLVideoElement>(null)
  const croppedVideoRef = useRef<HTMLVideoElement>(null)
  const waveformRef = useRef<HTMLDivElement>(null)
  const wavesurferRef = useRef<WaveSurfer | null>(null)

  // Style State
  const [fontSize, setFontSize] = useState(24)
  const [fontColor, setFontColor] = useState("#FFFFFF")
  const [bgColor, setBgColor] = useState("rgba(0,0,0,0.5)")

  // Publishing State
  const [publishing, setPublishing] = useState(false)
  const [publishSuccess, setPublishSuccess] = useState(false)

  useEffect(() => {
    fetchEditorData()
    return () => {
      if (wavesurferRef.current) {
        wavesurferRef.current.destroy()
      }
    }
  }, [candidateId])

  const fetchEditorData = async () => {
    try {
      setLoading(true)
      const res = await api.get(`/api/v1/videos/candidates/${candidateId}`)
      setCandidate(res.data)

      if (res.data.transcript_data) {
        setTranscript(res.data.transcript_data)
      }
    } catch (err) {
      setError("Failed to load editor data")
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handlePrepareEditor = async () => {
    try {
      setPreparing(true)
      await api.post(`/api/v1/videos/prepare_editor/${candidateId}`)
      
      // Poll for completion
      const pollInterval = setInterval(async () => {
        const res = await api.get(`/api/v1/videos/candidates/${candidateId}`)
        if (res.data.draft_video_path && res.data.transcript_data) {
          setCandidate(res.data)
          setTranscript(res.data.transcript_data)
          setPreparing(false)
          clearInterval(pollInterval)
          initWaveform(res.data.draft_video_path)
        }
      }, 3000)
      
      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        setPreparing(false)
      }, 300000)
    } catch (err) {
      setError("Failed to prepare editor")
      setPreparing(false)
    }
  }

  const initWaveform = useCallback((videoPath: string) => {
    if (!waveformRef.current || wavesurferRef.current) return

    const videoUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/${videoPath}`
    
    wavesurferRef.current = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: "#4a5568",
      progressColor: "#8b5cf6",
      cursorColor: "#ffffff",
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 60,
      normalize: true,
    })

    wavesurferRef.current.load(videoUrl)

    wavesurferRef.current.on("ready", () => {
      setDuration(wavesurferRef.current?.getDuration() || 0)
    })

    wavesurferRef.current.on("audioprocess", (time) => {
      setCurrentTime(time)
      syncVideos(time)
    })

    wavesurferRef.current.on("seeking", (time) => {
      setCurrentTime(time)
      syncVideos(time)
    })
  }, [])

  const syncVideos = (time: number) => {
    if (originalVideoRef.current) {
      originalVideoRef.current.currentTime = time
    }
    if (croppedVideoRef.current) {
      croppedVideoRef.current.currentTime = time
    }
  }

  const handlePlayPause = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause()
      setIsPlaying(!isPlaying)
    }
    
    if (originalVideoRef.current) {
      if (isPlaying) originalVideoRef.current.pause()
      else originalVideoRef.current.play()
    }
    if (croppedVideoRef.current) {
      if (isPlaying) croppedVideoRef.current.pause()
      else croppedVideoRef.current.play()
    }
  }

  const handleSeek = (seconds: number) => {
    const newTime = Math.max(0, Math.min(duration, currentTime + seconds))
    if (wavesurferRef.current) {
      wavesurferRef.current.seekTo(newTime / duration)
    }
    syncVideos(newTime)
    setCurrentTime(newTime)
  }

  const handleMuteToggle = () => {
    setIsMuted(!isMuted)
    if (wavesurferRef.current) {
      wavesurferRef.current.setMuted(!isMuted)
    }
    if (croppedVideoRef.current) {
      croppedVideoRef.current.muted = !isMuted
    }
  }

  const handleWordClick = (startTime: number) => {
    if (wavesurferRef.current && duration > 0) {
      wavesurferRef.current.seekTo(startTime / duration)
    }
    syncVideos(startTime)
    setCurrentTime(startTime)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const getCurrentWord = () => {
    return transcript.find(
      (word) => currentTime >= word.start && currentTime <= word.end
    )
  }

  const handlePublish = async (platform: string) => {
    if (!candidate?.is_rendered) {
      setError("Please render the clip first before publishing")
      return
    }
    
    try {
      setPublishing(true)
      // Find the clip ID associated with this candidate
      // For now, we'll use a placeholder
      await distributionApi.publish(candidate.id, platform, candidate.title)
      setPublishSuccess(true)
      setTimeout(() => setPublishSuccess(false), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to publish")
    } finally {
      setPublishing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center text-red-400">
        {error}
      </div>
    )
  }

  const videoUrl = candidate?.draft_video_path
    ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/${candidate.draft_video_path}`
    : ""

  const needsPreparation = !candidate?.draft_video_path || !candidate?.transcript_data

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex flex-col">
      {/* HEADER */}
      <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/dashboard")}
            className="text-neutral-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="font-bold">{candidate?.title || "Untitled Clip"}</h1>
            <p className="text-xs text-neutral-500">
              {formatTime(candidate?.start_time || 0)} - {formatTime(candidate?.end_time || 0)}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {publishSuccess && (
            <span className="text-green-400 text-sm flex items-center gap-1">
              <Check className="w-4 h-4" /> Published!
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePublish("tiktok")}
            disabled={publishing || !candidate?.is_rendered}
            className="border-neutral-700 text-white"
          >
            {publishing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
            Publish
          </Button>
        </div>
      </header>

      {needsPreparation ? (
        /* PREPARATION SCREEN */
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-bold mb-4">Editor Not Ready</h2>
            <p className="text-neutral-400 mb-6">
              We need to prepare the video and transcript for editing.
            </p>
            <Button
              onClick={handlePrepareEditor}
              disabled={preparing}
              className="bg-white text-neutral-900 hover:bg-neutral-200"
            >
              {preparing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Preparing... (This may take a few minutes)
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Prepare Editor
                </>
              )}
            </Button>
          </div>
        </div>
      ) : (
        /* MAIN EDITOR */
        <div className="flex-1 flex">
          {/* LEFT: ORIGINAL VIDEO */}
          <div className="w-1/4 border-r border-neutral-800 p-4 flex flex-col">
            <h3 className="text-sm font-medium text-neutral-400 mb-3">Original (16:9)</h3>
            <div className="bg-black rounded-lg overflow-hidden aspect-video">
              <video
                ref={originalVideoRef}
                className="w-full h-full object-contain"
                src={videoUrl}
                muted
              />
            </div>
            
            {/* STYLE CONTROLS */}
            <div className="mt-6 space-y-4">
              <h3 className="text-sm font-medium text-neutral-400 flex items-center gap-2">
                <Palette className="w-4 h-4" /> Subtitle Style
              </h3>
              
              <div>
                <label className="block text-xs text-neutral-500 mb-2">Font Size: {fontSize}px</label>
                <input
                  type="range"
                  min="16"
                  max="48"
                  value={fontSize}
                  onChange={(e) => setFontSize(parseInt(e.target.value))}
                  className="w-full accent-purple-500"
                />
              </div>
              
              <div>
                <label className="block text-xs text-neutral-500 mb-2">Text Color</label>
                <div className="flex gap-2">
                  {["#FFFFFF", "#FFFF00", "#00FFFF", "#FF00FF", "#00FF00"].map((c) => (
                    <button
                      key={c}
                      onClick={() => setFontColor(c)}
                      className={`w-8 h-8 rounded-full border-2 transition ${
                        fontColor === c ? "border-white scale-110" : "border-transparent"
                      }`}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* CENTER: CROPPED PREVIEW */}
          <div className="flex-1 flex flex-col items-center justify-center p-6 bg-neutral-900/50">
            <h3 className="text-sm font-medium text-neutral-400 mb-3">Preview (9:16)</h3>
            
            {/* PHONE FRAME */}
            <div className="relative bg-neutral-800 rounded-[2.5rem] p-3 shadow-2xl">
              <div className="relative w-[280px] aspect-[9/16] bg-black rounded-[2rem] overflow-hidden">
                {/* VIDEO */}
                <video
                  ref={croppedVideoRef}
                  className="w-full h-full object-cover"
                  src={videoUrl}
                  muted={isMuted}
                />
                
                {/* SUBTITLE OVERLAY */}
                <div className="absolute inset-0 pointer-events-none flex flex-col justify-end items-center pb-16 p-4">
                  {getCurrentWord() && (
                    <span
                      style={{
                        fontSize: `${fontSize}px`,
                        color: fontColor,
                        textShadow: "2px 2px 4px rgba(0,0,0,0.8)",
                        backgroundColor: bgColor,
                        padding: "4px 12px",
                        borderRadius: "4px",
                        fontWeight: "bold",
                      }}
                      className="animate-in fade-in zoom-in duration-100"
                    >
                      {getCurrentWord().word}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            {/* PLAYBACK CONTROLS */}
            <div className="mt-6 flex items-center gap-4">
              <button
                onClick={() => handleSeek(-5)}
                className="p-2 text-neutral-400 hover:text-white transition"
              >
                <SkipBack className="w-5 h-5" />
              </button>
              
              <button
                onClick={handlePlayPause}
                className="p-4 bg-white text-neutral-900 rounded-full hover:bg-neutral-200 transition"
              >
                {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-0.5" />}
              </button>
              
              <button
                onClick={() => handleSeek(5)}
                className="p-2 text-neutral-400 hover:text-white transition"
              >
                <SkipForward className="w-5 h-5" />
              </button>
              
              <button
                onClick={handleMuteToggle}
                className="p-2 text-neutral-400 hover:text-white transition"
              >
                {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </button>
              
              <span className="text-sm font-mono text-neutral-400">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>
            
            {/* WAVEFORM */}
            <div className="w-full max-w-2xl mt-6 bg-neutral-800 rounded-lg p-2">
              <div ref={waveformRef} />
            </div>
          </div>

          {/* RIGHT: TRANSCRIPT */}
          <div className="w-1/4 border-l border-neutral-800 p-4 flex flex-col">
            <h3 className="text-sm font-medium text-neutral-400 mb-3 flex items-center gap-2">
              <Type className="w-4 h-4" /> Transcript
            </h3>
            
            <div className="flex-1 overflow-y-auto space-y-1">
              {transcript.map((word, idx) => {
                const isActive = currentTime >= word.start && currentTime <= word.end
                
                return (
                  <div
                    key={idx}
                    onClick={() => handleWordClick(word.start)}
                    className={`p-2 rounded cursor-pointer transition text-sm ${
                      isActive
                        ? "bg-purple-600 text-white"
                        : "bg-neutral-800 hover:bg-neutral-700 text-neutral-300"
                    }`}
                  >
                    <span className="text-[10px] text-neutral-500 block mb-0.5">
                      {formatTime(word.start)}
                    </span>
                    <input
                      className="bg-transparent w-full outline-none"
                      value={word.word}
                      onChange={(e) => {
                        const newTranscript = [...transcript]
                        newTranscript[idx].word = e.target.value
                        setTranscript(newTranscript)
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
