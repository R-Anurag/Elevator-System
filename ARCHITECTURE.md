# Elevator System Architecture

## Microservices Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   Frontend     │  Next.js React App
                    │   Port: 3000   │  - Real-time UI
                    └────────┬───────┘  - WebSocket client
                             │
                             ▼
                    ┌────────────────┐
                    │   Backend      │  FastAPI Service
                    │   Port: 8000   │  - Elevator logic
                    └────────┬───────┘  - WebSocket server
                             │          - Business rules
                             ▼
                    ┌────────────────┐
                    │  DB Service    │  FastAPI REST API
                    │   Port: 8001   │  - Data persistence
                    └────────┬───────┘  - CRUD operations
                             │
                             ▼
                    ┌────────────────┐
                    │  PostgreSQL    │  Database
                    │   Port: 5432   │  - State storage
                    └────────────────┘  - History logs
```

## Service Responsibilities

### Frontend (Next.js)
**Location:** `frontend/`
**Port:** 3000

- User interface rendering
- Real-time elevator visualization
- WebSocket connection to backend
- User interaction handling

**Key Files:**
- `src/components/` - React components
- `src/hooks/useElevatorSocket.ts` - WebSocket hook
- `src/lib/api.ts` - HTTP client

### Backend (FastAPI)
**Location:** `backend/`
**Port:** 8000

- Elevator control logic
- Request scheduling algorithms
- Simulation engine
- WebSocket broadcasting
- Business rule enforcement

**Key Files:**
- `app/services/controller.py` - Core elevator orchestration
- `app/services/simulator.py` - Movement simulation
- `app/domain/strategies.py` - Scheduling algorithms
- `app/db_client.py` - Database service HTTP client
- `config.yaml` - System configuration

**Dependencies:**
- DB Service (HTTP client via httpx)

### Database Service (FastAPI)
**Location:** `db-service/`
**Port:** 8001

- Data persistence layer
- CRUD operations for elevators, requests, history
- Direct PostgreSQL access
- REST API for backend

**Key Files:**
- `app/api/routes.py` - REST endpoints
- `app/models/database.py` - SQLAlchemy ORM models
- `app/models/schemas.py` - Pydantic schemas
- `app/database.py` - Database connection

**Dependencies:**
- PostgreSQL (SQLAlchemy + asyncpg)

### PostgreSQL
**Port:** 5432

- Persistent data storage
- Tables: elevators, requests, elevator_history, maintenance_logs

## Data Flow

### External Request Flow
```
User clicks floor button
    ↓
Frontend → POST /api/request/external → Backend
    ↓
Backend: Assign elevator using strategy
    ↓
Backend → POST /api/requests → DB Service
    ↓
DB Service → INSERT → PostgreSQL
    ↓
Backend → WebSocket broadcast → Frontend
    ↓
UI updates in real-time
```

### Elevator Movement Flow
```
Simulator tick (every 800ms)
    ↓
Backend: Move elevator one floor
    ↓
Backend → POST /api/history → DB Service
    ↓
DB Service → INSERT → PostgreSQL
    ↓
Backend → WebSocket broadcast → Frontend
    ↓
UI animates elevator movement
```

## Configuration

### Environment Variables

**Backend:**
- `DB_SERVICE_URL` - Database service endpoint (default: http://db-service:8001/api)

**Database Service:**
- `DATABASE_URL` - PostgreSQL connection string

**Frontend:**
- `NEXT_PUBLIC_API_URL` - Backend HTTP endpoint
- `NEXT_PUBLIC_WS_URL` - Backend WebSocket endpoint

### Configuration Files

**Backend:**
- `config.yaml` - Elevator system settings (floors, capacity, strategies)

## Deployment

### Docker Compose
```bash
docker-compose up --build
```

Services start in order:
1. PostgreSQL (with health check)
2. DB Service (waits for PostgreSQL)
3. Backend (waits for DB Service)
4. Frontend (waits for Backend)

### Manual Deployment

1. Start PostgreSQL
2. Start DB Service: `cd db-service && python run.py`
3. Start Backend: `cd backend && python run.py`
4. Start Frontend: `cd frontend && npm run dev`

## API Endpoints

### Backend (Port 8000)
- `GET /` - Health check
- `GET /api/status` - System status
- `POST /api/request/external` - Call elevator
- `POST /api/request/internal` - Select floor
- `POST /api/emergency` - Trigger emergency
- `WS /ws` - WebSocket connection
- `GET /api/analytics/*` - Analytics endpoints

### Database Service (Port 8001)
- `GET /` - Health check
- `POST /api/elevators` - Upsert elevator
- `GET /api/elevators` - Get all elevators
- `POST /api/requests` - Create request
- `PUT /api/requests/{id}` - Update request
- `GET /api/requests/pending` - Get pending requests
- `POST /api/history` - Log history
- `GET /api/history/{elevator_id}` - Get history
- `POST /api/maintenance/start` - Start maintenance
- `POST /api/maintenance/end/{elevator_id}` - End maintenance

## Technology Stack

| Service | Framework | Language | Database Driver |
|---------|-----------|----------|-----------------|
| Frontend | Next.js 16 | TypeScript | - |
| Backend | FastAPI | Python 3.13 | httpx |
| DB Service | FastAPI | Python 3.13 | asyncpg + SQLAlchemy |
| Database | PostgreSQL 16 | SQL | - |

## Design Principles

1. **Separation of Concerns**: Each service has a single responsibility
2. **Loose Coupling**: Services communicate via HTTP/WebSocket
3. **Stateless Backend**: Business logic doesn't manage database connections
4. **Real-time Updates**: WebSocket for instant UI synchronization
5. **Configuration-Driven**: System behavior controlled via config.yaml
