from dotenv import load_dotenv
load_dotenv()

import sys
import os

# Adjust the Python path to include the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database_utils import init_all_databases, _create_sample_users_if_not_exist
from src.document_updater import synchronize_documents
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InitializationScript")

if __name__ == '__main__':
    logger.info("Starting database and document initialization...")
    try:
        logger.info("Initializing all databases...")
        init_all_databases()
        logger.info("Database initialization complete.")

        logger.info("Creating sample users if they don't exist...")
        _create_sample_users_if_not_exist()
        logger.info("Sample user creation step complete.")

        logger.info("Synchronizing documents...")
        synchronize_documents()
        logger.info("Document synchronization complete.")

        logger.info("All initialization tasks finished successfully.")

    except Exception as e:
        logger.critical(f"A critical error occurred during initialization: {e}", exc_info=True)
        # In a production environment, you might want to exit with a non-zero code
        # to signal a failed deployment, but for Render's boot process,
        # letting it continue might be safer so the server can at least start.
        # If the web server can run without this data, we can let it proceed.
        # If not, you could re-introduce a sys.exit(1) here.
        # For now, we log it as critical and allow the server to attempt a start.
        logger.warning("Initialization failed. The application will continue to start, but may be in a degraded state.")