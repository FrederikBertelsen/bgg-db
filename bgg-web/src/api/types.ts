export type Rank = {
  name: string
  value: number
}

export type GameLink = {
  id: string
  name: string
}

export type GameVersion = {
  id: number
  language: string
  name: string
  publisher: string
  thumbnail: string
  volume: string
  weight: string
  year_published: number
}

export type GameCard = {
  id: string
  name: string
  max_players: number
  max_playing_time: number
  min_players: number
  min_playing_time: number
  niches: string[]
  year_published: number
  rating: number
  weight: number
  short_description: string | null
  thumbnail: string | null
  ranks: Rank[]
  score: number
}

export type FullGame = {
  alternative_names: string[]
  artists: string[]
  components: string[]
  id: string
  description: string
  designers: string[]
  estimated_volume_cm3: number
  estimated_weight_kg: number
  expands: string[]
  expansions: GameLink[]
  image: string
  implementations: string[]
  max_players: number
  max_playing_time: number
  mechanics: string[]
  min_age: number
  min_players: number
  min_playing_time: number
  name: string
  niches: string[]
  player_count_scores: Record<string, number>
  playing_time: number
  publishers: string[]
  ranks: Rank[]
  rating: number
  rating_count: number
  rating_stddev: number
  short_description: string
  tags: string[]
  themes: string[]
  thumbnail: string
  types: string[]
  versions: GameVersion[]
  weight: number
  year_published: number
}
