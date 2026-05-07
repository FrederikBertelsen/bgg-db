import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { searchGames } from '../api/client'
import type { GameCard } from '../api/types'
import { GameCard as GameCardComponent } from '../components/GameCard'

export function SearchPage() {
  const [searchParams] = useSearchParams()
  const term = searchParams.get('q')?.trim() ?? ''
  const [results, setResults] = useState<GameCard[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  async function runSearch(nextTerm: string) {
    if (!nextTerm) {
      setResults([])
      setError('Enter a search term')
      setLoading(false)
      return
    }

    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setLoading(true)
    setError(null)
    try {
      const data = await searchGames(nextTerm, 10, ac.signal)
      setResults(data)
    } catch (err) {
      if (ac.signal.aborted) return
      setResults([])
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      if (!ac.signal.aborted) setLoading(false)
    }
  }

  useEffect(() => {
    void runSearch(term)
    return () => abortRef.current?.abort()
  }, [term])

  return (
    <div className="page">
      <main className="contentSingle">
        <section className="panel">
          <div className="resultsHeader">
            <div>
              <h1 className="title">Search results</h1>
              <p className="subtitle">{term ? `Showing results for “${term}”.` : 'Add a search query to the URL or use the top bar.'}</p>
            </div>
            {term ? <div className="resultsPill">{results.length} results</div> : null}
          </div>
          {error ? <div className="error">{error}</div> : null}
          {loading ? <div className="muted">Loading…</div> : null}
          <div className="resultsGrid">
            {results.map((g) => (
              <GameCardComponent key={g.id} game={g} to={`/game/${g.id}`} />
            ))}
            {!loading && results.length === 0 ? <div className="muted">No results.</div> : null}
          </div>
        </section>
      </main>
    </div>
  )
}
