"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Film, Scissors, Zap, Upload, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/use-auth"

export default function LandingPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.push("/dashboard")
    }
  }, [isAuthenticated, isLoading, router])

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* HEADER */}
      <header className="border-b border-neutral-800">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center">
              <Film className="w-5 h-5 text-neutral-900" />
            </div>
            <span className="font-bold text-lg">AI Content Factory</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost" className="text-neutral-400 hover:text-white">
                Sign In
              </Button>
            </Link>
            <Link href="/login">
              <Button className="bg-white hover:bg-neutral-200 text-neutral-900">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* HERO SECTION */}
      <section className="max-w-7xl mx-auto px-4 py-24 text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          Turn Your YouTube Videos
          <br />
          <span className="text-neutral-400">Into Viral Short Clips</span>
        </h1>
        <p className="text-xl text-neutral-400 max-w-2xl mx-auto mb-10">
          AI-powered tool that automatically analyzes your long-form content and creates 
          engaging short-form clips optimized for TikTok, Reels, and Shorts.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/login">
            <Button size="lg" className="bg-white hover:bg-neutral-200 text-neutral-900 h-12 px-8 text-base">
              Start Creating <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* FEATURES */}
      <section className="max-w-7xl mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center mb-4">
              <Upload className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-2">1. Paste URL</h3>
            <p className="text-neutral-400">
              Simply paste your YouTube video URL and let our AI analyze the content.
            </p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center mb-4">
              <Scissors className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-2">2. AI Analysis</h3>
            <p className="text-neutral-400">
              Our AI identifies the most engaging moments and suggests viral clip candidates.
            </p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center mb-4">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-2">3. Export & Post</h3>
            <p className="text-neutral-400">
              Render clips in 9:16 format ready for TikTok, Instagram Reels, and YouTube Shorts.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 py-20">
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-12 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Create Viral Content?</h2>
          <p className="text-neutral-400 mb-8 max-w-xl mx-auto">
            Join creators who are saving hours of editing time and growing their audience with AI-generated clips.
          </p>
          <Link href="/login">
            <Button size="lg" className="bg-white hover:bg-neutral-200 text-neutral-900 h-12 px-8 text-base">
              Get Started Free <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-neutral-800 py-8">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-neutral-500">
            <Film className="w-4 h-4" />
            <span className="text-sm">AI Content Factory</span>
          </div>
          <p className="text-sm text-neutral-500">
            Built for content creators
          </p>
        </div>
      </footer>
    </div>
  )
}
