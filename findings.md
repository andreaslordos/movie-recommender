# Movie Data Analysis Findings

## Overview

The `movie_data/` directory contains 7 CSV files from TMDB (The Movie Database) and MovieLens datasets. These files provide comprehensive movie metadata, credits, keywords, user ratings, and cross-reference IDs.

---

## File Summaries

### 1. movies_metadata.csv
- **Size**: 34.4 MB | **Rows**: ~45,571
- **Purpose**: Core movie information

| Column | Description |
|--------|-------------|
| `id` | TMDB movie ID (primary key) |
| `imdb_id` | IMDB identifier (e.g., `tt0114709`) |
| `title` / `original_title` | Movie title |
| `overview` | Plot synopsis |
| `release_date` | Release date |
| `runtime` | Duration in minutes |
| `budget` / `revenue` | Financial data in USD |
| `popularity` | TMDB popularity score |
| `vote_average` / `vote_count` | User rating statistics |
| `genres` | JSON array of genre objects |
| `belongs_to_collection` | JSON object for film series |
| `production_companies` | JSON array of studios |
| `production_countries` | JSON array of countries |
| `spoken_languages` | JSON array of languages |
| `adult` | Boolean for adult content |
| `homepage` | Official website URL |
| `poster_path` | TMDB poster image path |
| `status` | Release status |
| `tagline` | Marketing tagline |
| `video` | Has video content |

---

### 2. credits.csv
- **Size**: 189.9 MB | **Rows**: ~45,476
- **Purpose**: Cast and crew information

| Column | Description |
|--------|-------------|
| `id` | TMDB movie ID (foreign key to movies_metadata) |
| `cast` | JSON array of cast members with: `cast_id`, `character`, `name`, `gender`, `order`, `profile_path` |
| `crew` | JSON array of crew members with: `department`, `job`, `name`, `gender`, `profile_path` |

---

### 3. keywords.csv
- **Size**: 6.2 MB | **Rows**: ~46,419
- **Purpose**: Searchable tags/themes for movies

| Column | Description |
|--------|-------------|
| `id` | TMDB movie ID (foreign key to movies_metadata) |
| `keywords` | JSON array of keyword objects with `id` and `name` (e.g., "jealousy", "friendship", "toy comes to life") |

---

### 4. ratings.csv
- **Size**: 709.5 MB | **Rows**: ~26,024,289
- **Purpose**: Full MovieLens user ratings dataset

| Column | Description |
|--------|-------------|
| `userId` | Unique user identifier |
| `movieId` | MovieLens movie ID (**not** TMDB ID) |
| `rating` | Rating value (0.5 to 5.0 scale, half-star increments) |
| `timestamp` | Unix timestamp of rating |

---

### 5. ratings_small.csv
- **Size**: 2.4 MB | **Rows**: ~100,004
- **Purpose**: Subset of ratings for development/testing

Same schema as `ratings.csv`.

---

### 6. links.csv
- **Size**: 989 KB | **Rows**: ~45,843
- **Purpose**: ID mapping between MovieLens and external databases

| Column | Description |
|--------|-------------|
| `movieId` | MovieLens movie ID |
| `imdbId` | IMDB ID (without `tt` prefix) |
| `tmdbId` | TMDB ID (links to movies_metadata.id) |

---

### 7. links_small.csv
- **Size**: 183 KB | **Rows**: ~9,125
- **Purpose**: Subset of links for development/testing

Same schema as `links.csv`.

---

## Data Relationships

```
┌─────────────────────┐
│  movies_metadata    │
│  (id = tmdbId)      │
└─────────┬───────────┘
          │
    ┌─────┴─────┬────────────┐
    │           │            │
    ▼           ▼            ▼
┌────────┐ ┌──────────┐ ┌─────────────┐
│credits │ │ keywords │ │   links     │
│ (id)   │ │  (id)    │ │ (tmdbId)    │
└────────┘ └──────────┘ └──────┬──────┘
                               │
                               ▼
                        ┌────────────┐
                        │  ratings   │
                        │ (movieId)  │
                        └────────────┘
```

**Key Insight**: To connect ratings data to movie metadata:
1. Use `links.csv` to map `movieId` (MovieLens) → `tmdbId` (TMDB)
2. Join on `movies_metadata.id` using `tmdbId`

---

## Data Quality Notes

- **Nested JSON**: `genres`, `cast`, `crew`, `keywords`, `production_companies`, and `belongs_to_collection` columns contain JSON-encoded arrays/objects that need parsing
- **Missing Values**: Some movies have empty/zero values for `budget`, `revenue`, `homepage`
- **ID Systems**: Two different ID systems are in use:
  - **TMDB IDs**: Used in `movies_metadata`, `credits`, `keywords`
  - **MovieLens IDs**: Used in `ratings` (requires `links.csv` for mapping)

---

## Recommended Use Cases

| Use Case | Primary Files |
|----------|---------------|
| Content-based filtering | `movies_metadata`, `keywords`, `credits` |
| Collaborative filtering | `ratings`, `links` |
| Hybrid recommender | All files |
| Development/Testing | `*_small.csv` variants |
