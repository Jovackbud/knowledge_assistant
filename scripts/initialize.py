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
