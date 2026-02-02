# Fullstack Template

A modern fullstack starter template with Next.js 16 and FastAPI.

## Tech Stack

**Frontend**
- Next.js 16 with App Router
- React 19
- TypeScript
- Tailwind CSS 4

**Backend**
- FastAPI
- Pydantic
- SQLAlchemy

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+

### Backend Setup

```bash
# Create virtual environment (at project root)
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment variables
cp backend/.env.example backend/.env

# Run the server
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Run the development server
npm run dev
```

The app will be available at `http://localhost:3000`

## Project Structure

```
.
├── .venv/                   # Python virtual environment (at root)
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Backend environment template
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── public/              # Static assets
│   ├── package.json         # Node dependencies
│   └── .env.example         # Frontend environment template
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/`      | Health check |

## Development

### Running Both Services

Open two terminal windows:

```bash
# Terminal 1 - Backend (from project root)
source .venv/bin/activate && uvicorn backend.main:app --reload

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## License

MIT
