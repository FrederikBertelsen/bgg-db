import type { FullGame, GameCard } from './types'

export class ApiError extends Error {
  status: number
  url: string
  body: unknown

  constructor(message: string, opts: { status: number; url: string; body: unknown }) {
    super(message)
    this.name = 'ApiError'
    this.status = opts.status
    this.url = opts.url
    this.body = opts.body
  }
}

const apiBaseUrl: string = import.meta.env.VITE_API_BASE_URL ?? '/api'

function buildUrl(path: string) {
  if (apiBaseUrl.startsWith('http://') || apiBaseUrl.startsWith('https://')) {
    return new URL(path, apiBaseUrl).toString()
  }

  if (!path.startsWith('/')) {
    throw new Error(`API path must start with "/": ${path}`)
  }
  return `${apiBaseUrl}${path}`
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const url = buildUrl(path)
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  })

  const text = await res.text()
  let body: unknown = null

  try {
    body = text ? (JSON.parse(text) as unknown) : null
  } catch {
    // JSON parsing failed - body stays null
  }

  if (!res.ok) {
    let message: string
    if (res.status === 500) {
      message = 'Server error. Please try again later.'
    } else if (typeof body === 'object' && body && 'error' in body) {
      message = String((body as { error: unknown }).error)
    } else {
      message = `Request failed (${res.status})`
    }
    throw new ApiError(message, { status: res.status, url, body })
  }

  return body as T
}

export function searchGames(term: string, n = 10, signal?: AbortSignal) {
  const encoded = encodeURIComponent(term.trim())
  return getJson<GameCard[]>(`/search/${encoded}?n=${n}`, signal)
}

export function getGame(id: string, signal?: AbortSignal) {
  return getJson<FullGame>(`/games/${encodeURIComponent(id)}`, signal)
}

export function recommendGames(id: string, n = 10, signal?: AbortSignal) {
  return getJson<GameCard[]>(`/recommend/${encodeURIComponent(id)}?n=${n}`, signal)
}

export function autocomplete(term: string, n = 5, signal?: AbortSignal) {
  const encoded = encodeURIComponent(term.trim())
  return getJson<string[]>(`/autocomplete/${encoded}?n=${n}`, signal)
}
