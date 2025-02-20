from sqlalchemy.orm import Session
from database.models import User, SessionFactory
import logging

logger = logging.getLogger(__name__)

def get_session() -> Session:
    """
    Create a new database session.

    Returns:
        A SQLAlchemy Session object. Caller must close it manually.
    """
    try:
        return SessionFactory()
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise

def get_user(telegram_id: str, session: Session) -> User | None:
    """
    Fetch a user by Telegram ID.

    Args:
        telegram_id: User's Telegram ID.
        session: Active database session.

    Returns:
        User object or None if not found.
    """
    try:
        return session.query(User).filter_by(telegram_id=telegram_id).first()
    except Exception as e:
        logger.error(f"Error fetching user {telegram_id}: {str(e)}")
        raise

def add_user(telegram_id: str, session: Session) -> User:
    """
    Add a new user to the database.

    Args:
        telegram_id: User's Telegram ID.
        session: Active database session.

    Returns:
        Newly created User object.

    Raises:
        Exception: If commit fails (e.g., duplicate telegram_id).
    """
    try:
        user = User(telegram_id=telegram_id)
        session.add(user)
        session.commit()
        logger.info(f"Added user {telegram_id}")
        return user
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to add user {telegram_id}: {str(e)}")
        raise
