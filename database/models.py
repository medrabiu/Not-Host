from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite or psql
DATABASE_URL = "sqlite:///bot.db"
engine = create_engine(DATABASE_URL, echo=False)  # Set echo=True for debugging
Base = declarative_base()

class User(Base):
    """
    Represents a bot user with basic info and wallet status.

    Columns:
        id: Auto-incrementing primary key.
        telegram_id: Unique Telegram ID.
        has_wallet: Tracks if wallets are created.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    has_wallet = Column(Boolean, default=False)

# Create tables if they don't exist
Base.metadata.create_all(engine)

# Session factory for database interactions
SessionFactory = sessionmaker(bind=engine)
