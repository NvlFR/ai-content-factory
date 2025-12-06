import { create } from "zustand"

interface ClipCandidate {
  id: number
  project_id: string
  start_time: number
  end_time: number
  title: string
  description: string
  viral_score: number
  is_rendered: boolean
  draft_video_path: string | null
  transcript_data: Array<{ start: number; end: number; word: string }> | null
}

interface Project {
  id: string
  youtube_url: string
  status: string
  title: string | null
  thumbnail_url: string | null
  created_at: string
}

interface VideoState {
  // Current project
  currentProject: Project | null
  projects: Project[]
  
  // Editor state
  currentCandidate: ClipCandidate | null
  candidates: ClipCandidate[]
  
  // Playback sync
  currentTime: number
  isPlaying: boolean
  duration: number
  
  // Subtitle editing
  editedTranscript: Array<{ start: number; end: number; word: string }> | null
  
  // Actions
  setCurrentProject: (project: Project | null) => void
  setProjects: (projects: Project[]) => void
  setCurrentCandidate: (candidate: ClipCandidate | null) => void
  setCandidates: (candidates: ClipCandidate[]) => void
  setCurrentTime: (time: number) => void
  setIsPlaying: (playing: boolean) => void
  setDuration: (duration: number) => void
  setEditedTranscript: (transcript: Array<{ start: number; end: number; word: string }> | null) => void
  updateWord: (index: number, word: string) => void
  reset: () => void
}

export const useVideoStore = create<VideoState>((set, get) => ({
  currentProject: null,
  projects: [],
  currentCandidate: null,
  candidates: [],
  currentTime: 0,
  isPlaying: false,
  duration: 0,
  editedTranscript: null,

  setCurrentProject: (project) => set({ currentProject: project }),
  setProjects: (projects) => set({ projects }),
  setCurrentCandidate: (candidate) => set({ 
    currentCandidate: candidate,
    editedTranscript: candidate?.transcript_data || null
  }),
  setCandidates: (candidates) => set({ candidates }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setDuration: (duration) => set({ duration: duration }),
  setEditedTranscript: (transcript) => set({ editedTranscript: transcript }),
  
  updateWord: (index, word) => {
    const transcript = get().editedTranscript
    if (transcript && transcript[index]) {
      const updated = [...transcript]
      updated[index] = { ...updated[index], word }
      set({ editedTranscript: updated })
    }
  },
  
  reset: () => set({
    currentProject: null,
    currentCandidate: null,
    candidates: [],
    currentTime: 0,
    isPlaying: false,
    duration: 0,
    editedTranscript: null
  })
}))
