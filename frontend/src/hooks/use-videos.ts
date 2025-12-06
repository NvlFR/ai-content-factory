import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { videosApi } from "@/lib/api"

export function useVideos() {
  return useQuery({
    queryKey: ["videos"],
    queryFn: async () => {
      const response = await videosApi.list()
      return response.data
    },
  })
}

export function useVideo(id: string) {
  return useQuery({
    queryKey: ["video", id],
    queryFn: async () => {
      const response = await videosApi.get(id)
      return response.data
    },
    enabled: !!id,
  })
}

export function useCandidates(projectId: string) {
  return useQuery({
    queryKey: ["candidates", projectId],
    queryFn: async () => {
      const response = await videosApi.getCandidates(projectId)
      return response.data
    },
    enabled: !!projectId,
    refetchInterval: (query) => {
      const data = query.state.data as any
      if (data?.some((c: any) => !c.is_rendered)) {
        return 5000
      }
      return false
    },
  })
}

export function useCreateVideo() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (youtubeUrl: string) => videosApi.create(youtubeUrl),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] })
    },
  })
}

export function useRenderClip() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (candidateId: number) => videosApi.renderClip(candidateId),
    onSuccess: (_, candidateId) => {
      queryClient.invalidateQueries({ queryKey: ["candidates"] })
    },
  })
}

export function usePrepareEditor() {
  return useMutation({
    mutationFn: (candidateId: number) => videosApi.prepareEditor(candidateId),
  })
}
