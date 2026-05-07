import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { autocomplete } from '../api/client'

export function SiteHeader() {
  const location = useLocation()
  const navigate = useNavigate()
  const autocompleteAbortRef = useRef<AbortController | null>(null)

  const [term, setTerm] = useState(() => {
    const initialParams = new URLSearchParams(location.search)
    return initialParams.get('q') ?? ''
  })
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)

  useEffect(() => {
    const nextTerm = new URLSearchParams(location.search).get('q') ?? ''
    if (nextTerm) {
      setTerm(nextTerm)
    }
  }, [location.search])

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
        if (!ac.signal.aborted) {
          setSuggestions(data)
        }
      } catch {
        if (!ac.signal.aborted) {
          setSuggestions([])
        }
      }
    }, 150)

    return () => {
      window.clearTimeout(handle)
      ac.abort()
    }
  }, [term])

  function submitSearch(nextTerm: string) {
    const trimmed = nextTerm.trim()
    if (!trimmed) {
      return
    }

    setSuggestionsOpen(false)
    navigate(`/search?q=${encodeURIComponent(trimmed)}`)
  }

  return (
    <header className="siteHeader">
      <div className="siteHeaderInner">
        <Link className="brand" to="/" aria-label="Go to home">
          <span className="brandMark">BGG</span>
          <span className="brandText">
            <span className="brandName">Boardgame Explorer</span>
            <span className="brandTag">Search the catalog</span>
          </span>
        </Link>

        <form
          className="siteSearch"
          onSubmit={(event) => {
            event.preventDefault()
            submitSearch(term)
          }}
        >
          <div className="searchBox">
            <input
              value={term}
              onChange={(event) => {
                setTerm(event.target.value)
                setSuggestionsOpen(true)
              }}
              onFocus={() => setSuggestionsOpen(true)}
              onBlur={() => {
                window.setTimeout(() => setSuggestionsOpen(false), 120)
              }}
              placeholder="Search boardgames"
              aria-label="Search boardgames"
              autoComplete="off"
            />
            {suggestionsOpen && suggestions.length ? (
              <div className="autocomplete" role="listbox" aria-label="Suggestions">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="autocompleteItem"
                    role="option"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => {
                      setTerm(suggestion)
                      submitSearch(suggestion)
                    }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <button type="submit" className="siteSearchButton">
            Search
          </button>
        </form>
      </div>
    </header>
  )
}