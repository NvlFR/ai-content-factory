"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowLeft,
  Loader2,
  Youtube,
  Instagram,
  CheckCircle,
  XCircle,
  ExternalLink,
  Unplug,
} from "lucide-react"
import { useAuth } from "@/hooks/use-auth"
import { distributionApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface PlatformStatus {
  platform: string
  is_connected: boolean
  username: string | null
  profile_picture: string | null
}

const TikTokIcon = () => (
  <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
)

export default function DistributionPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  
  const [platforms, setPlatforms] = useState<PlatformStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login")
      return
    }
    if (isAuthenticated) {
      fetchPlatforms()
    }
  }, [isAuthenticated, authLoading])

  const fetchPlatforms = async () => {
    try {
      setLoading(true)
      const res = await distributionApi.getPlatforms()
      setPlatforms(res.data)
    } catch (err) {
      console.error("Failed to load platforms", err)
    } finally {
      setLoading(false)
    }
  }

  const handleConnectTikTok = async () => {
    try {
      setActionLoading("tiktok")
      const res = await distributionApi.getTikTokAuthUrl()
      window.location.href = res.data.auth_url
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to get TikTok auth URL")
      setActionLoading(null)
    }
  }

  const handleConnectInstagram = async () => {
    try {
      setActionLoading("instagram")
      const res = await distributionApi.getInstagramAuthUrl()
      window.location.href = res.data.auth_url
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to get Instagram auth URL")
      setActionLoading(null)
    }
  }

  const handleDisconnect = async (platform: string) => {
    if (!confirm(`Disconnect ${platform}?`)) return
    
    try {
      setActionLoading(platform)
      if (platform === "tiktok") {
        await distributionApi.disconnectTikTok()
      }
      fetchPlatforms()
    } catch (err) {
      setError(`Failed to disconnect ${platform}`)
    } finally {
      setActionLoading(null)
    }
  }

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case "tiktok":
        return <TikTokIcon />
      case "instagram":
        return <Instagram className="w-6 h-6" />
      case "youtube_shorts":
        return <Youtube className="w-6 h-6 text-red-500" />
      default:
        return null
    }
  }

  const getPlatformName = (platform: string) => {
    switch (platform) {
      case "tiktok":
        return "TikTok"
      case "instagram":
        return "Instagram Reels"
      case "youtube_shorts":
        return "YouTube Shorts"
      default:
        return platform
    }
  }

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case "tiktok":
        return "bg-black"
      case "instagram":
        return "bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500"
      case "youtube_shorts":
        return "bg-red-600"
      default:
        return "bg-neutral-700"
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/dashboard")}
            className="text-neutral-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <h1 className="font-bold text-lg">Distribution Hub</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-lg">
            {error}
            <button onClick={() => setError("")} className="ml-2 underline">Dismiss</button>
          </div>
        )}

        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white">Connected Platforms</CardTitle>
            <CardDescription>
              Connect your social media accounts to auto-publish clips
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {platforms.map((platform) => (
              <div
                key={platform.platform}
                className="flex items-center justify-between p-4 bg-neutral-800 rounded-lg"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 ${getPlatformColor(platform.platform)} rounded-xl flex items-center justify-center text-white`}>
                    {getPlatformIcon(platform.platform)}
                  </div>
                  <div>
                    <p className="font-medium text-white">{getPlatformName(platform.platform)}</p>
                    {platform.is_connected ? (
                      <p className="text-sm text-neutral-400">@{platform.username}</p>
                    ) : (
                      <p className="text-sm text-neutral-500">Not connected</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {platform.is_connected ? (
                    <>
                      <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-1 rounded">
                        <CheckCircle className="w-3 h-3" />
                        Connected
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDisconnect(platform.platform)}
                        disabled={actionLoading === platform.platform}
                        className="text-neutral-400 hover:text-red-400"
                      >
                        {actionLoading === platform.platform ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Unplug className="w-4 h-4" />
                        )}
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (platform.platform === "tiktok") handleConnectTikTok()
                        else if (platform.platform === "instagram") handleConnectInstagram()
                      }}
                      disabled={actionLoading === platform.platform || platform.platform === "youtube_shorts"}
                      className="border-neutral-600 text-white hover:bg-neutral-700"
                    >
                      {actionLoading === platform.platform ? (
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      ) : (
                        <ExternalLink className="w-4 h-4 mr-2" />
                      )}
                      {platform.platform === "youtube_shorts" ? "Use YouTube Login" : "Connect"}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white">Auto-Post Settings</CardTitle>
            <CardDescription>
              Configure automatic posting behavior
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 bg-neutral-800 rounded-lg">
              <div>
                <p className="font-medium text-white">Auto-post without review</p>
                <p className="text-sm text-neutral-400">
                  Automatically publish clips after rendering (not recommended)
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-neutral-500 bg-neutral-700 px-2 py-1 rounded">
                  Coming Soon
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center text-neutral-500 text-sm">
          <p>Need API keys? Set up your developer accounts:</p>
          <div className="flex justify-center gap-4 mt-2">
            <a 
              href="https://developers.tiktok.com/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-neutral-400 hover:text-white underline"
            >
              TikTok Developer
            </a>
            <a 
              href="https://developers.facebook.com/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-neutral-400 hover:text-white underline"
            >
              Meta Developer
            </a>
          </div>
        </div>
      </main>
    </div>
  )
}
