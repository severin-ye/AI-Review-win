import { useQuery } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface HealthResponse {
  status: string
  version: string
  backend: string
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/api/health')
}

/** 后端连接状态，5 秒轮询（导航栏底部指示器使用） */
export function useBackendHealth() {
  return useQuery({
    queryKey: ['backend-health'],
    queryFn: fetchHealth,
    refetchInterval: 5000,
    retry: false,
  })
}
