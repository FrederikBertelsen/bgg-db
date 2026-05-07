import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getGame, recommendGames } from '../api/client'
import type { FullGame, GameCard } from '../api/types'
import { GameCard as GameCardComponent } from '../components/GameCard'
import { PlayerCountGraph } from '../components/PlayerCountGraph'
import { ScoreRing } from '../components/ScoreRing'
import { formatNumber, formatRange } from '../lib/format'

export function GamePage() {
  const params = useParams()
  const id = params.id ?? null

  const [game, setGame] = useState<FullGame | null>(null)
  const [recs, setRecs] = useState<GameCard[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!id) return

    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setLoading(true)
    setError(null)
    setGame(null)
    setRecs([])

    ;(async () => {
      try {
        const [g, r] = await Promise.all([
          getGame(id, ac.signal),
          recommendGames(id, 10, ac.signal),
        ])
        setGame(g)
        setRecs(r)
      } catch (err) {
        if (ac.signal.aborted) return
        setError(err instanceof Error ? err.message : 'Failed to load game')
      } finally {
        if (!ac.signal.aborted) setLoading(false)
      }
    })()

    return () => ac.abort()
  }, [id])

  const heroImageUrl = useMemo(() => {
    if (!game) return ''
    const image = typeof game.image === 'string' ? game.image : null
    const thumb = typeof game.thumbnail === 'string' ? game.thumbnail : null
    return image ?? thumb ?? ''
  }, [game])

  const descriptionHtml = useMemo(() => {
    if (!game || typeof game.description !== 'string') return null
    const trimmed = game.description.trim()
    if (!trimmed) return null
    return trimmed
  }, [game])

  const creditsByRole = useMemo(() => {
    const map = new Map<string, string[]>()
    if (game?.designers.length) map.set('designers', game.designers)
    if (game?.artists.length) map.set('artists', game.artists)
    if (game?.publishers.length) map.set('publishers', game.publishers)
    return map
  }, [game])

  const ranks = game?.ranks ?? []
  const playerCountScoresRaw = game?.player_count_scores ?? null

  const playerCountScores = useMemo(() => {
    if (!playerCountScoresRaw) return null
    const entries = Object.entries(playerCountScoresRaw)
      .filter(([, value]) => typeof value === 'number')
      .sort(([a], [b]) => {
        return Number(a) - Number(b)
      })
    return Object.fromEntries(entries) as Record<string, number>
  }, [playerCountScoresRaw])

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1 className="title">Game</h1>
          <p className="subtitle">
            <Link className="navLink" to="/">
              ← Back to search
            </Link>
          </p>
        </div>
      </header>

      <main className="contentSingle">
        <section className="panel">
          {error ? <div className="error">{error}</div> : null}
          {loading ? <div className="muted">Loading…</div> : null}

          {game ? (
            <article className="gameLayout gameLayout--single">
              <section className="gameMain">
                <section className="cardLike gameHero">
                  <a href={`https://boardgamegeek.com/boardgame/${game.id}`} target="_blank" rel="noopener noreferrer">
                    <img className="heroImage heroImage--large" src={heroImageUrl} alt={game.name} loading="lazy" />
                  </a>
                  <div className="gameHeroBody">
                    <div className="heroTitleRow">
                      <div className="detailsTitle">{game.name}</div>
                      <div className="heroScores">
                        <ScoreRing value={game.rating ?? null} outOf={10} label="Rating" />
                        <ScoreRing value={game.weight ?? null} outOf={5} reverse={true} label="Weight" />
                      </div>
                    </div>
                    <div className="meta">
                      <span className="metaItem">
                        <span className="metaKey">Year</span>
                        <span className="metaValue">{game.year_published ?? '—'}</span>
                      </span>
                      <span className="metaItem">
                        <span className="metaKey">Players</span>
                        <span className="metaValue">{formatRange(game.min_players, game.max_players)}</span>
                      </span>
                      <span className="metaItem">
                        <span className="metaKey">Minutes</span>
                        <span className="metaValue">{formatRange(game.min_playing_time, game.max_playing_time)}</span>
                      </span>
                    </div>
                    <div className="heroFooter">
                      <div className="heroRanks">
                        {ranks.map((r) => (
                            <div key={r.name} className="heroRank">
                              <div className="heroRankLabel">
                                <strong>{r.name} Rank</strong>
                                <strong className="heroRankValue">{r.value}</strong>
                              </div>
                            </div>
                        ))}
                      </div>
                      <div className="heroStats">
                        <div className="heroStatItem">
                          <div className="heroStatKey">Rating count</div>
                          <div className="heroStatValue">{typeof game.rating_count === 'number' ? game.rating_count : '—'}</div>
                        </div>
                        <div className="heroStatItem">
                          <div className="heroStatKey">Std dev</div>
                          <div className="heroStatValue">{formatNumber(game.rating_stddev, 2)}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                <div className="propertiesRow">
                  <section className="section cardLike">
                    <h3>Properties</h3>
                    <div className="properties">
                      <div><strong>Types:</strong> {Array.isArray(game.types) && game.types.length ? game.types.join(' · ') : '—'}</div>
                      <div><strong>Mechanics:</strong> {Array.isArray(game.mechanics) && game.mechanics.length ? game.mechanics.join(' · ') : '—'}</div>
                      <div><strong>Components:</strong> {Array.isArray(game.components) && game.components.length ? game.components.join(' · ') : '—'}</div>
                      <div><strong>Themes:</strong> {Array.isArray(game.themes) && game.themes.length ? game.themes.join(' · ') : '—'}</div>
                      <div><strong>Niches:</strong> {Array.isArray(game.niches) && game.niches.length ? game.niches.join(' · ') : '—'}</div>
                    </div>
                  </section>

                  {playerCountScores && Object.keys(playerCountScores).length ? (
                    <section className="section cardLike">
                      <h3>Player count Recommendations</h3>
                      <PlayerCountGraph scores={playerCountScores} />
                    </section>
                  ) : null}
                </div>



                {descriptionHtml ? (
                  <section className="section cardLike">
                    <h3>Description</h3>
                    <div className="description" dangerouslySetInnerHTML={{ __html: descriptionHtml }} />
                  </section>
                ) : null}

                



                {recs.length ? (
                  <section className="section cardLike">
                    <h3>Similar</h3>
                    <div className="recs recs--top">
                      {recs.map((rec) => (
                        <GameCardComponent key={rec.id} game={rec} to={`/game/${rec.id}`} />
                      ))}
                    </div>
                  </section>
                ) : null}

                {Array.isArray(game.expansions) && game.expansions.length ? (
                  <section className="section cardLike">
                    <h3>Expansions</h3>
                    <div className="tags">
                      {game.expansions.map((e) => (
                        <span key={e.id} className="tag">{e.name}</span>
                      ))}
                    </div>
                  </section>
                ) : null}
                


                {creditsByRole.size ? (
                  <section className="section cardLike">
                    <h3>Credits</h3>
                    <div className="credits">
                      {Array.from(creditsByRole.entries()).map(([role, names]) => (
                        <div key={role} className="creditRow">
                          <div className="creditRole">{role.replaceAll('_', ' ')}</div>
                          <div className="creditNames">{names.join(', ')}</div>
                        </div>
                      ))}
                    </div>
                  </section>
                ) : null}
              </section>
            </article>
          ) : null}
        </section>
      </main>
    </div>
  )
}
