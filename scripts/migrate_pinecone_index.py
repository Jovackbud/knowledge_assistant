"""
Pinecone Index Migration Script
================================
Runs automatically during deploy (before initialize.py).

What it does:
  1. Checks the current Pinecone index dimension against the embedding model dimension.
  2. If they match → exits cleanly (no-op, safe to run on every deploy).
  3. If they don't match → deletes the old index, creates a new one at the
     correct dimension, and clears the DB sync state so the next sync
     re-indexes all documents from scratch.

This is idempotent: running it multiple times is always safe.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PineconeMigration")

# --- Read required env vars before importing anything else ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "knowledge-assistant-v2")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "models/gemini-embedding-001")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Cloud/region used when creating a fresh index (no existing one to read from)
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

if not PINECONE_API_KEY:
    raise RuntimeError("FATAL: PINECONE_API_KEY is not set.")
if not GOOGLE_API_KEY:
    raise RuntimeError("FATAL: GOOGLE_API_KEY is not set.")


def get_embedding_dimension(model_name: str) -> int:
    """
    Probes the embedding model with a single test string to get the
    actual output dimension. This is the ground truth — no hardcoding.
    """
    logger.info(f"Probing embedding dimension for model '{model_name}'...")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    embedder = GoogleGenerativeAIEmbeddings(model=model_name, task_type="RETRIEVAL_QUERY")
    vector = embedder.embed_query("dimension probe")
    dim = len(vector)
    logger.info(f"Model '{model_name}' produces {dim}-dimensional vectors.")
    return dim


def get_existing_index_info(pc, index_name: str):
    """
    Returns (dimension, cloud, region) for an existing Pinecone index,
    or (None, None, None) if the index doesn't exist.
    """
    try:
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing_indexes:
            logger.info(f"Index '{index_name}' does not exist yet.")
            return None, None, None
        desc = pc.describe_index(index_name)
        dim = desc.dimension
        # Safely extract cloud/region from spec (object or dict shape)
        spec = desc.spec
        if hasattr(spec, "serverless"):
            cloud = spec.serverless.cloud
            region = spec.serverless.region
        elif isinstance(spec, dict) and "serverless" in spec:
            cloud = spec["serverless"]["cloud"]
            region = spec["serverless"]["region"]
        else:
            cloud, region = PINECONE_CLOUD, PINECONE_REGION
        logger.info(f"Existing index '{index_name}': dim={dim}, cloud={cloud}, region={region}.")
        return dim, cloud, region
    except Exception as e:
        logger.error(f"Error checking existing index '{index_name}': {e}", exc_info=True)
        raise


def delete_index_with_wait(pc, index_name: str):
    """Deletes a Pinecone index and waits until it's fully gone."""
    logger.warning(f"Deleting Pinecone index '{index_name}'...")
    pc.delete_index(index_name)
    # Poll until deletion is confirmed (Pinecone deletions are async)
    for attempt in range(30):
        existing = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing:
            logger.info(f"Index '{index_name}' confirmed deleted.")
            return
        logger.info(f"Waiting for index deletion... attempt {attempt + 1}/30")
        time.sleep(5)
    raise RuntimeError(f"Timed out waiting for index '{index_name}' to be deleted.")


def create_index_with_wait(pc, index_name: str, dimension: int, cloud: str, region: str):
    """Creates a new Pinecone serverless index and waits until it's ready."""
    from pinecone import ServerlessSpec
    logger.info(f"Creating new Pinecone index '{index_name}' (dim={dimension}, cloud={cloud}, region={region})...")
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric="cosine",
        spec=ServerlessSpec(cloud=cloud, region=region),
    )
    # Poll until the index is ready to accept vectors
    for attempt in range(60):
        desc = pc.describe_index(index_name)
        # Handle both dict-style and object-style status depending on SDK version
        status = desc.status
        is_ready = status.get("ready", False) if isinstance(status, dict) else getattr(status, "ready", False)
        if is_ready:
            logger.info(f"Index '{index_name}' is ready.")
            return
        logger.info(f"Waiting for index to become ready... attempt {attempt + 1}/60")
        time.sleep(5)
    raise RuntimeError(f"Timed out waiting for index '{index_name}' to become ready.")


def clear_sync_state():
    """
    Clears the SyncState table in the DB so the next document sync
    treats all S3 files as new and re-indexes them into the fresh index.
    """
    logger.info("Clearing sync state from database to force full re-index...")
    from src.database_utils import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("DELETE FROM SyncState"))
    logger.info("✅ Sync state cleared. Next sync will re-index all documents.")


def run_migration():
    logger.info("=== Pinecone Index Migration Check ===")

    # Step 1: Get the dimension the current embedding model actually produces
    required_dim = get_embedding_dimension(EMBEDDING_MODEL_NAME)

    # Step 2: Check what the existing index has (dimension + cloud/region)
    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing_dim, existing_cloud, existing_region = get_existing_index_info(pc, PINECONE_INDEX_NAME)

    # Step 3: Decide action
    if existing_dim is None:
        # Index doesn't exist at all — create it fresh using env var defaults
        logger.info(f"No existing index found. Creating '{PINECONE_INDEX_NAME}' at dim={required_dim}.")
        create_index_with_wait(pc, PINECONE_INDEX_NAME, required_dim, PINECONE_CLOUD, PINECONE_REGION)
        logger.info("✅ Migration complete: fresh index created.")
        return

    if existing_dim == required_dim:
        # Dimensions match — nothing to do
        logger.info(
            f"✅ No migration needed. Index '{PINECONE_INDEX_NAME}' dimension "
            f"({existing_dim}) matches model dimension ({required_dim})."
        )
        return

    # Dimensions mismatch — must rebuild
    logger.warning(
        f"⚠️  Dimension mismatch detected: index={existing_dim}, model={required_dim}. "
        f"Rebuilding index '{PINECONE_INDEX_NAME}'..."
    )

    # Preserve the original cloud/region so we recreate in the same location
    target_cloud = existing_cloud or PINECONE_CLOUD
    target_region = existing_region or PINECONE_REGION

    # Step 4: Delete old index
    delete_index_with_wait(pc, PINECONE_INDEX_NAME)

    # Step 5: Create new index at correct dimension in the same cloud/region
    create_index_with_wait(pc, PINECONE_INDEX_NAME, required_dim, target_cloud, target_region)

    # Step 6: Clear sync state so all docs get re-indexed
    clear_sync_state()

    logger.info(
        f"✅ Migration complete. Index '{PINECONE_INDEX_NAME}' rebuilt at dim={required_dim} "
        f"(cloud={target_cloud}, region={target_region}). "
        "All documents will be re-indexed on next sync."
    )


if __name__ == "__main__":
    run_migration()
