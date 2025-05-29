import logging
import sys
from pathlib import Path
import os
from dotenv import load_dotenv # Added to load .env

# Configure basic logging to show info messages and above
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Add the 'src' directory to the system path so we can import from it
# Assumes this script is run from the project root directory
project_root = Path(__file__).parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
    logger.info(f"Added {src_dir} to sys.path")


try:
    # Import necessary functions from your src directory
    from src.document_updater import synchronize_documents
    from src.database_utils import init_all_databases, _create_sample_users_if_not_exist
    logger.info("Successfully imported synchronize_documents and database_utils functions.")
except ImportError as e:
    logger.error(f"Failed to import modules. Ensure you are running from the project root, 'src' directory exists, and necessary libraries are installed. Error: {e}")
    sys.exit(1) # Exit the script if imports fail


if __name__ == "__main__":
    print("--- Running Document Synchronization Script ---")
    try:
        # Initialize databases (creates the database directory and .db files if they don't exist)
        # This is important as sample user creation relies on the auth DB
        logger.info("Initializing databases...")
        init_all_databases()
        logger.info("Databases initialized.")

        # Ensure sample users exist in the auth database
        # This populates the auth DB with users needed for testing RBAC filters
        logger.info("Checking/creating sample users...")
        _create_sample_users_if_not_exist()
        logger.info("Sample user creation check completed.")

        # Run the main document synchronization logic
        # This will scan docs, process them, embed, and insert into Milvus
        logger.info("Starting document synchronization...")
        synchronize_documents()
        logger.info("Document synchronization finished.")

        print("--- Document Synchronization Completed ---")

    except Exception as e:
        # Catch any exceptions during the process and log them
        logger.error(f"An error occurred during synchronization: {e}", exc_info=True)
        print(f"\n--- Document Synchronization Failed: {e} ---")
        sys.exit(1) # Exit with an error code