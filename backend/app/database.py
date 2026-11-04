"""
Database connection and session management
"""


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Convert postgresql:// to postgresql+psycopg:// for psycopg3
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
}
if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency that creates a new database session for each request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# MONGODB CONNECTION
# ============================================

try:
    from pymongo import MongoClient
    
    # Sync MongoDB client (for simple operations)
    mongo_client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
    mongo_db = mongo_client[settings.MONGODB_DB]
    
    def get_mongo_db():
        """Get MongoDB database instance"""
        return mongo_db
    
except ImportError:
    print("Warning: pymongo not installed. MongoDB features will not work.")
    
    def get_mongo_db():
        """Dummy function when MongoDB is not available"""
        raise Exception("MongoDB is not configured")