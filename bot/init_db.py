import logging
import asyncio
from database.db import init_db

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Initialize the database tables."""
    try:
        await init_db()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())