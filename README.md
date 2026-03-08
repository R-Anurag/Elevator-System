# Elevator System

A real-time elevator management system with microservices architecture: FastAPI backend, database service, and Next.js frontend.

## Quick Start

```bash
# 1. Create database password secret
echo "YOUR_STRONG_PASSWORD" > secrets/db_password.txt

# 2. Build and run
docker-compose up --build -d

# 3. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## Architecture

```
Frontend (Next.js) → Backend (FastAPI) → DB Service (FastAPI) → PostgreSQL
     :3000               :8000                :8001              :5432
```

## Features

- ✅ Real-time elevator monitoring via WebSocket
- ✅ Multi-elevator management with intelligent scheduling
- ✅ Interactive UI with live animations
- ✅ PostgreSQL persistence with Docker secrets
- ✅ Microservices architecture
- ✅ Production-ready with resource limits
- ✅ Request history and analytics
- ✅ Maintenance and emergency modes

## Configuration

Edit `backend/config.yaml` to configure:
- Number of floors and elevators
- Elevator capacity
- Scheduling strategy (nearest, direction_based, idle_preference)
- Simulation speed
- Emergency settings

## Technology Stack

- **Frontend**: Next.js 16, React 19, TypeScript
- **Backend**: FastAPI, Python 3.13, WebSockets
- **Database Service**: FastAPI, SQLAlchemy, asyncpg
- **Database**: PostgreSQL 16
- **Deployment**: Docker, Docker Compose

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system architecture
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide

## License

MIT
