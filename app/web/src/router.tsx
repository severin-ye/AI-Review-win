import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

type NavigateOptions = { replace?: boolean }
type Navigate = (to: string, options?: NavigateOptions) => void

type RouterState = {
  path: string
  navigate: Navigate
}

const RouterContext = createContext<RouterState | null>(null)

function readHashPath(): string {
  const raw = window.location.hash.replace(/^#/, '').split('?')[0]
  if (!raw || raw === '/') return '/documents'
  return raw.startsWith('/') ? raw : `/${raw}`
}

export function HashRouter({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(readHashPath)

  useEffect(() => {
    if (!window.location.hash || window.location.hash === '#/') {
      window.history.replaceState(null, '', '#/documents')
    }
    const onHashChange = () => setPath(readHashPath())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const navigate = useCallback<Navigate>((to, options) => {
    const next = to.startsWith('/') ? to : `/${to}`
    if (options?.replace) {
      window.history.replaceState(null, '', `#${next}`)
      setPath(next)
      return
    }
    if (window.location.hash === `#${next}`) {
      setPath(next)
    } else {
      window.location.hash = next
    }
  }, [])

  const value = useMemo(() => ({ path, navigate }), [navigate, path])
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
}

function useRouter(): RouterState {
  const router = useContext(RouterContext)
  if (!router) throw new Error('Router hooks must be used inside HashRouter')
  return router
}

export function useHashPath(): string {
  return useRouter().path
}

export function useNavigate(): Navigate {
  return useRouter().navigate
}

export function useParams<T extends Record<string, string | undefined>>(): T {
  const path = useHashPath()
  const match = /^\/workbench(?:\/([^/]+))?\/?$/.exec(path)
  const docId = match?.[1] ? decodeURIComponent(match[1]) : undefined
  return { docId } as unknown as T
}
