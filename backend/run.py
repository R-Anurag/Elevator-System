"""
run.py — starts the FastAPI server via uvicorn.
Settings (host, port) are read from config.yaml.
"""
import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.api.host,
        port=s.api.port,
        reload=True,
        log_level="info",
    )
