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
  const overallRank = game.ranks?.find((r) => r.category === 'Overall')?.rank ?? null

  return (
    <Link
      to={to}
      className={selected ? 'card card--selected' : 'card'}
      aria-label={game.name}
    >
      <img
        className="thumb"
        src={game.thumbnail_url ?? ''}
        alt={game.name}
        loading="lazy"
      />
      <div className="cardBody">
        <div className="cardTop">
          <div className="cardTitle">{game.name}</div>
          <div className="chips">
            {overallRank ? <span className="chip">Overall #{overallRank}</span> : null}
            {typeof game.score === 'number' ? (
              <span className="chip chip--score">Score {game.score.toFixed(3)}</span>
            ) : null}
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
            <span className="metaValue">{formatRange(game.min_playtime, game.max_playtime)}</span>
          </span>
        </div>

        <div className="cardScores">
          <ScoreRing value={game.rating_average} outOf={10} label="Rating" />
          <ScoreRing value={game.weight_average ?? null} outOf={5} label="Weight" />
          {typeof game.score === 'number' ? (
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
