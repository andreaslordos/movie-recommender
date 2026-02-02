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
  embedding VECTOR(1536)
);

-- Create index for fast similarity search (run AFTER data is loaded)
-- CREATE INDEX ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
