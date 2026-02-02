# Movie Recommender Design

## Overview

A semantic search-based movie recommender that takes natural language queries (e.g., "movie about a ship hitting an iceberg") and returns 5-10 relevant movies using vector similarity search.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js       │────▶│   FastAPI       │────▶│   Supabase      │
│   Frontend      │     │   Backend       │     │   (pgvector)    │
│                 │◀────│                 │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   OpenAI API    │
                        │   (embeddings)  │
                        └─────────────────┘
```

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Vector Store | Supabase (pgvector) | Hosted Postgres + vector search in one, free tier available |
| Embedding Model | OpenAI `text-embedding-3-large` | Best quality, 3072 dimensions, ~$2-3 one-time cost for 45k movies |
| Backend | FastAPI (existing) | Already set up, excellent for async API calls |
| Frontend | Next.js + React (existing) | Already set up with Tailwind |

## Data Model

### Supabase Table: `movies`

```sql
CREATE TABLE movies (
  id BIGINT PRIMARY KEY,              -- TMDB ID
  title TEXT NOT NULL,
  overview TEXT,
  release_date DATE,
  poster_path TEXT,
  genres TEXT[],                      -- Array of genre names
  keywords TEXT[],                    -- Array of keyword names
  vote_average FLOAT,
  vote_count INT,
  embedding VECTOR(3072)              -- text-embedding-3-large output
);

-- Index for fast similarity search
CREATE INDEX ON movies USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

### Embedded Content Format

For each movie, concatenate into a single string:

```
{title}. {overview} Genres: {genre1}, {genre2}. Keywords: {keyword1}, {keyword2}, {keyword3}...
```

Example:
```
Titanic. A seventeen-year-old aristocrat falls in love with a kind but poor artist
aboard the luxurious, ill-fated R.M.S. Titanic. Genres: Drama, Romance.
Keywords: iceberg, ship, love, disaster, ocean, tragedy...
```

## API Design

### POST /search

**Request:**
```json
{
  "query": "movie about a ship hitting an iceberg",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 597,
      "title": "Titanic",
      "overview": "A seventeen-year-old aristocrat...",
      "release_date": "1997-11-18",
      "poster_path": "/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg",
      "genres": ["Drama", "Romance"],
      "vote_average": 7.9,
      "similarity": 0.89
    }
  ]
}
```

## Frontend Design

Minimal single-page interface:

```
┌──────────────────────────────────────────────────────┐
│                  Movie Recommender                    │
│                                                       │
│  ┌─────────────────────────────────────┐  ┌────────┐ │
│  │ Describe a movie you'd like...      │  │ Search │ │
│  └─────────────────────────────────────┘  └────────┘ │
│                                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│  │ Poster  │ │ Poster  │ │ Poster  │ │ Poster  │    │
│  │         │ │         │ │         │ │         │    │
│  │ Title   │ │ Title   │ │ Title   │ │ Title   │    │
│  │ Year    │ │ Year    │ │ Year    │ │ Year    │    │
│  │ Overview│ │ Overview│ │ Overview│ │ Overview│    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
└──────────────────────────────────────────────────────┘
```

- Search input with submit button
- Grid of movie cards (4 per row on desktop, 2 on mobile)
- Each card shows: poster image, title, year, truncated overview, genres
- Loading state while searching
- Poster images from TMDB CDN: `https://image.tmdb.org/t/p/w500{poster_path}`

## Implementation Plan

### Step 1: Supabase Setup
- Create Supabase project
- Enable pgvector extension
- Create `movies` table with schema above
- Get connection string and API keys

### Step 2: Embedding Script (`scripts/embed_movies.py`)
- Load `movies_metadata.csv` and `keywords.csv`
- Parse JSON fields (genres, keywords)
- Filter to movies with valid overview (skip empty)
- Build combined text for each movie
- Batch embed via OpenAI API (100 movies per batch)
- Upload to Supabase in batches
- Progress logging

### Step 3: Backend Search Endpoint
- Add `supabase` and `openai` Python packages
- Create `/search` POST endpoint
- Embed incoming query with OpenAI
- Query Supabase with pgvector similarity
- Return top N results with metadata

### Step 4: Frontend Search UI
- Replace placeholder page with search interface
- Search input component
- Movie card grid component
- API call to backend on submit
- Loading and empty states

### Step 5: Polish
- Error handling (API failures, empty results)
- Add "no results" message
- Mobile responsive layout

## Environment Variables

**Backend `.env`:**
```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
```

**Frontend `.env.local`:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Estimated Costs

| Item | Cost |
|------|------|
| Embedding 45k movies (one-time) | ~$2-3 |
| Query embedding (per search) | ~$0.0001 |
| Supabase free tier | $0 (up to 500MB, 50k rows) |

## Out of Scope (Future Enhancements)

- User accounts and saved preferences
- Collaborative filtering from ratings data
- Filters (genre, year, rating)
- "More like this" for individual movies
- Re-embedding when data updates
