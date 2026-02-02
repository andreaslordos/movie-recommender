#!/usr/bin/env python3
"""
One-time script to embed movie data and upload to Supabase.
Run from project root: python scripts/embed_movies.py

Uses parallel processing for faster embedding of ~45k movies.
"""

import os
import asyncio
from openai import AsyncOpenAI
from supabase import create_client
from dotenv import load_dotenv
import polars as pl

# Load environment from backend/.env
load_dotenv("backend/.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables. Check backend/.env")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100  # Movies per API call
MAX_CONCURRENT = 5  # Concurrent API calls (reduced for stability)
MAX_RETRIES = 3  # Retries per batch


def parse_json_safe(value: str | None) -> list:
    """Parse JSON-like string, return empty list on failure."""
    if value is None or value == "" or value == "[]":
        return []
    try:
        # Handle Python-style dicts (single quotes) by using eval
        # This is safe here since we control the source data
        parsed = eval(value)  # noqa: S307
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception:
        return []


def extract_names(items: list, key: str = "name") -> list[str]:
    """Extract 'name' field from list of dicts."""
    return [item.get(key, "") for item in items if isinstance(item, dict)]


def build_embedding_text(title: str, overview: str, genres: list[str], keywords: list[str]) -> str:
    """Build the text string to embed for a movie."""
    parts = [title] if title else []
    if overview:
        parts.append(overview)
    if genres:
        parts.append(f"Genres: {', '.join(genres)}")
    if keywords:
        parts.append(f"Keywords: {', '.join(keywords[:20])}")
    return ". ".join(parts)


async def get_embeddings_batch(texts: list[str], semaphore: asyncio.Semaphore) -> list[list[float]]:
    """Get embeddings for a batch of texts with rate limiting and retry."""
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                response = await openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                    timeout=60.0  # 60 second timeout
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                    print(f"  Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    raise


async def process_and_upload_batch(
    batch_num: int,
    rows: list[dict],
    semaphore: asyncio.Semaphore,
    total_batches: int
) -> int:
    """Process a batch: get embeddings and upload to Supabase."""
    # Build embedding texts
    texts = []
    for row in rows:
        text = build_embedding_text(
            row["title"],
            row["overview"],
            row["genres"],
            row["keywords"]
        )
        texts.append(text)

    # Get embeddings
    embeddings = await get_embeddings_batch(texts, semaphore)

    # Prepare records for Supabase
    records = []
    for idx, row in enumerate(rows):
        record = {
            "id": row["id"],
            "title": row["title"],
            "overview": row["overview"],
            "release_date": row["release_date"],
            "poster_path": row["poster_path"],
            "genres": row["genres"],
            "keywords": row["keywords"][:20] if row["keywords"] else [],
            "vote_average": row["vote_average"],
            "vote_count": row["vote_count"],
            "embedding": embeddings[idx]
        }
        records.append(record)

    # Upsert to Supabase
    supabase.table("movies").upsert(records).execute()

    print(f"Batch {batch_num}/{total_batches} complete ({len(rows)} movies)")
    return len(rows)


async def main():
    print("Loading movies_metadata.csv...")
    movies_df = pl.read_csv(
        "movie_data/movies_metadata.csv",
        infer_schema_length=10000,
        ignore_errors=True,  # Skip malformed rows
        schema_overrides={"adult": pl.String, "id": pl.String}  # Read as strings first
    )

    print("Loading keywords.csv...")
    keywords_df = pl.read_csv("movie_data/keywords.csv")

    # Parse genres from movies_metadata
    print("Parsing genres...")
    movies_df = movies_df.with_columns(
        pl.col("genres").map_elements(
            lambda x: extract_names(parse_json_safe(x)),
            return_dtype=pl.List(pl.String)
        ).alias("genre_names")
    )

    # Parse keywords
    print("Parsing keywords...")
    keywords_df = keywords_df.with_columns(
        pl.col("keywords").map_elements(
            lambda x: extract_names(parse_json_safe(x)),
            return_dtype=pl.List(pl.String)
        ).alias("keyword_names")
    )

    # Cast IDs to integers for joining
    movies_df = movies_df.with_columns(
        pl.col("id").cast(pl.Int64, strict=False)
    )
    keywords_df = keywords_df.with_columns(
        pl.col("id").cast(pl.Int64, strict=False)
    )

    # Join keywords into movies
    print("Joining keywords...")
    movies_df = movies_df.join(
        keywords_df.select(["id", "keyword_names"]),
        on="id",
        how="left"
    )

    # Fill null keyword_names with empty lists
    movies_df = movies_df.with_columns(
        pl.col("keyword_names").fill_null([])
    )

    # Filter to valid movies
    print("Filtering movies...")
    valid_movies = movies_df.filter(
        pl.col("id").is_not_null() &
        pl.col("title").is_not_null() &
        pl.col("overview").is_not_null() &
        (pl.col("overview").str.len_chars() > 10)
    ).unique(subset=["id"])

    total = len(valid_movies)
    print(f"Processing {total} movies with {MAX_CONCURRENT} concurrent batches...")

    # Prepare rows for processing
    rows = []
    for row in valid_movies.iter_rows(named=True):
        # Parse release_date safely
        release_date = None
        if row.get("release_date"):
            try:
                rd = str(row["release_date"])
                if len(rd) >= 10 and rd[4] == "-":
                    release_date = rd[:10]
            except Exception:
                pass

        rows.append({
            "id": int(row["id"]),
            "title": str(row["title"]) if row.get("title") else "",
            "overview": str(row["overview"]) if row.get("overview") else None,
            "release_date": release_date,
            "poster_path": str(row["poster_path"]) if row.get("poster_path") and row["poster_path"] != "nan" else None,
            "genres": row.get("genre_names") or [],
            "keywords": row.get("keyword_names") or [],
            "vote_average": float(row["vote_average"]) if row.get("vote_average") is not None else None,
            "vote_count": int(row["vote_count"]) if row.get("vote_count") is not None else None,
        })

    # Create batches
    batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    total_batches = len(batches)

    # Process batches concurrently
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = [
        process_and_upload_batch(i + 1, batch, semaphore, total_batches)
        for i, batch in enumerate(batches)
    ]

    results = await asyncio.gather(*tasks)
    total_uploaded = sum(results)

    print(f"\nDone! Uploaded {total_uploaded} movies.")
    print("\nNow run this in Supabase SQL Editor to create the search index:")
    print("CREATE INDEX ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")


if __name__ == "__main__":
    asyncio.run(main())
