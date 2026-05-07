import { Link } from 'react-router-dom'
import type { GameCard as GameCardType } from '../api/types'
import { formatRange } from '../lib/format'
import { ScoreRing } from './ScoreRing'

type Props = {
  game: GameCardType
  to: string
  selected?: boolean
}

export function GameCard({ game, to, selected }: Props) {
  const rankText = game.ranks.map((rank) => `${rank.name}: ${rank.value}`).join(' · ')
  const nicheText = game.niches.length ? game.niches.join(' · ') : '—'

  return (
    <Link
      to={to}
      className={selected ? 'card card--selected' : 'card'}
      aria-label={game.name}
    >
      <img
        className="thumb"
        src={game.thumbnail ?? ''}
        alt={game.name}
        loading="lazy"
      />
      <div className="cardBody">
        <div className="cardTop">
          <div className="cardTitle">{game.name}</div>
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

        <div className="cardFacts">
          <div className="cardFact">
            <span className="cardFactKey">Ranks</span>
            <span className="cardFactValue">{rankText || '—'}</span>
          </div>
          <div className="cardFact">
            <span className="cardFactKey">Niches</span>
            <span className="cardFactValue">{nicheText}</span>
          </div>
        </div>

        <div className="cardScores">
          <ScoreRing value={game.rating} outOf={10} label="Rating" />
          <ScoreRing value={game.weight ?? null} reverse={true} outOf={5} label="Weight" />
          {typeof game.score === 'number' && game.score < 100 ? (
            <ScoreRing value={game.score} outOf={1} label="Rec" />
          ) : null}
        </div>

        {game.short_description ? (
          <div className="desc">{game.short_description}</div>
        ) : null}
      </div>
    </Link>
  )
}
