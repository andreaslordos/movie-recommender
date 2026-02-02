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
