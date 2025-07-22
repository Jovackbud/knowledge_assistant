from dotenv import load_dotenv
load_dotenv()

import sys
import os

# Adjust the Python path to include the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.embeddings import Embeddings

from src.database_utils import init_all_databases, _create_sample_users_if_not_exist
from src.document_updater import synchronize_documents
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InitializationScript")

def run_initialization(embeddings_client: Embeddings):
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
        _create_sample_users_if_not_exist()
        logger.info("Sample user creation step complete.")

        logger.info("Synchronizing documents...")
        synchronize_documents(embeddings_client)
        logger.info("Document synchronization complete.")

        logger.info("All initialization tasks finished successfully.")

    except Exception as e:
        logger.critical(f"A critical error occurred during initialization: {e}", exc_info=True)
        # Re-raise the exception to make it clear the startup failed.
        # This is better for debugging on Render.
        raise RuntimeError("Initialization failed, application cannot start.") from e