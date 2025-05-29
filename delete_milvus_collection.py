# delete_milvus_collection.py
import pymilvus
from pymilvus import utility, connections
import logging
import os
from dotenv import load_dotenv # Needed to load from .env

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Get configuration from environment variables (matching your .env)
# Use defaults if .env or variables are missing, but log a warning.
MILVUS_HOST = os.getenv("MILVUS_HOST") or "127.0.0.1"
MILVUS_PORT = os.getenv("MILVUS_PORT") or "19530"
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME") or "adv_rbac_kb_v1"

if os.getenv("MILVUS_HOST") is None or os.getenv("MILVUS_PORT") is None or os.getenv("MILVUS_COLLECTION_NAME") is None:
    logger.warning(f"Using default Milvus config as .env or variables not found: Host={MILVUS_HOST}, Port={MILVUS_PORT}, Collection={MILVUS_COLLECTION_NAME}")
else:
    logger.info(f"Loaded Milvus config from .env: Host={MILVUS_HOST}, Port={MILVUS_PORT}, Collection={MILVUS_COLLECTION_NAME}")
# --------------------

def delete_collection(collection_name: str):
    """Connects to Milvus and drops the specified collection."""
    try:
        logger.info(f"Attempting to connect to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
        # Connect to Milvus using the 'default' alias
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
        logger.info("Milvus connection successful.")

        # Check if the collection exists before attempting to drop
        if utility.has_collection(collection_name, using='default'):
            logger.warning(f"Collection '{collection_name}' found. Dropping...")
            utility.drop_collection(collection_name, using='default')
            logger.info(f"Collection '{collection_name}' dropped successfully.")
        else:
            logger.info(f"Collection '{collection_name}' does not exist in Milvus. No need to drop.")

    except Exception as e:
        logger.error(f"An error occurred during Milvus collection deletion: {e}", exc_info=True)
        print(f"\nError deleting Milvus collection: {e}")
    finally:
        # Disconnect when done
        if connections.has_connection("default"):
             connections.disconnect(alias="default")
             logger.info("Milvus disconnected.")


# Execute the deletion function when the script is run
if __name__ == "__main__":
    print(f"--- Running Milvus Collection Deletion Script ---")
    # Call the function to delete the collection specified in config
    delete_collection(MILVUS_COLLECTION_NAME)
    print(f"--- Finished Milvus Collection Deletion Script ---")
    