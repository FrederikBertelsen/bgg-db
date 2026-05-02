import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { autocomplete, searchGames } from '../api/client'
import type { GameCard } from '../api/types'
import { GameCard as GameCardComponent } from '../components/GameCard'

export function SearchPage() {
  const [term, setTerm] = useState('')
  const [results, setResults] = useState<GameCard[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [suggestions, setSuggestions] = useState<string[]>([])
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const autocompleteAbortRef = useRef<AbortController | null>(null)
  const navigate = useNavigate()

  async function runSearch(nextTerm: string) {
    const trimmed = nextTerm.trim()
    if (!trimmed) {
      setResults([])
      setError('Enter a search term')
      return
    }

    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setLoading(true)
    setError(null)
    try {
      const data = await searchGames(trimmed, 10, ac.signal)
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const trimmed = term.trim()
    if (!trimmed) {
      setSuggestions([])
      return
    }

    autocompleteAbortRef.current?.abort()
    const ac = new AbortController()
    autocompleteAbortRef.current = ac

    const handle = window.setTimeout(async () => {
      try {
        const data = await autocomplete(trimmed, 5, ac.signal)
        if (ac.signal.aborted) return
        setSuggestions(data)
      } catch {
        if (ac.signal.aborted) return
        setSuggestions([])
      }
    }, 150)

    return () => {
      window.clearTimeout(handle)
      ac.abort()
    }
  }, [term])

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1 className="title">Boardgame Search</h1>
          <p className="subtitle">Search and open a game for details.</p>
        </div>
        <form
          className="search"
          onSubmit={(e) => {
            e.preventDefault()
            void runSearch(term)
            setSuggestionsOpen(false)
          }}
        >
          <div className="searchBox">
            <input
              value={term}
              onChange={(e) => {
                setTerm(e.target.value)
                setSuggestionsOpen(true)
              }}
              onFocus={() => setSuggestionsOpen(true)}
              onBlur={() => {
                // Allow click selection.
                window.setTimeout(() => setSuggestionsOpen(false), 120)
              }}
              placeholder="Search boardgames (e.g. catan)"
              aria-label="Search"
              autoComplete="off"
            />
            {suggestionsOpen && suggestions.length ? (
              <div className="autocomplete" role="listbox" aria-label="Suggestions">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="autocompleteItem"
                    role="option"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={async () => {
                      setTerm(s)
                      setSuggestionsOpen(false)
                      try {
                        const data = await searchGames(s, 10)
                        const exact = data.find((g) => g.name === s) ?? data[0]
                        if (exact) {
                          navigate(`/game/${exact.id}`)
                          return
                        }
                        setResults(data)
                      } catch {
                        void runSearch(s)
                      }
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>
      </header>

      <main className="contentSingle">
        <section className="panel">
          <h2 className="panelTitle">Results</h2>
          {error ? <div className="error">{error}</div> : null}
          <div className="resultsGrid">
            {results.map((g) => (
              <div key={g.id} onClick={() => navigate(`/game/${g.id}`)}>
                <GameCardComponent game={g} to={`/game/${g.id}`} />
              </div>
            ))}
            {!loading && results.length === 0 ? <div className="muted">No results.</div> : null}
          </div>
        </section>
      </main>
    </div>
  )
}
