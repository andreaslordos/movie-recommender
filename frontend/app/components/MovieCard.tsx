interface Movie {
  id: number
  title: string
  overview: string | null
  release_date: string | null
  poster_path: string | null
  genres: string[]
  keywords: string[]
  vote_average: number | null
  vote_count: number | null
  similarity: number
}

interface MovieCardProps {
  movie: Movie
  onClick: () => void
}

export type { Movie }

export default function MovieCard({ movie, onClick }: MovieCardProps) {
  const year = movie.release_date ? new Date(movie.release_date).getFullYear() : null
  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : "/placeholder-poster.svg"

  return (
    <div
      className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="aspect-[2/3] relative bg-gray-200">
        <img
          src={posterUrl}
          alt={movie.title}
          className="w-full h-full object-cover"
          onError={(e) => {
            e.currentTarget.src = "/placeholder-poster.svg"
          }}
        />
        {movie.vote_average && (
          <div className="absolute top-2 right-2 bg-black/70 text-white text-sm px-2 py-1 rounded">
            {movie.vote_average.toFixed(1)}
          </div>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 truncate" title={movie.title}>
          {movie.title}
        </h3>
        {year && <p className="text-sm text-gray-500">{year}</p>}
        {movie.genres.length > 0 && (
          <p className="text-xs text-gray-400 mt-1 truncate">
            {movie.genres.slice(0, 3).join(" • ")}
          </p>
        )}
        {movie.overview && (
          <p className="text-sm text-gray-600 mt-2 line-clamp-3">
            {movie.overview}
          </p>
        )}
      </div>
    </div>
  )
}
