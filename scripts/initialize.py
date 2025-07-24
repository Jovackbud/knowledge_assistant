from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InitializationScript")

from src.database_utils import init_all_databases, create_sample_users_if_not_exist
from src.document_updater import synchronize_documents

def run_initialization():
    """
    Runs the full suite of initialization tasks: databases, sample users,
    and the initial document synchronization.
    """
    logger.info("Starting database and document initialization...")
    try:
        logger.info("Initializing all databases...")
        init_all_databases()
        logger.info("Database initialization complete.")

        logger.info("Creating sample users if they don't exist...")
        create_sample_users_if_not_exist()
        logger.info("Sample user creation step complete.")

        # logger.info("Synchronizing documents...")
        # synchronize_documents()
        # logger.info("Document synchronization complete.")

        logger.info("All initialization tasks finished successfully.")

    except Exception as e:
        logger.critical(f"A critical error occurred during initialization: {e}", exc_info=True)
        # Re-raise the exception to make it clear the startup failed.
        # This is better for debugging on Render.
        raise RuntimeError("Initialization failed, application cannot start.") from e
    
if __name__ == "__main__":
        run_initialization()