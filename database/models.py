from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# SQLite for prototyping; replace with PostgreSQL in production
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
    wallets = relationship("Wallet", back_populates="user")  # Relationship to Wallet

class Wallet(Base):
    """
    Represents a user's wallet for a specific blockchain.

    Columns:
        id: Auto-incrementing primary key.
        user_id: Foreign key to User.
        chain: 'solana' or 'ton'.
        public_key: Wallet address.
        encrypted_private_key: Encrypted private key for custodial use.
    """
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chain = Column(String, nullable=False)  # 'solana' or 'ton'
    public_key = Column(String, unique=True, nullable=False)
    encrypted_private_key = Column(String, nullable=False)
    user = relationship("User", back_populates="wallets")  # Bidirectional relationship

# Create tables if they don't exist
Base.metadata.create_all(engine)

# Session factory for database interactions
SessionFactory = sessionmaker(bind=engine)
