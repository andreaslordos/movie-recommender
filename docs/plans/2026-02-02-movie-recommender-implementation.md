# Movie Recommender Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a semantic search movie recommender that takes natural language queries and returns relevant movies using vector similarity.

**Architecture:** FastAPI backend embeds user queries via OpenAI, searches Supabase pgvector for similar movies, returns results to Next.js frontend displaying movie cards.

**Tech Stack:** FastAPI, Supabase (pgvector), OpenAI text-embedding-3-large, Next.js 16, React 19, Tailwind CSS

---

## Task 1: Supabase Database Setup

**Files:**
- Create: `backend/supabase_setup.sql`
- Modify: `backend/.env`

**Step 1: Create the SQL schema file**

Create `backend/supabase_setup.sql`:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create movies table
CREATE TABLE IF NOT EXISTS movies (
  id BIGINT PRIMARY KEY,
  title TEXT NOT NULL,
  overview TEXT,
  release_date DATE,
  poster_path TEXT,
  genres TEXT[],
  keywords TEXT[],
  vote_average FLOAT,
  vote_count INT,
  embedding VECTOR(3072)
);

-- Create index for fast similarity search (run AFTER data is loaded)
-- CREATE INDEX ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Step 2: Run SQL in Supabase**

1. Go to Supabase dashboard → SQL Editor
2. Paste and run the SQL above
3. Note: The index creation is commented out - run it AFTER embeddings are loaded

**Step 3: Update backend/.env**

Add these variables (get values from Supabase dashboard → Settings → API):

```
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=YOUR_ANON_KEY
```

**Step 4: Commit**

```bash
git add backend/supabase_setup.sql
git commit -m "feat: add Supabase schema for movies table with pgvector"
```

---

## Task 2: Add Python Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add required packages**

Add to `backend/requirements.txt`:

```
# Web framework
fastapi==0.128.0
uvicorn==0.40.0

# Data validation
pydantic==2.12.5

# Database
SQLAlchemy==2.0.46

# OpenAI embeddings
openai==1.59.9

# Supabase client
supabase==2.11.0

# Data processing (for embedding script)
pandas==2.2.3

# Environment variables
python-dotenv==1.0.1
```

**Step 2: Install dependencies**

```bash
cd backend && pip install -r requirements.txt
```

**Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add openai, supabase, pandas dependencies"
```

---

## Task 3: Create Embedding Script

**Files:**
- Create: `scripts/embed_movies.py`

**Step 1: Create the scripts directory and embedding script**

Create `scripts/embed_movies.py`:

```python
#!/usr/bin/env python3
"""
One-time script to embed movie data and upload to Supabase.
Run from project root: python scripts/embed_movies.py
"""

import os
import ast
import pandas as pd
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

# Load environment from backend/.env
load_dotenv("backend/.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables. Check backend/.env")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100


def parse_json_column(value):
    """Parse JSON-like string column, return empty list on failure."""
    if pd.isna(value) or value == "":
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return parsed
        return []
    except (ValueError, SyntaxError):
        return []


def extract_names(items, key="name"):
    """Extract 'name' field from list of dicts."""
    return [item.get(key, "") for item in items if isinstance(item, dict)]


def build_embedding_text(row):
    """Build the text string to embed for a movie."""
    title = row.get("title", "")
    overview = row.get("overview", "")
    genres = ", ".join(row.get("genre_names", []))
    keywords = ", ".join(row.get("keyword_names", [])[:20])  # Limit keywords

    parts = [title]
    if overview:
        parts.append(overview)
    if genres:
        parts.append(f"Genres: {genres}")
    if keywords:
        parts.append(f"Keywords: {keywords}")

    return ". ".join(parts)


def get_embeddings(texts):
    """Get embeddings for a batch of texts."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]


def main():
    print("Loading movies_metadata.csv...")
    movies_df = pd.read_csv("movie_data/movies_metadata.csv", low_memory=False)

    print("Loading keywords.csv...")
    keywords_df = pd.read_csv("movie_data/keywords.csv")

    # Parse genres from movies_metadata
    print("Parsing genres...")
    movies_df["genre_list"] = movies_df["genres"].apply(parse_json_column)
    movies_df["genre_names"] = movies_df["genre_list"].apply(extract_names)

    # Parse keywords
    print("Parsing keywords...")
    keywords_df["keyword_list"] = keywords_df["keywords"].apply(parse_json_column)
    keywords_df["keyword_names"] = keywords_df["keyword_list"].apply(extract_names)

    # Convert id columns to numeric for merging
    movies_df["id"] = pd.to_numeric(movies_df["id"], errors="coerce")
    keywords_df["id"] = pd.to_numeric(keywords_df["id"], errors="coerce")

    # Merge keywords into movies
    movies_df = movies_df.merge(
        keywords_df[["id", "keyword_names"]],
        on="id",
        how="left"
    )
    movies_df["keyword_names"] = movies_df["keyword_names"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    # Filter to movies with valid data
    print("Filtering movies...")
    valid_movies = movies_df[
        movies_df["id"].notna() &
        movies_df["title"].notna() &
        movies_df["overview"].notna() &
        (movies_df["overview"].str.len() > 10)
    ].copy()

    # Drop duplicates by id
    valid_movies = valid_movies.drop_duplicates(subset=["id"])

    print(f"Processing {len(valid_movies)} movies...")

    # Build embedding text
    valid_movies["embedding_text"] = valid_movies.apply(build_embedding_text, axis=1)

    # Process in batches
    total = len(valid_movies)
    uploaded = 0

    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch = valid_movies.iloc[start:end]

        print(f"Processing batch {start//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE}...")

        # Get embeddings
        texts = batch["embedding_text"].tolist()
        embeddings = get_embeddings(texts)

        # Prepare records for Supabase
        records = []
        for idx, (_, row) in enumerate(batch.iterrows()):
            # Parse release_date safely
            release_date = None
            if pd.notna(row.get("release_date")):
                try:
                    release_date = str(row["release_date"])[:10]  # YYYY-MM-DD
                except:
                    pass

            record = {
                "id": int(row["id"]),
                "title": str(row["title"]),
                "overview": str(row["overview"]) if pd.notna(row["overview"]) else None,
                "release_date": release_date,
                "poster_path": str(row["poster_path"]) if pd.notna(row.get("poster_path")) else None,
                "genres": row["genre_names"],
                "keywords": row["keyword_names"][:20],
                "vote_average": float(row["vote_average"]) if pd.notna(row.get("vote_average")) else None,
                "vote_count": int(row["vote_count"]) if pd.notna(row.get("vote_count")) else None,
                "embedding": embeddings[idx]
            }
            records.append(record)

        # Upsert to Supabase
        supabase.table("movies").upsert(records).execute()
        uploaded += len(records)
        print(f"Uploaded {uploaded}/{total} movies")

    print("Done! Remember to create the vector index in Supabase SQL Editor:")
    print("CREATE INDEX ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add scripts/embed_movies.py
git commit -m "feat: add movie embedding script for Supabase upload"
```

---

## Task 4: Run Embedding Script

**Prerequisite:** Ensure `backend/.env` has valid `OPENAI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY`

**Step 1: Run the script**

```bash
python scripts/embed_movies.py
```

Expected output:
```
Loading movies_metadata.csv...
Loading keywords.csv...
Parsing genres...
Parsing keywords...
Filtering movies...
Processing ~42000 movies...
Processing batch 1/420...
Uploaded 100/42000 movies
...
Done! Remember to create the vector index...
```

**Step 2: Create the vector index**

In Supabase SQL Editor, run:

```sql
CREATE INDEX ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Step 3: Verify data**

In Supabase SQL Editor:

```sql
SELECT COUNT(*) FROM movies;
SELECT id, title, genres FROM movies LIMIT 5;
```

---

## Task 5: Backend Search Endpoint

**Files:**
- Modify: `backend/main.py`

**Step 1: Implement the search endpoint**

Replace `backend/main.py` with:

```python
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EMBEDDING_MODEL = "text-embedding-3-large"


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class MovieResult(BaseModel):
    id: int
    title: str
    overview: str | None
    release_date: str | None
    poster_path: str | None
    genres: list[str]
    vote_average: float | None
    similarity: float


class SearchResponse(BaseModel):
    results: list[MovieResult]


@app.get("/")
def read_root():
    return {"status": "Backend running"}


@app.post("/search", response_model=SearchResponse)
async def search_movies(request: SearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Embed the query
    embedding_response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=request.query
    )
    query_embedding = embedding_response.data[0].embedding

    # Search Supabase using pgvector
    # Using RPC function for vector similarity search
    result = supabase.rpc(
        "match_movies",
        {
            "query_embedding": query_embedding,
            "match_count": request.limit
        }
    ).execute()

    movies = []
    for row in result.data:
        movies.append(MovieResult(
            id=row["id"],
            title=row["title"],
            overview=row["overview"],
            release_date=row["release_date"],
            poster_path=row["poster_path"],
            genres=row["genres"] or [],
            vote_average=row["vote_average"],
            similarity=row["similarity"]
        ))

    return SearchResponse(results=movies)
```

**Step 2: Create Supabase RPC function**

In Supabase SQL Editor, run:

```sql
CREATE OR REPLACE FUNCTION match_movies(
  query_embedding VECTOR(3072),
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id BIGINT,
  title TEXT,
  overview TEXT,
  release_date DATE,
  poster_path TEXT,
  genres TEXT[],
  vote_average FLOAT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.id,
    m.title,
    m.overview,
    m.release_date,
    m.poster_path,
    m.genres,
    m.vote_average,
    1 - (m.embedding <=> query_embedding) AS similarity
  FROM movies m
  WHERE m.embedding IS NOT NULL
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

**Step 3: Test the endpoint**

Start the server:
```bash
cd backend && uvicorn main:app --reload
```

Test with curl:
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "movie about a ship hitting an iceberg", "limit": 5}'
```

Expected: JSON response with Titanic at the top.

**Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: add /search endpoint with vector similarity search"
```

---

## Task 6: Frontend Search UI

**Files:**
- Modify: `frontend/app/page.tsx`
- Create: `frontend/app/components/MovieCard.tsx`
- Create: `frontend/app/components/SearchBar.tsx`

**Step 1: Create SearchBar component**

Create `frontend/app/components/SearchBar.tsx`:

```tsx
"use client"

import { useState } from "react"

interface SearchBarProps {
  onSearch: (query: string) => void
  isLoading: boolean
}

export default function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query.trim())
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Describe a movie you'd like to watch..."
          className="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </div>
    </form>
  )
}
```

**Step 2: Create MovieCard component**

Create `frontend/app/components/MovieCard.tsx`:

```tsx
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

interface MovieCardProps {
  movie: Movie
}

export default function MovieCard({ movie }: MovieCardProps) {
  const year = movie.release_date ? new Date(movie.release_date).getFullYear() : null
  const posterUrl = movie.poster_path
    ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
    : "/placeholder-poster.svg"

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
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
```

**Step 3: Update the main page**

Replace `frontend/app/page.tsx`:

```tsx
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
```

**Step 4: Create placeholder poster SVG**

Create `frontend/public/placeholder-poster.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300" fill="#e5e7eb">
  <rect width="200" height="300"/>
  <text x="100" y="150" text-anchor="middle" fill="#9ca3af" font-family="sans-serif" font-size="14">No Poster</text>
</svg>
```

**Step 5: Commit**

```bash
git add frontend/app/page.tsx frontend/app/components/ frontend/public/placeholder-poster.svg
git commit -m "feat: add search UI with movie cards"
```

---

## Task 7: Test End-to-End

**Step 1: Start backend**

```bash
cd backend && uvicorn main:app --reload
```

**Step 2: Start frontend**

```bash
cd frontend && npm run dev
```

**Step 3: Test in browser**

1. Open http://localhost:3000
2. Search for "movie about a ship hitting an iceberg"
3. Verify Titanic appears in results
4. Test other queries:
   - "funny movie about toys coming to life"
   - "scary horror movie in space"
   - "romantic comedy in New York"

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete movie recommender MVP"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Supabase schema setup |
| 2 | Python dependencies |
| 3 | Embedding script |
| 4 | Run embeddings (one-time) |
| 5 | Backend /search endpoint |
| 6 | Frontend search UI |
| 7 | End-to-end testing |

**Total estimated one-time cost:** ~$2-3 for embedding 45k movies
