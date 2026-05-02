import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getGame, recommendGames } from '../api/client'
import type { FullGame, GameCard } from '../api/types'
import { GameCard as GameCardComponent } from '../components/GameCard'
import { PlayerCountGraph } from '../components/PlayerCountGraph'
import { ScoreRing } from '../components/ScoreRing'
import { formatNumber, formatRange, normalizeDescriptionHtml } from '../lib/format'

function getNum(game: FullGame | null, key: string) {
  if (!game) return null
  const value = (game as Record<string, unknown>)[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function GamePage() {
  const params = useParams()
  const id = params.id ?? null

  const [game, setGame] = useState<FullGame | null>(null)
  const [recs, setRecs] = useState<GameCard[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [descriptionOpen, setDescriptionOpen] = useState(false)

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
    setDescriptionOpen(false)

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
    const image = typeof game.image_url === 'string' ? game.image_url : null
    const thumb = typeof game.thumbnail_url === 'string' ? game.thumbnail_url : null
    return image ?? thumb ?? ''
  }, [game])

  const descriptionHtml = useMemo(() => {
    if (!game || typeof game.description !== 'string') return null
    const trimmed = game.description.trim()
    if (!trimmed) return null
    return normalizeDescriptionHtml(trimmed)
  }, [game])

  const creditsByRole = useMemo(() => {
    const credits = Array.isArray(game?.credits) ? (game?.credits as unknown[]) : []
    const map = new Map<string, string[]>()
    for (const c of credits) {
      if (!c || typeof c !== 'object') continue
      const role = (c as { role?: unknown }).role
      const names = (c as { names?: unknown }).names
      if (typeof role !== 'string' || !Array.isArray(names)) continue
      const cleaned = names.filter((n) => typeof n === 'string') as string[]
      if (!cleaned.length) continue
      map.set(role, cleaned)
    }
    return map
  }, [game])

  const ranks = Array.isArray(game?.ranks) ? (game?.ranks as unknown[]) : []
  const playerCountScoresRaw =
    game && typeof (game as { player_count_scores?: unknown }).player_count_scores === 'object'
      ? ((game as { player_count_scores?: Record<string, unknown> }).player_count_scores ?? null)
      : null

  const playerCountScores = useMemo(() => {
    if (!playerCountScoresRaw) return null
    const entries = Object.entries(playerCountScoresRaw)
      .filter(([, value]) => typeof value === 'number')
      .sort(([a], [b]) => Number(a) - Number(b))
    return Object.fromEntries(entries) as Record<string, number>
  }, [playerCountScoresRaw])

  const sideStats: Array<[string, number | null]> = [
    ['Owned', typeof game?.owned_count === 'number' ? game.owned_count : null],
    ['Wishlists', typeof game?.wish_count === 'number' ? game.wish_count : null],
    ['Fans', typeof game?.fan_count === 'number' ? game.fan_count : null],
    ['Views', typeof game?.view_count === 'number' ? game.view_count : null],
    ['Comments', typeof game?.comment_count === 'number' ? game.comment_count : null],
    ['Geeklists', getNum(game, 'geeklist_count')],
    ['Trading', getNum(game, 'trading_count')],
    ['Want to play', getNum(game, 'want_to_play_count')],
    ['Want to buy', getNum(game, 'want_to_buy_count')],
    ['Wishlist comments', getNum(game, 'wishlist_comment_count')],
  ]

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
            <article className="gameLayout">
              <section className="gameMain">
                <section className="cardLike gameHero">
                  <img className="heroImage heroImage--large" src={heroImageUrl} alt={game.name} loading="lazy" />
                  <div className="gameHeroBody">
                    <div className="detailsTitle">{game.name}</div>
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
                        <span className="metaValue">{formatRange(game.min_playtime, game.max_playtime)}</span>
                      </span>
                    </div>
                    <div className="heroScores">
                      <ScoreRing value={game.rating_average ?? null} outOf={10} label="Rating" />
                      <ScoreRing value={game.weight_average ?? null} outOf={5} label="Weight" />
                    </div>
                    {typeof game.url === 'string' && game.url.startsWith('http') ? (
                      <a className="link" href={game.url} target="_blank" rel="noreferrer">
                        View on BoardGameGeek
                      </a>
                    ) : null}
                  </div>
                </section>

                {ranks.length ? (
                  <section className="section cardLike">
                    <h3>Ranks</h3>
                    <div className="rankChips">
                      {ranks
                        .map((rank) => rank as { category?: unknown; rank?: unknown })
                        .filter((rank) => typeof rank.category === 'string')
                        .map((rank) => (
                          <div key={String(rank.category)} className="rankChip">
                            <div className="rankChipLabel">{String(rank.category)}</div>
                            <div className="rankChipValue">#{typeof rank.rank === 'string' ? rank.rank : '—'}</div>
                          </div>
                        ))}
                    </div>
                  </section>
                ) : null}

                <section className="section cardLike">
                  <h3>Overview</h3>
                  <div className="overviewGrid">
                    <div className="overviewItem">
                      <div className="overviewKey">Players</div>
                      <div className="overviewValue">{formatRange(game.min_players, game.max_players)}</div>
                    </div>
                    <div className="overviewItem">
                      <div className="overviewKey">Playtime</div>
                      <div className="overviewValue">{formatRange(game.min_playtime, game.max_playtime)} min</div>
                    </div>
                    <div className="overviewItem">
                      <div className="overviewKey">Rating count</div>
                      <div className="overviewValue">{typeof game.rating_count === 'number' ? game.rating_count : '—'}</div>
                    </div>
                    <div className="overviewItem">
                      <div className="overviewKey">Std dev</div>
                      <div className="overviewValue">{formatNumber(game.stddev_rating, 2)}</div>
                    </div>
                    <div className="overviewItem">
                      <div className="overviewKey">Plays</div>
                      <div className="overviewValue">{typeof game.play_count === 'number' ? game.play_count : '—'}</div>
                    </div>
                    <div className="overviewItem">
                      <div className="overviewKey">Plays (30d)</div>
                      <div className="overviewValue">{typeof game.play_count_last_month === 'number' ? game.play_count_last_month : '—'}</div>
                    </div>
                    <div className="overviewItem">
                      <div className="overviewKey">Best players</div>
                      <div className="overviewValue">{formatRange(getNum(game, 'PlayerCountBestMin'), getNum(game, 'PlayerCountBestMax'))}</div>
                    </div>
                    <div className="overviewItem">
                      <div className="overviewKey">Recommended players</div>
                      <div className="overviewValue">{formatRange(getNum(game, 'PlayerCountRecommendedMin'), getNum(game, 'PlayerCountRecommendedMax'))}</div>
                    </div>
                  </div>
                </section>

                {descriptionHtml ? (
                  <section className="section cardLike">
                    <h3>Description</h3>
                    {!descriptionOpen && typeof game.short_description === 'string' ? (
                      <p className="desc">{game.short_description}</p>
                    ) : null}
                    <details
                      className="expander"
                      open={descriptionOpen}
                      onToggle={(event) => setDescriptionOpen((event.target as HTMLDetailsElement).open)}
                    >
                      <summary>{descriptionOpen ? 'Hide description' : 'Show description'}</summary>
                      <div className="description" dangerouslySetInnerHTML={{ __html: descriptionHtml }} />
                    </details>
                  </section>
                ) : typeof game.short_description === 'string' ? (
                  <section className="section cardLike">
                    <h3>Description</h3>
                    <p className="desc">{game.short_description}</p>
                  </section>
                ) : null}

                {recs.length ? (
                  <section className="section cardLike">
                    <h3>Recommendations</h3>
                    <div className="recs recs--top">
                      {recs.map((rec) => (
                        <GameCardComponent key={rec.id} game={rec} to={`/game/${rec.id}`} />
                      ))}
                    </div>
                  </section>
                ) : null}

                {playerCountScores && Object.keys(playerCountScores).length ? (
                  <section className="section cardLike">
                    <h3>Player count ratings</h3>
                    <p className="muted">Scores are out of 1.</p>
                    <PlayerCountGraph scores={playerCountScores} />
                  </section>
                ) : null}

                {Array.isArray(game.categories) && game.categories.length ? (
                  <section className="section cardLike">
                    <h3>Categories</h3>
                    <div className="tags">
                      {game.categories.map((category) => (
                        <span key={category} className="tag">
                          {category}
                        </span>
                      ))}
                    </div>
                  </section>
                ) : null}

                {Array.isArray(game.mechanics) && game.mechanics.length ? (
                  <section className="section cardLike">
                    <h3>Mechanics</h3>
                    <div className="tags">
                      {game.mechanics.map((mechanic) => (
                        <span key={mechanic} className="tag">
                          {mechanic}
                        </span>
                      ))}
                    </div>
                  </section>
                ) : null}

                {Array.isArray(game.honors) && game.honors.length ? (
                  <section className="section cardLike">
                    <h3>Honors</h3>
                    <ul className="bullets">
                      {game.honors.map((honor) => (
                        <li key={honor}>{honor}</li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                {Array.isArray(game.families) && game.families.length ? (
                  <section className="section cardLike">
                    <h3>Families</h3>
                    <div className="tags">
                      {game.families.map((family: string) => (
                        <span key={family} className="tag">
                          {family}
                        </span>
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

              <aside className="gameSide">
                <section className="section cardLike sideSection">
                  <h3>Side stats</h3>
                  <div className="sideStats">
                    {sideStats.map(([label, value]) => (
                      <div key={label} className="sideStatRow">
                        <span className="sideStatKey">{label}</span>
                        <span className="sideStatValue">{typeof value === 'number' ? value : '—'}</span>
                      </div>
                    ))}
                  </div>
                </section>
              </aside>
            </article>
          ) : null}
        </section>
      </main>
    </div>
  )
}
