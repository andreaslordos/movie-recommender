"use client"

import { useState } from "react"
import SearchBar from "./components/SearchBar"
import MovieCard from "./components/MovieCard"

interface Movie {
  id: number
  title: string
  overview: string | null
  release_date: string | null
  poster_path: string | null
  genres: string[]
  vote_average: number | null
  similarity: number
}

export default function Home() {
  const [movies, setMovies] = useState<Movie[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)

  const handleSearch = async (query: string) => {
    setIsLoading(true)
    setError(null)
    setHasSearched(true)

    try {
      const response = await fetch("http://localhost:8000/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 10 }),
      })

      if (!response.ok) {
        throw new Error("Search failed")
      }

      const data = await response.json()
      setMovies(data.results)
    } catch (err) {
      setError("Failed to search movies. Please try again.")
      setMovies([])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Movie Recommender
          </h1>
          <p className="text-gray-600">
            Describe what you're in the mood for and find your next favorite movie
          </p>
        </div>

        <div className="flex justify-center mb-12">
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />
        </div>

        {error && (
          <div className="text-center text-red-600 mb-8">{error}</div>
        )}

        {isLoading && (
          <div className="text-center text-gray-500">
            Searching for movies...
          </div>
        )}

        {!isLoading && hasSearched && movies.length === 0 && !error && (
          <div className="text-center text-gray-500">
            No movies found. Try a different description.
          </div>
        )}

        {movies.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {movies.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
