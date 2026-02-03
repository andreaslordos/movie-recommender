"use client"

import { useEffect } from "react"
import type { Movie } from "./MovieCard"

interface MovieModalProps {
  movie: Movie
  onClose: () => void
}

export default function MovieModal({ movie, onClose }: MovieModalProps) {
  const year = movie.release_date ? new Date(movie.release_date).getFullYear() : null
  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : "/placeholder-poster.svg"
  const tmdbUrl = `https://www.themoviedb.org/movie/${movie.id}`

  useEffect(() => {
    document.body.style.overflow = "hidden"
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.body.style.overflow = ""
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="relative">
          {/* Header with poster and basic info */}
          <div className="flex gap-6 p-6 pb-4">
            <div className="w-40 flex-shrink-0">
              <div className="aspect-[2/3] rounded-lg overflow-hidden bg-gray-200 shadow-md">
                <img
                  src={posterUrl}
                  alt={movie.title}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.currentTarget.src = "/placeholder-poster.svg"
                  }}
                />
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <button
                onClick={onClose}
                className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Close"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              <h2 className="text-2xl font-bold text-gray-900 pr-8">
                {movie.title}
              </h2>

              {year && (
                <p className="text-gray-500 mt-1">{year}</p>
              )}

              {/* Rating */}
              {movie.vote_average != null && (
                <div className="flex items-center gap-2 mt-3">
                  <span className="text-yellow-500 text-lg">&#9733;</span>
                  <span className="font-semibold text-gray-900">
                    {movie.vote_average.toFixed(1)}
                  </span>
                  <span className="text-sm text-gray-400">/&nbsp;10</span>
                  {movie.vote_count != null && (
                    <span className="text-sm text-gray-400">
                      ({movie.vote_count.toLocaleString()} votes)
                    </span>
                  )}
                </div>
              )}

              {/* Match score */}
              <div className="mt-3">
                <span className="inline-block text-xs font-medium bg-indigo-50 text-indigo-700 px-2 py-1 rounded-full">
                  {(movie.similarity * 100).toFixed(0)}% match
                </span>
              </div>

              {/* Genres */}
              {movie.genres.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {movie.genres.map((genre) => (
                    <span
                      key={genre}
                      className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full"
                    >
                      {genre}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Overview */}
          {movie.overview && (
            <div className="px-6 pb-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-1">Overview</h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                {movie.overview}
              </p>
            </div>
          )}

          {/* Keywords */}
          {movie.keywords.length > 0 && (
            <div className="px-6 pb-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Keywords</h3>
              <div className="flex flex-wrap gap-1.5">
                {movie.keywords.map((keyword) => (
                  <span
                    key={keyword}
                    className="text-xs bg-gray-50 text-gray-500 px-2 py-0.5 rounded border border-gray-200"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Links */}
          <div className="px-6 pb-6 pt-2 flex gap-3">
            <a
              href={tmdbUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              View on TMDB
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
