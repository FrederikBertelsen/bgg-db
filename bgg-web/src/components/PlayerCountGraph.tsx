type Props = {
  scores: Record<string, number>
}

export function PlayerCountGraph({ scores }: Props) {
  const entries = Object.entries(scores)
    .filter(([, value]) => typeof value === 'number')
    .sort(([a], [b]) => {
      // Handle anything with '+' as largest (sort to end)
      const aHasPlus = a.includes('+')
      const bHasPlus = b.includes('+')
      if (aHasPlus && !bHasPlus) return 1
      if (!aHasPlus && bHasPlus) return -1
      return Number(a) - Number(b)
    })
    .map(([k, v]) => ({ k, v: typeof v === 'number' ? v : 0 }))
  
  const max = entries.reduce((m, e) => (e.v > m ? e.v : m), 0.0001)

  return (
    <div className="playerGraphColumns">
      {entries.map(({ k, v }) => {
        const heightPercent = Math.round((v / max) * 100)
        return (
          <div key={k} className="playerColumn">
            <div
              className="playerBarSpacer"
              style={{ flex: `0 1 ${100 - heightPercent}%` }}
            />
            <div
              className="playerBarVertical"
              style={{ flex: `0 1 ${heightPercent}%` }}
            />
            <div className="playerBarLabel">{k}</div>
          </div>
        )
      })}
    </div>
  )
}

export default PlayerCountGraph
