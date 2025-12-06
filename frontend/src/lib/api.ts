import axios from "axios"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token")
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  exchangeToken: (code: string, redirectUri: string) =>
    api.post("/api/v1/auth/google/token", { code, redirect_uri: redirectUri }),
  
  getMe: () => api.get("/api/v1/auth/me"),
  
  logout: () => api.post("/api/v1/auth/logout"),
}

// Videos API
export const videosApi = {
  list: () => api.get("/api/v1/videos/"),
  
  get: (id: string) => api.get(`/api/v1/videos/${id}`),
  
  create: (youtubeUrl: string) => 
    api.post("/api/v1/videos/", { youtube_url: youtubeUrl }),
  
  analyze: (id: string) => 
    api.post(`/api/v1/videos/${id}/analyze`),
  
  getCandidates: (projectId: string) =>
    api.get(`/api/v1/videos/${projectId}/candidates`),
  
  renderClip: (candidateId: number) =>
    api.post(`/api/v1/videos/candidates/${candidateId}/render`),
  
  prepareEditor: (candidateId: number) =>
    api.post(`/api/v1/videos/candidates/${candidateId}/prepare-editor`),
}

// Channels API
export const channelsApi = {
  getYouTube: () => api.get("/api/v1/channels/youtube"),
  
  disconnectYouTube: () => api.delete("/api/v1/channels/youtube"),
  
  reconnectYouTube: () => api.post("/api/v1/channels/youtube/reconnect"),
  
  getYouTubeVideos: (maxResults: number = 10) => 
    api.get(`/api/v1/channels/youtube/videos?max_results=${maxResults}`),
}

// Clips API  
export const clipsApi = {
  list: (approvedOnly?: boolean) => 
    api.get(`/api/v1/clips/${approvedOnly ? '?approved_only=true' : ''}`),
  
  get: (id: number) => api.get(`/api/v1/clips/${id}`),
  
  update: (id: number, data: { caption?: string; is_approved?: boolean }) =>
    api.patch(`/api/v1/clips/${id}`, data),
  
  approve: (id: number, approved: boolean) =>
    api.post(`/api/v1/clips/${id}/approve`, { approved }),
  
  delete: (id: number) => api.delete(`/api/v1/clips/${id}`),
  
  getPendingCount: () => api.get('/api/v1/clips/pending/count'),
}

// Distribution API
export const distributionApi = {
  getPlatforms: () => api.get("/api/v1/distribution/platforms"),
  
  getTikTokAuthUrl: () => api.get("/api/v1/distribution/tiktok/auth-url"),
  connectTikTok: (code: string, redirectUri: string) =>
    api.post("/api/v1/distribution/tiktok/connect", { 
      platform: "tiktok", 
      auth_code: code, 
      redirect_uri: redirectUri 
    }),
  disconnectTikTok: () => api.delete("/api/v1/distribution/tiktok"),
  
  getInstagramAuthUrl: () => api.get("/api/v1/distribution/instagram/auth-url"),
  connectInstagram: (code: string, redirectUri: string) =>
    api.post("/api/v1/distribution/instagram/connect", { 
      platform: "instagram", 
      auth_code: code, 
      redirect_uri: redirectUri 
    }),
  
  publish: (clipId: number, platform: string, caption?: string) =>
    api.post("/api/v1/distribution/publish", { 
      clip_id: clipId, 
      platform, 
      caption 
    }),
}
