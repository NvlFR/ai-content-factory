import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { channelsApi } from "@/lib/api"

export function useChannels() {
  return useQuery({
    queryKey: ["channels"],
    queryFn: async () => {
      const response = await channelsApi.list()
      return response.data
    },
  })
}

export function useAddChannel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (channelId: string) => channelsApi.add(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })
}

export function useDeleteChannel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => channelsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })
}

export function useToggleChannel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => channelsApi.toggle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })
}
