"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { Loader2, Plus, Trash2, Youtube, ArrowLeft, Radio } from "lucide-react";
import Link from "next/link";

interface Channel {
  id: number;
  name: string;
  channel_id: string;
  is_active: boolean;
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [newUrl, setNewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/v1/channels/");
      setChannels(res.data);
    } catch (err) {
      console.error("Gagal load channels", err);
    }
  };

  const handleAddChannel = async () => {
    if (!newUrl) return;
    setLoading(true);
    setError("");

    try {
      await axios.post("http://localhost:8000/api/v1/channels/", {
        url: newUrl,
      });
      setNewUrl("");
      fetchChannels(); // Refresh list
    } catch (err) {
      setError("Gagal menambahkan channel. Pastikan URL valid.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Stop monitoring this channel?")) return;
    try {
      await axios.delete(`http://localhost:8000/api/v1/channels/${id}`);
      fetchChannels();
    } catch (err) {
      alert("Error deleting channel");
    }
  };

  return (
    <div className="min-h-screen p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-4 mb-8">
        <Link
          href="/"
          className="p-2 hover:bg-slate-100 rounded-full transition"
        >
          <ArrowLeft className="w-6 h-6 text-slate-600" />
        </Link>
        <h1 className="text-3xl font-bold text-slate-900">Channel Monitor</h1>
      </div>

      {/* INPUT CARD */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm mb-8">
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Add New YouTube Channel
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="https://www.youtube.com/@GadgetIn"
            className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 outline-none"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            disabled={loading}
          />
          <button
            onClick={handleAddChannel}
            disabled={loading || !newUrl}
            className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg flex items-center gap-2 font-medium disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            Monitor
          </button>
        </div>
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>

      {/* LIST CHANNELS */}
      <div className="grid gap-4">
        {channels.length === 0 && (
          <div className="text-center py-12 text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-300">
            No channels monitored yet.
          </div>
        )}

        {channels.map((channel) => (
          <div
            key={channel.id}
            className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center text-red-600">
                <Youtube className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-slate-800">
                  {channel.name}
                </h3>
                <p className="text-xs text-slate-500 font-mono">
                  ID: {channel.channel_id}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-green-600 text-sm font-medium bg-green-50 px-3 py-1 rounded-full">
                <Radio className="w-3 h-3 animate-pulse" /> Live Monitoring
              </div>
              <button
                onClick={() => handleDelete(channel.id)}
                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
