# document_updater.py
import os
import time
import json
import logging
from pymilvus import Collection
from typing import Dict, List
from config import DOCS_FOLDER, ALLOWED_EXTENSIONS, MILVUS_COLLECTION_NAME
from rag_processor import RAGService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DocumentUpdater")


def synchronize_documents():
    """Main document synchronization workflow"""
    try:
        rag_service = RAGService.from_config()
        collection = Collection(MILVUS_COLLECTION_NAME)
        collection.load()

        current_state = scan_docs_folder()
        last_state = load_sync_state()

        process_deletions(last_state, current_state, collection)
        process_additions(current_state, rag_service.embeddings)

        save_sync_state(current_state)
        logger.info("✅ Document sync completed")
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")


def scan_docs_folder() -> Dict[str, float]:
    """Scan documents folder for current state"""
    return {
        os.path.relpath(os.path.join(root, f), DOCS_FOLDER): os.path.getmtime(os.path.join(root, f))
        for root, _, files in os.walk(DOCS_FOLDER)
        for f in files
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    }


def load_sync_state() -> Dict[str, float]:
    """Load last sync state from file"""
    try:
        with open("sync_state.json", 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_sync_state(state: Dict[str, float]):
    """Save current sync state to file"""
    with open("sync_state.json", 'w') as f:
        json.dump(state, f)


def process_deletions(old_state: Dict, new_state: Dict, collection: Collection):
    """Handle deleted documents"""
    deleted = set(old_state.keys()) - set(new_state.keys())
    if deleted:
        collection.delete(f"source IN {list(deleted)}")
        logger.info(f"Deleted {len(deleted)} documents")


def process_additions(current_state: Dict, embeddings):
    """Handle new/updated documents"""
    # Implementation for document processing
    pass