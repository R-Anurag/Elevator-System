# Elevator System

A real-time elevator management system with FastAPI backend and Next.js frontend.

## Project Structure

- `backend/` - FastAPI server with WebSocket support
- `frontend/` - Next.js React application

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

The API will run on `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will run on `http://localhost:3000`

## Configuration

### Backend
- Copy `config.yaml` and adjust settings as needed
- Database is created automatically on first run

### Frontend
- Create `.env.local` with:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
  ```

## Features

- Real-time elevator monitoring via WebSocket
- Multi-elevator management
- Request queue handling
- Interactive UI with live updates
