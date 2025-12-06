"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  Loader2, 
  Youtube, 
  ArrowLeft, 
  Radio, 
  CheckCircle2, 
  XCircle,
  RefreshCw,
  ExternalLink,
  Play
} from "lucide-react";
import Link from "next/link";
import { channelsApi, videosApi } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";

interface YouTubeChannel {
  id: string;
  platform: string;
  channel_id: string | null;
  channel_name: string | null;
  channel_thumbnail: string | null;
  is_connected: boolean;
}

interface VideoItem {
  video_id: string;
  title: string;
  thumbnail: string;
  published_at: string;
}

export default function ChannelsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, handleGoogleLogin } = useAuth();
  
  const [channel, setChannel] = useState<YouTubeChannel | null>(null);
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [videosLoading, setVideosLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
      return;
    }
    if (isAuthenticated) {
      fetchChannel();
    }
  }, [isAuthenticated, authLoading]);

  const fetchChannel = async () => {
    try {
      setLoading(true);
      const res = await channelsApi.getYouTube();
      setChannel(res.data);
      
      if (res.data && res.data.is_connected) {
        fetchVideos();
      }
    } catch (err) {
      console.error("Failed to load channel", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchVideos = async () => {
    try {
      setVideosLoading(true);
      const res = await channelsApi.getYouTubeVideos(5);
      setVideos(res.data);
    } catch (err) {
      console.error("Failed to load videos", err);
    } finally {
      setVideosLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm("Stop monitoring YouTube channel? You can reconnect anytime.")) return;
    
    try {
      setActionLoading(true);
      await channelsApi.disconnectYouTube();
      setChannel(prev => prev ? { ...prev, is_connected: false } : null);
      setVideos([]);
    } catch (err) {
      setError("Failed to disconnect channel");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReconnect = async () => {
    try {
      setActionLoading(true);
      await channelsApi.reconnectYouTube();
      setChannel(prev => prev ? { ...prev, is_connected: true } : null);
      fetchVideos();
    } catch (err) {
      setError("Failed to reconnect. Please login again with Google.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleProcessVideo = async (videoId: string) => {
    try {
      const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
      await videosApi.create(videoUrl);
      router.push("/dashboard");
    } catch (err) {
      setError("Failed to process video");
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-4 mb-8">
        <Link
          href="/dashboard"
          className="p-2 hover:bg-neutral-800 rounded-full transition"
        >
          <ArrowLeft className="w-6 h-6 text-neutral-400" />
        </Link>
        <h1 className="text-3xl font-bold">YouTube Channel</h1>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-lg mb-6">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* CONNECTED CHANNEL CARD */}
      {channel && channel.channel_id ? (
        <div className="bg-neutral-900 p-6 rounded-xl border border-neutral-800 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {channel.channel_thumbnail ? (
                <img 
                  src={channel.channel_thumbnail} 
                  alt={channel.channel_name || "Channel"} 
                  className="w-16 h-16 rounded-full"
                />
              ) : (
                <div className="w-16 h-16 bg-neutral-800 rounded-full flex items-center justify-center">
                  <Youtube className="w-8 h-8 text-red-500" />
                </div>
              )}
              <div>
                <h2 className="text-xl font-bold">{channel.channel_name || "YouTube Channel"}</h2>
                <p className="text-sm text-neutral-500 font-mono">ID: {channel.channel_id}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {channel.is_connected ? (
                <>
                  <div className="flex items-center gap-2 text-green-400 text-sm font-medium bg-green-500/10 px-3 py-1.5 rounded-full">
                    <Radio className="w-3 h-3 animate-pulse" />
                    Auto-Monitoring Active
                  </div>
                  <button
                    onClick={handleDisconnect}
                    disabled={actionLoading}
                    className="px-4 py-2 text-sm text-neutral-400 hover:text-red-400 hover:bg-neutral-800 rounded-lg transition disabled:opacity-50"
                  >
                    {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Disconnect"}
                  </button>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2 text-neutral-500 text-sm font-medium bg-neutral-800 px-3 py-1.5 rounded-full">
                    <XCircle className="w-3 h-3" />
                    Monitoring Paused
                  </div>
                  <button
                    onClick={handleReconnect}
                    disabled={actionLoading}
                    className="px-4 py-2 text-sm bg-white text-neutral-900 hover:bg-neutral-200 rounded-lg transition disabled:opacity-50 flex items-center gap-2"
                  >
                    {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Reconnect
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-neutral-800">
            <p className="text-sm text-neutral-400">
              <CheckCircle2 className="w-4 h-4 inline mr-2 text-green-500" />
              New videos from this channel will be automatically detected and processed.
            </p>
          </div>
        </div>
      ) : (
        /* NO CHANNEL CONNECTED */
        <div className="bg-neutral-900 p-8 rounded-xl border border-dashed border-neutral-700 mb-8 text-center">
          <Youtube className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Connect Your YouTube Channel</h2>
          <p className="text-neutral-400 mb-6 max-w-md mx-auto">
            Login with your Google account to automatically monitor your YouTube channel for new uploads.
          </p>
          <button
            onClick={handleGoogleLogin}
            className="bg-white hover:bg-neutral-200 text-neutral-900 px-6 py-3 rounded-lg font-medium transition inline-flex items-center gap-2"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </button>
        </div>
      )}

      {/* RECENT VIDEOS */}
      {channel && channel.is_connected && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold">Recent Videos</h3>
            <button 
              onClick={fetchVideos} 
              disabled={videosLoading}
              className="text-sm text-neutral-400 hover:text-white flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${videosLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {videosLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-neutral-500" />
            </div>
          ) : videos.length === 0 ? (
            <div className="text-center py-12 text-neutral-500 bg-neutral-900 rounded-xl border border-neutral-800">
              No videos found
            </div>
          ) : (
            <div className="grid gap-4">
              {videos.map((video) => (
                <div
                  key={video.video_id}
                  className="flex items-center gap-4 bg-neutral-900 p-4 rounded-xl border border-neutral-800 hover:border-neutral-700 transition"
                >
                  <div className="relative group">
                    <img 
                      src={video.thumbnail} 
                      alt={video.title}
                      className="w-32 h-20 object-cover rounded-lg"
                    />
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center rounded-lg">
                      <Play className="w-8 h-8 text-white" />
                    </div>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium truncate">{video.title}</h4>
                    <p className="text-sm text-neutral-500">
                      {new Date(video.published_at).toLocaleDateString('id-ID', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric'
                      })}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <a
                      href={`https://youtube.com/watch?v=${video.video_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-neutral-500 hover:text-white hover:bg-neutral-800 rounded-lg transition"
                    >
                      <ExternalLink className="w-5 h-5" />
                    </a>
                    <button
                      onClick={() => handleProcessVideo(video.video_id)}
                      className="px-4 py-2 bg-white text-neutral-900 hover:bg-neutral-200 rounded-lg text-sm font-medium transition"
                    >
                      Process
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
