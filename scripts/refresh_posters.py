#!/usr/bin/env python3
"""
Bulk-refresh poster_path values from the TMDB API.
Run from project root: python scripts/refresh_posters.py

Phase 1: Fetches current poster_path for all movie IDs from TMDB API
         and writes results to scripts/poster_updates.json
Phase 2: Run with --apply flag to update Supabase from that JSON file.

Requires TMDB_API_KEY in backend/.env (free at themoviedb.org).
No external dependencies needed for Phase 1 (stdlib only).
"""

import os
import sys
import json
import csv
import time
import signal
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from dotenv import load_dotenv

load_dotenv("backend/.env")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

OUTPUT_FILE = "scripts/poster_updates.json"
MAX_WORKERS = 20  # Thread pool size
RATE_LIMIT = 35   # Requests per second (TMDB allows ~40)
PROGRESS_EVERY = 500

# Simple rate limiter using a semaphore + sleep
_rate_semaphore = Semaphore(RATE_LIMIT)


def fetch_poster(movie_id: int) -> tuple[int, str | None]:
    """Fetch current poster_path for a single movie from TMDB API."""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return (movie_id, data.get("poster_path"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return (movie_id, None)
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 2))
                time.sleep(retry_after)
                continue
            return (movie_id, None)
        except Exception:
            if attempt < 2:
                time.sleep(1)
                continue
            return (movie_id, None)

    return (movie_id, None)


def rate_limited_fetch(movie_id: int) -> tuple[int, str | None]:
    """Wrapper that enforces rate limiting."""
    _rate_semaphore.acquire()
    try:
        return fetch_poster(movie_id)
    finally:
        # Release after a delay to enforce rate limit
        import threading
        threading.Timer(1.0, _rate_semaphore.release).start()


def load_movie_ids() -> list[int]:
    """Load all unique movie IDs from the CSV dataset."""
    ids = set()
    with open("movie_data/movies_metadata.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ids.add(int(row["id"]))
            except (ValueError, KeyError):
                pass
    return sorted(ids)


def phase1_fetch():
    """Phase 1: Fetch all poster paths from TMDB and save to JSON."""
    if not TMDB_API_KEY:
        print("ERROR: Set TMDB_API_KEY in backend/.env")
        print("Get a free key at https://www.themoviedb.org/settings/api")
        sys.exit(1)

    # Quick validation that the API key works
    print("Validating TMDB API key...")
    test_url = f"https://api.themoviedb.org/3/movie/862?api_key={TMDB_API_KEY}"
    try:
        req = urllib.request.Request(test_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"  API key works! Test: Toy Story poster = {data.get('poster_path')}")
    except urllib.error.HTTPError as e:
        print(f"  ERROR: TMDB API returned {e.code}. Check your API key.")
        sys.exit(1)

    print("\nLoading movie IDs from CSV...")
    movie_ids = load_movie_ids()
    print(f"Found {len(movie_ids)} unique movie IDs")

    # Resume support: skip already-fetched IDs
    results = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing = json.load(f)
        for mid_str, path in existing.get("poster_paths", {}).items():
            results[int(mid_str)] = path
        for mid in existing.get("not_found_ids", []):
            results[int(mid)] = None
        already = len(results)
        movie_ids = [mid for mid in movie_ids if mid not in results]
        print(f"Resuming: {already} already fetched, {len(movie_ids)} remaining")

    if not movie_ids:
        print("All movies already fetched! Use --apply to update Supabase.")
        return

    total = len(movie_ids)
    print(f"\nFetching poster paths from TMDB API ({MAX_WORKERS} threads, {RATE_LIMIT}/sec)...")
    start_time = time.time()
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(rate_limited_fetch, mid): mid for mid in movie_ids}

        for future in as_completed(futures):
            movie_id, poster_path = future.result()
            results[movie_id] = poster_path
            done += 1

            if done % PROGRESS_EVERY == 0 or done == total:
                elapsed = time.time() - start_time
                rate = done / elapsed if elapsed > 0 else 0
                found = sum(1 for v in results.values() if v is not None)
                print(f"  {done}/{total} fetched ({rate:.1f}/sec) — {found} posters found so far")

            # Save checkpoint every 2000 movies
            if done % 2000 == 0:
                _save_results(results)

    _save_results(results)

    found = sum(1 for v in results.values() if v is not None)
    not_found = sum(1 for v in results.values() if v is None)
    print(f"\nResults:")
    print(f"  Posters found:     {found}")
    print(f"  Not found / gone:  {not_found}")
    print(f"\nSaved to {OUTPUT_FILE}")
    print(f"Run 'python scripts/refresh_posters.py --apply' to update Supabase.")


def _save_results(results: dict[int, str | None]):
    """Save current results to JSON (checkpoint-safe)."""
    found = {str(k): v for k, v in results.items() if v is not None}
    not_found = [k for k, v in results.items() if v is None]

    output = {
        "poster_paths": found,
        "not_found_ids": not_found,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_fetched": len(results),
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f)


def phase2_apply():
    """Phase 2: Read JSON and bulk-update Supabase poster_path values."""
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY in backend/.env")
        sys.exit(1)

    if not os.path.exists(OUTPUT_FILE):
        print(f"ERROR: {OUTPUT_FILE} not found. Run without --apply first.")
        sys.exit(1)

    from supabase import create_client

    print(f"Loading poster data from {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)

    poster_paths = data["poster_paths"]
    print(f"  {len(poster_paths)} poster paths to update")
    print(f"  Data fetched at: {data.get('fetched_at', 'unknown')}")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Use bulk_update_posters RPC to update thousands of rows per call.
    # Run backend/bulk_update_posters.sql in the Supabase SQL Editor first.
    items = [{"id": int(mid), "poster_path": path} for mid, path in poster_paths.items()]
    total = len(items)

    batch_size = 500  # rows per RPC call (Supabase has statement timeouts)
    updated = 0

    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        result = supabase.rpc("bulk_update_posters", {"updates": batch}).execute()
        affected = result.data if isinstance(result.data, int) else len(batch)
        updated += affected
        print(f"  Updated {updated}/{total}")

    print(f"\nDone! Updated {updated} poster paths in Supabase.")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        phase2_apply()
    else:
        phase1_fetch()
