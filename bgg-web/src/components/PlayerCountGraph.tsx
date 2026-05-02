type Props = {
  scores: Record<string, number>
}

export function PlayerCountGraph({ scores }: Props) {
  const entries = Object.entries(scores).map(([k, v]) => ({ k, v: typeof v === 'number' ? v : 0 }))
  const max = entries.reduce((m, e) => (e.v > m ? e.v : m), 0.0001)

  return (
    <div className="playerGraph">
      {entries.map(({ k, v }) => (
        <div key={k} className="playerRow">
          <div className="playerLabel">{k}</div>
          <div className="playerBarWrap">
            <div
              className="playerBar"
              style={{ width: `${Math.round((v / max) * 100)}%` }}
              title={`${(v * 100).toFixed(1)}%`}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default PlayerCountGraph
