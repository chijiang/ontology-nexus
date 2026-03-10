import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(BASE_DIR, "work_ticket.db")

# For Async gRPC Server
ASYNC_DB_URL = f"sqlite+aiosqlite:///{DB_FILE_PATH}"
async_engine = create_async_engine(ASYNC_DB_URL, echo=False)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

# For Sync Data Import Script
SYNC_DB_URL = f"sqlite:///{DB_FILE_PATH}"
sync_engine = create_engine(SYNC_DB_URL, echo=False)
sync_session_maker = sessionmaker(sync_engine)
