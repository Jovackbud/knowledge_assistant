import os
import re
import time
import json
import logging
from pathlib import Path
import tempfile
import boto3
from botocore.exceptions import ClientError
from pinecone.exceptions import NotFoundException

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import Pinecone as PineconeVectorStore
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Dict, List, Any, Optional

from .utils import sanitize_tag
from .services import shared_services

from .config import (
    PINECONE_INDEX_NAME, ALLOWED_EXTENSIONS, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP, SYNC_STATE_FILE,
    DEFAULT_DEPARTMENT_TAG, DEFAULT_PROJECT_TAG, DEFAULT_HIERARCHY_LEVEL, DEFAULT_ROLE_TAG,
    KNOWN_DEPARTMENT_TAGS, ROLE_SPECIFIC_FOLDER_TAGS, HIERARCHY_LEVELS_CONFIG
)

logger = logging.getLogger("DocumentUpdater")

_metadata_cache = {}

# Initialize the S3 client. Boto3 will automatically use the credentials and endpoint URL from .env
s3_client = boto3.client("s3")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


def find_metadata_file(start_path: Path) -> Optional[Dict[str, Any]]:
    """
    Looks for a 'metadata.json' file in the current directory or any parent directory.
    This allows for inherited permissions. Caches results to avoid redundant S3 calls.
    """
    global _metadata_cache
    
    # Check cache first
    if start_path in _metadata_cache:
        return _metadata_cache[start_path]

    original_path = start_path
    current_dir = start_path
    while current_dir != current_dir.parent:
        # Check cache for parent directories as well during traversal
        if current_dir in _metadata_cache:
            _metadata_cache[original_path] = _metadata_cache[current_dir]
            return _metadata_cache[current_dir]

        metadata_file_key = str(current_dir / "metadata.json").replace('\\', '/')
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=metadata_file_key)
            metadata_content = response['Body'].read().decode('utf-8')
            found_metadata = json.loads(metadata_content)
            _metadata_cache[original_path] = found_metadata # Cache result
            return found_metadata
        except (ClientError, json.JSONDecodeError):
            current_dir = current_dir.parent
    
    # If not found all the way to the root, cache the negative result
    _metadata_cache[original_path] = None
    return None

def extract_metadata_from_path(relative_path: str) -> Dict[str, Any]:
    """
    Extracts metadata by finding and loading a 'metadata.json' manifest file
    from the document's directory or a parent directory in S3/R2.
    """
    path_obj = Path(relative_path)
    # The starting point for the search is the directory containing the file
    search_dir = path_obj.parent

    # Define the default metadata structure
    metadata = {
        "department_tag": DEFAULT_DEPARTMENT_TAG,
        "project_tag": DEFAULT_PROJECT_TAG,
        "hierarchy_level_required": DEFAULT_HIERARCHY_LEVEL,
        "role_tag_required": DEFAULT_ROLE_TAG,
    }

    # Find the explicit metadata from a manifest file
    manifest_data = find_metadata_file(search_dir)

    if manifest_data:
        # If a manifest is found, update the defaults with its values.
        # This is safer as it only updates keys that are explicitly provided.
        # Use the sanitize function on every tag read from the manifest
        metadata["department_tag"] = sanitize_tag(manifest_data.get("department_tag", metadata["department_tag"]))
        metadata["project_tag"] = sanitize_tag(manifest_data.get("project_tag", metadata["project_tag"]))
        metadata["hierarchy_level_required"] = manifest_data.get("hierarchy_level_required", metadata["hierarchy_level_required"])
        metadata["role_tag_required"] = sanitize_tag(manifest_data.get("role_tag_required", metadata["role_tag_required"]))
        logger.info(f"Loaded and sanitized metadata for '{relative_path}'. Data: {metadata}")
    else:
        logger.warning(f"No 'metadata.json' found in the path for '{relative_path}'. "
                       f"Falling back to default metadata. This may restrict access unexpectedly.")

    return metadata


def get_document_loader(file_path: str, ext: str):
    """Initializes a document loader based on file extension."""
    try:
        if ext == ".txt": return TextLoader(file_path, encoding="utf-8")
        elif ext == ".pdf": return PyPDFLoader(file_path)
        elif ext == ".md": return UnstructuredMarkdownLoader(file_path)
        return None
    except Exception as e:
        logger.error(f"Error initializing loader for {file_path}: {e}", exc_info=True)
        return None

def load_and_split_s3_document(s3_key: str) -> List[Dict[str, Any]]:
    """Downloads a file from S3/R2, loads it, and splits it into processable chunks."""
    ext = os.path.splitext(s3_key)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return []

    with tempfile.NamedTemporaryFile(delete=True, suffix=ext) as tmp_file:
        try:
            s3_client.download_file(S3_BUCKET_NAME, s3_key, tmp_file.name)
        except ClientError as e:
            logger.error(f"Failed to download '{s3_key}' from bucket '{S3_BUCKET_NAME}': {e}")
            return []

        loader = get_document_loader(tmp_file.name, ext)
        if not loader: return []
        
        try:
            documents = loader.load()
        except Exception as e:
            logger.error(f"Error loading document from temp file for S3 key '{s3_key}': {e}", exc_info=True)
            return []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    split_docs = text_splitter.split_documents(documents)
    path_metadata = extract_metadata_from_path(s3_key)

    processed_chunks = []
    for i, doc_chunk in enumerate(split_docs):
        chunk_metadata = {"source": s3_key, "chunk_index": i, **path_metadata}
        processed_chunks.append({"page_content": doc_chunk.page_content, "metadata": chunk_metadata})
    
    logger.info(f"Processed S3 key '{s3_key}': {len(processed_chunks)} chunks created.")
    return processed_chunks

def scan_s3_bucket() -> Dict[str, str]:
    """Scans the S3/R2 bucket and returns a dictionary of object keys and their ETags."""
    logger.info(f"Scanning S3-compatible bucket: '{S3_BUCKET_NAME}'")
    current_state = {}
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=S3_BUCKET_NAME):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key.endswith('/'): continue
                if os.path.splitext(key)[1].lower() in ALLOWED_EXTENSIONS:
                    current_state[key] = obj['ETag'].strip('"')
    except ClientError as e:
        logger.error(f"Failed to scan S3 bucket '{S3_BUCKET_NAME}': {e}")
        return {}
    logger.info(f"Found {len(current_state)} documents in S3 bucket.")
    return current_state

def load_sync_state() -> Dict[str, str]:
    if not SYNC_STATE_FILE.exists(): return {}
    try:
        with open(SYNC_STATE_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, IOError): return {}

def save_sync_state(state: Dict[str, str]):
    try:
        with open(SYNC_STATE_FILE, 'w') as f: json.dump(state, f, indent=4)
        logger.info(f"Saved current S3 sync state to '{SYNC_STATE_FILE}'.")
    except IOError: logger.error("Failed to save sync state file.")

def clear_metadata_cache():
    global _metadata_cache
    _metadata_cache.clear()

def synchronize_documents():
    """
    Synchronizes documents from the S3/R2 bucket to the Pinecone vector store.
    This version includes robust error handling for Pinecone operations.
    """
    clear_metadata_cache()
    if not S3_BUCKET_NAME:
        logger.error("S3_BUCKET_NAME environment variable not set. Aborting document synchronization.")
        return

    logger.info("Starting document synchronization from S3/R2 to Pinecone...")
    try:
        # The embeddings client is now passed in, not created here.
        vector_store = PineconeVectorStore.from_existing_index(index_name=PINECONE_INDEX_NAME, embedding=shared_services.document_embedder)
        logger.info(f"Successfully connected to Pinecone index '{PINECONE_INDEX_NAME}'.")

        current_s3_state = scan_s3_bucket()
        last_sync_state = load_sync_state()

        # Determine changes by comparing the current state of the S3 bucket
        # with the state from the last successful synchronization.
        last_keys = set(last_sync_state.keys())
        current_keys = set(current_s3_state.keys())
        
        deleted_keys = last_keys - current_keys
        new_keys = current_keys - last_keys
        updated_keys = {
            key for key in current_keys.intersection(last_keys)
            if current_s3_state[key] != last_sync_state.get(key)
        }
        
        # --- ROBUST DELETION LOGIC ---
        if deleted_keys:
            logger.info(f"Deleting documents for keys: {deleted_keys}")
            for key in deleted_keys:
                try:
                    # Attempt to delete all vectors associated with the deleted file's source key.
                    vector_store.delete(filter={"source": key})
                except NotFoundException:
                    # This error can occur if the index is empty or the vectors were already
                    # removed. It's safe to log a warning and continue.
                    logger.warning(
                        f"Attempted to delete vectors for key '{key}', but they were not found in the index. "
                        "This is safe to ignore during a first-time sync or if the data is already clean."
                    )
            logger.info(f"Finished processing deletions for {len(deleted_keys)} documents from Pinecone.")

        # --- PROCESS ADDITIONS AND UPDATES ---
        files_to_process = new_keys.union(updated_keys)
        if not files_to_process:
            logger.info("No new or updated documents in S3/R2 to process.")
        else:
            logger.info(f"Processing {len(files_to_process)} new/updated documents from S3/R2...")
            for s3_key in files_to_process:
                # For updated files, first delete existing chunks to avoid orphans.
                # This also uses a resilient try/except block.
                if s3_key in updated_keys:
                    try:
                        vector_store.delete(filter={"source": s3_key})
                        logger.info(f"Deleted old chunks for updated S3 key '{s3_key}'.")
                    except NotFoundException:
                        logger.warning(
                            f"Attempted to delete old chunks for updated key '{s3_key}' but none were found. "
                            "Proceeding with adding new chunks."
                        )

                chunks = load_and_split_s3_document(s3_key)
                if not chunks: continue

                texts_to_add = [c['page_content'] for c in chunks]
                metadatas_to_add = [c['metadata'] for c in chunks]
                ids_to_add = [f"{s3_key}-{i}" for i in range(len(chunks))]

                # Pinecone's add_texts is an "upsert" operation. It will add new vectors
                # or update existing ones if the IDs already exist.
                vector_store.add_texts(texts=texts_to_add, metadatas=metadatas_to_add, ids=ids_to_add)
                logger.info(f"Upserted {len(texts_to_add)} chunks for S3 key '{s3_key}'.")

                # Pause for a moment to respect API rate limits.
                logger.info("Pausing for 8 seconds to respect API rate limits...")
                time.sleep(8)

        # After all operations are complete, save the current state for the next run.
        save_sync_state(current_s3_state)
        logger.info("✅ S3/R2 to Pinecone document synchronization completed successfully.")

    except Exception as e:
        logger.error(f"❌ Document synchronization failed: {e}", exc_info=True)
        raise