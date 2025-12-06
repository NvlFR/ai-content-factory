import { useEffect } from "react"
import { useAuthStore } from "@/store/auth-store"
import { authApi } from "@/lib/api"

export function useAuth() {
  const { user, token, isAuthenticated, isLoading, login, logout, setLoading, setUser } = useAuthStore()

  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem("token")
      if (storedToken && !user) {
        try {
          const response = await authApi.getMe()
          setUser(response.data)
        } catch {
          logout()
        }
      }
      setLoading(false)
    }
    
    checkAuth()
  }, [])

  const handleGoogleLogin = () => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
    const redirectUri = `${window.location.origin}/auth/callback`
    const scope = "openid email profile https://www.googleapis.com/auth/youtube.readonly"
    
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${clientId}&` +
      `redirect_uri=${encodeURIComponent(redirectUri)}&` +
      `response_type=code&` +
      `scope=${encodeURIComponent(scope)}&` +
      `access_type=offline&` +
      `prompt=consent`
    
    window.location.href = authUrl
  }

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout,
    handleGoogleLogin,
  }
}
