"use client"

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuthStore } from "@/store/auth-store"
import { authApi } from "@/lib/api"

function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code")
      const token = searchParams.get("token")
      const errorParam = searchParams.get("error")

      if (errorParam) {
        setError("Authentication cancelled or failed")
        setTimeout(() => router.push("/"), 3000)
        return
      }

      // If token is passed directly (from backend redirect)
      if (token) {
        localStorage.setItem("token", token)
        try {
          const response = await authApi.getMe()
          login(response.data, token)
          router.push("/dashboard")
        } catch {
          setError("Failed to get user info")
          setTimeout(() => router.push("/"), 3000)
        }
        return
      }

      // If code is passed (frontend OAuth flow)
      if (code) {
        try {
          const redirectUri = `${window.location.origin}/auth/callback`
          const response = await authApi.exchangeToken(code, redirectUri)
          const { access_token, user } = response.data
          login(user, access_token)
          router.push("/dashboard")
        } catch (err: any) {
          setError(err.response?.data?.detail || "Authentication failed")
          setTimeout(() => router.push("/"), 3000)
        }
        return
      }

      setError("No authentication code received")
      setTimeout(() => router.push("/"), 3000)
    }

    handleCallback()
  }, [searchParams, login, router])

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
      <div className="text-center">
        {error ? (
          <div className="text-red-400">
            <p className="text-xl mb-2">{error}</p>
            <p className="text-neutral-400">Redirecting...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin" />
            <p className="text-white text-lg">Authenticating...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
          <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  )
}
