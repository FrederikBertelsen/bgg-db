export type Rank = {
  category: string
  rank: string
  bayes_average: string
}

export type GameCard = {
  id: string
  name: string
  year_published: number | null
  min_players: number | null
  max_players: number | null
  min_playtime: number | null
  max_playtime: number | null
  rating_average: number | null
  weight_average: number | null
  short_description: string | null
  thumbnail_url: string | null
  ranks: Rank[]
  score: number | null
}

export type FullGame = {
  id: string
  name: string
  description?: string
  image_url?: string
  thumbnail_url?: string
  url?: string

  year_published?: number
  min_players?: number
  max_players?: number
  min_playtime?: number
  max_playtime?: number
  min_age?: number

  rating_average?: number
  bayes_rating_average?: number
  weight_average?: number
  ranks?: Rank[]

  categories?: string[]
  mechanics?: string[]
  honors?: string[]

  // Allow backend to evolve without breaking the UI.
  [key: string]: unknown
}
