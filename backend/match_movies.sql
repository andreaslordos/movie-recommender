CREATE OR REPLACE FUNCTION match_movies(
  query_embedding VECTOR(1536),
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
