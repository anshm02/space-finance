# Space Money Backend - Lean Technologies Integration

FastAPI backend service with Lean Technologies Open Finance API integration.

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your Lean credentials
# Get credentials from: https://dev.leantech.me
```

### 2. Setup Database

```bash
# Create PostgreSQL database
createdb space_money

# Run migrations
alembic upgrade head

# Create data directories
mkdir -p data/raw data/metadata
```

### 3. Start Server

```bash
# Start with auto-reload
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --port 8000
```

Server will be available at: http://localhost:8000

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run integration tests
python test_lean_integration.py
```

## Key Endpoints

- `POST /api/v1/lean/customers` - Create Lean customer
- `POST /api/v1/lean/entities/link` - Link bank account
- `POST /api/v1/lean/sync` - Sync financial data
- `GET /api/v1/lean/accounts/{entity_id}` - Get accounts

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string
- `LEAN_APP_TOKEN` - Lean app token
- `LEAN_CLIENT_ID` - Lean client ID
- `LEAN_CLIENT_SECRET` - Lean client secret

Optional:
- `LEAN_BASE_URL` - Lean API base URL (default: sandbox)
- `DATA_DIR` - Data directory path (default: ./data)

## Development

### Project Structure

```
backend/
├── main.py                 # FastAPI app
├── config.py              # Configuration
├── database.py            # Database setup
├── models.py              # SQLAlchemy models
├── schemas.py             # Pydantic schemas
├── routers/               # API routes
│   └── lean.py           # Lean endpoints
├── services/              # Business logic
│   ├── lean_client.py    # Lean API client
│   └── data_service.py   # Data extraction
└── alembic/              # Database migrations
```

### Code Style

- Async/await for all I/O operations
- Type hints on all functions
- Pydantic models for validation
- Service layer for business logic
- Dependency injection pattern

See full documentation in: `../specs/lean-tech-integration/implementation-notes.md`
