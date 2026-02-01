import uvicorn
from app.core.config import settings


def main():
    """Start the FastAPI backend server."""
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)


if __name__ == "__main__":
    main()
