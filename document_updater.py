import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

# Milvus imports
from pymilvus import connections, utility, Collection
from pymilvus.exceptions import MilvusException

# Langchain/Local imports (reuse processing logic)
from langchain_community.vectorstores import Milvus  # Needed for add_documents
from langchain_community.embeddings import SentenceTransformerEmbeddings

# Import necessary components and config from rag_processor and config
from config import (
    DOCS_FOLDER, ALLOWED_EXTENSIONS,
    MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME,
    EMBEDDING_MODEL  # Need embedding model
)
from rag_processor import (
    connect_to_milvus,  # Reuse connection logic
    load_documents,  # Reuse document loading with metadata extraction
    text_splitter  # Reuse text splitter
)

# Configure logging specifically for the updater
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DocumentUpdater")

# --- Configuration ---
STATE_FILE = "sync_state.json"
# Primary key field name used by Langchain's Milvus implementation (usually 'pk')
# Verify this if necessary by inspecting collection schema or Langchain source
MILVUS_PK_FIELD = "pk"
MILVUS_SOURCE_FIELD = "source"  # Metadata field storing the filename
MILVUS_VECTOR_FIELD = "vector"  # Default vector field


# --- State Management ---
def load_state() -> Dict[str, float]:
    """Loads the last known state (filepath -> mtime) from the state file."""
    if not os.path.exists(STATE_FILE):
        logger.info(f"State file '{STATE_FILE}' not found. Starting fresh.")
        return {}
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            logger.info(f"Loaded state for {len(state)} files from '{STATE_FILE}'.")
            return state
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading state file '{STATE_FILE}': {e}. Starting fresh.", exc_info=True)
        return {}


def save_state(current_state: Dict[str, float]):
    """Saves the current state (filepath -> mtime) to the state file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(current_state, f, indent=4)
        logger.info(f"Saved state for {len(current_state)} files to '{STATE_FILE}'.")
    except IOError as e:
        logger.error(f"Error saving state file '{STATE_FILE}': {e}", exc_info=True)


# --- File System Scan ---
def scan_docs_folder() -> Dict[str, float]:
    """Scans DOCS_FOLDER recursively and returns current files and mtimes."""
    current_files = {}
    logger.info(f"Scanning documents folder: {DOCS_FOLDER}...")
    if not os.path.isdir(DOCS_FOLDER):
        logger.error(f"DOCS_FOLDER '{DOCS_FOLDER}' does not exist or is not a directory.")
        return {}

    for root, _, files in os.walk(DOCS_FOLDER):
        for filename in files:
            # Check if the file extension is allowed
            if any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                filepath = os.path.join(root, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    # Use relative path for state file key to be more portable
                    relative_path = os.path.relpath(filepath, DOCS_FOLDER)
                    current_files[relative_path] = mtime
                except OSError as e:
                    logger.warning(f"Could not get modification time for '{filepath}': {e}")

    logger.info(f"Scan complete. Found {len(current_files)} files with allowed extensions.")
    return current_files


# --- Milvus Operations ---
def delete_docs_from_milvus(filenames: List[str], collection: Collection):
    """Deletes chunks associated with given filenames from Milvus."""
    if not filenames:
        return 0

    deleted_count = 0
    # Escape filenames for the query string if they contain quotes or special chars
    # Simple escaping for double quotes - adjust if other chars are problematic
    safe_filenames = [name.replace('"', '\\"') for name in filenames]

    # Construct 'in' expression for Milvus query
    expr = f'{MILVUS_SOURCE_FIELD} in ["' + '", "'.join(safe_filenames) + '"]'
    logger.info(f"Querying Milvus for PKs to delete with expr: {expr}")

    try:
        # Query Milvus to get the primary keys (PKs) for the chunks to delete
        # Increase limit significantly if many chunks per file expected
        results = collection.query(expr=expr, output_fields=[MILVUS_PK_FIELD], limit=10000)

        pks_to_delete = [item[MILVUS_PK_FIELD] for item in results if MILVUS_PK_FIELD in item]

        if not pks_to_delete:
            logger.warning(
                f"No PKs found in Milvus for deletion query: {expr}. Files might have already been deleted or not indexed correctly.")
            return 0

        logger.info(f"Found {len(pks_to_delete)} PKs to delete for {len(filenames)} files.")

        # Construct delete expression using PKs
        delete_expr = f'{MILVUS_PK_FIELD} in [{",".join(map(str, pks_to_delete))}]'
        delete_result = collection.delete(delete_expr)

        # delete_result might provide info on success/failure or IDs deleted
        # For simplicity, we'll assume success if no exception, and log the count
        logger.info(f"Milvus delete operation executed for expr: {delete_expr}. Result: {delete_result}")
        # The number of PKs found might be a better indicator of deletions
        deleted_count = len(pks_to_delete)

    except MilvusException as e:
        logger.error(f"Milvus error during query/delete operation for files {filenames}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error during Milvus query/delete for files {filenames}: {e}", exc_info=True)

    return deleted_count


def add_docs_to_milvus(filepaths: List[str], vector_store_instance: Milvus, embeddings):
    """Loads, processes, and adds documents from filepaths to Milvus."""
    if not filepaths:
        return 0

    added_chunk_count = 0
    logger.info(f"Processing {len(filepaths)} files for addition/update...")

    # Note: load_documents expects full paths
    full_filepaths = [os.path.join(DOCS_FOLDER, rel_path) for rel_path in filepaths]

    # Reuse the loading and metadata extraction from rag_processor
    # This returns List[Document], where each Document might be a page (for PDF)
    # And already includes metadata like 'source' and access controls
    all_docs = []
    for full_path in full_filepaths:
        # Mimic the loading logic precisely if load_documents isn't directly usable
        # For now, assume load_documents works by processing a list?
        # Let's refine: process one file at a time for clarity in adder
        try:
            logger.debug(f"Loading document: {full_path}")
            # Simplified call assuming load_documents handles single files or adjust
            # We need to modify load_documents or create a variant for single file processing
            # For now, let's call the existing load_documents logic - it needs refactoring
            # Let's assume we refactor load_documents to handle a list of files
            # OR call it repeatedly (less efficient)
            # OR extract its core logic here

            # **Reusing core logic (more self-contained updater):**
            filename = os.path.basename(full_path)
            ext = os.path.splitext(filename)[1].lower()
            metadata = extract_metadata_from_path(full_path)  # From rag_processor

            if ext == ".pdf":
                loader = PyPDFLoader(full_path)
            elif ext == ".txt":
                loader = TextLoader(full_path, encoding='utf-8')
            else:
                continue

            loaded_docs_from_file = loader.load()

            for doc in loaded_docs_from_file:
                doc.metadata = {**doc.metadata, **metadata}
            all_docs.extend(loaded_docs_from_file)
            logger.debug(f"Loaded {len(loaded_docs_from_file)} pages/docs from {filename}")

        except Exception as e:
            logger.error(f"Failed to load/process file {full_path} for addition: {e}", exc_info=True)
            continue  # Skip this file

    if not all_docs:
        logger.warning("No documents successfully loaded for addition.")
        return 0

    # Split loaded documents into chunks
    chunks = text_splitter.split_documents(all_docs)
    if not chunks:
        logger.warning("No chunks generated from loaded documents.")
        return 0

    logger.info(f"Generated {len(chunks)} chunks from {len(filepaths)} files.")
    if chunks: logger.debug(f"Sample chunk metadata for addition: {chunks[0].metadata}")

    # Add chunks to Milvus using the vector_store instance
    try:
        # vector_store_instance needs the embedding function associated
        # We need to instantiate it correctly or pass embeddings to add_documents if possible
        # Let's assume vector_store_instance IS the Langchain Milvus object

        # Pass the embedding function directly if needed by the instance,
        # though often it's configured during instantiation.
        # vector_store_instance.embedding_function = embeddings # If needed

        # The add_documents method typically handles embedding
        result_pks = vector_store_instance.add_documents(chunks)
        added_chunk_count = len(result_pks)
        logger.info(f"Successfully added {added_chunk_count} chunks to Milvus. Result PKs sample: {result_pks[:5]}")

        # TODO: Optionally update state file with added PKs if needed later?

    except MilvusException as e:
        logger.error(f"Milvus error during add_documents: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error during add_documents: {e}", exc_info=True)

    return added_chunk_count


# --- Main Synchronization Logic ---
def synchronize_documents():
    """Performs the main sync process: scan, compare, update Milvus, save state."""
    logger.info("Starting document synchronization process...")

    # 0. Ensure connection to Milvus
    if not connect_to_milvus():
        logger.error("Cannot synchronize: Failed to connect to Milvus.")
        return

    # Get Milvus collection object for delete operations
    try:
        collection = Collection(MILVUS_COLLECTION_NAME)
        collection.load()  # Ensure collection is loaded for queries/deletes
        logger.info(f"Access established to Milvus collection '{MILVUS_COLLECTION_NAME}'.")
    except Exception as e:
        logger.error(f"Cannot synchronize: Failed to get or load Milvus collection '{MILVUS_COLLECTION_NAME}': {e}",
                     exc_info=True)
        return

    # Instantiate embeddings (needed for adding docs)
    try:
        embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
        logger.info("Embedding model loaded for updater.")
    except Exception as e:
        logger.error(f"Cannot synchronize: Failed to load embedding model: {e}", exc_info=True)
        return

    # Instantiate Langchain Milvus vector store object (needed for adding docs)
    # This assumes the collection exists (as it should after initial setup)
    try:
        vector_store_instance = Milvus(
            embedding_function=embeddings,  # Pass embeddings
            collection_name=MILVUS_COLLECTION_NAME,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT}
        )
        logger.info("Langchain Milvus vector store interface initialized.")
    except Exception as e:
        logger.error(f"Cannot synchronize: Failed to initialize Langchain Milvus interface: {e}", exc_info=True)
        return

    # 1. Load last state
    last_state = load_state()

    # 2. Scan current file system state
    current_state = scan_docs_folder()

    # 3. Compare states to find changes
    last_files = set(last_state.keys())
    current_files = set(current_state.keys())

    new_files = list(current_files - last_files)
    deleted_files = list(last_files - current_files)

    potentially_modified_files = list(current_files.intersection(last_files))
    modified_files = []
    for filepath_key in potentially_modified_files:
        # Compare modification times, allow for slight float precision issues
        if abs(current_state[filepath_key] - last_state[filepath_key]) > 1e-6:
            modified_files.append(filepath_key)

    logger.info(
        f"Change detection: Found {len(new_files)} new, {len(deleted_files)} deleted, {len(modified_files)} modified files.")

    # 4. Update Milvus
    files_to_delete = deleted_files + modified_files  # Delete old versions of modified files
    files_to_add = new_files + modified_files  # Add new versions of modified files

    total_deleted = 0
    total_added = 0

    # Perform deletions first
    if files_to_delete:
        logger.info(f"Attempting deletion of data for {len(files_to_delete)} files: {files_to_delete}")
        # Get filenames from relative paths for deletion query
        filenames_to_delete = [os.path.basename(fp) for fp in files_to_delete]
        deleted_count = delete_docs_from_milvus(filenames_to_delete, collection)
        logger.info(f"Deletion process completed. Deleted approx {deleted_count} chunks.")
        total_deleted = deleted_count
    else:
        logger.info("No files marked for deletion.")

    # Perform additions next
    if files_to_add:
        logger.info(f"Attempting addition/update of data for {len(files_to_add)} files: {files_to_add}")
        # Pass relative paths and the vector store instance
        added_count = add_docs_to_milvus(files_to_add, vector_store_instance, embeddings)
        logger.info(f"Addition process completed. Added approx {added_count} chunks.")
        total_added = added_count
    else:
        logger.info("No files marked for addition.")

    # 5. Save the new state (only if updates were successful?)
    # For simplicity now, always save the scanned current state.
    # More robust: update state based on successful adds/deletes.
    save_state(current_state)

    logger.info(f"Synchronization process finished. Deleted: {total_deleted} chunks, Added: {total_added} chunks.")


# --- Entry Point ---
if __name__ == "__main__":
    logger.info("Starting Standalone Document Updater Script")
    start_time = time.time()

    synchronize_documents()

    end_time = time.time()
    logger.info(f"Updater script finished in {end_time - start_time:.2f} seconds.")

    # To run periodically, this script would be invoked by an external scheduler (Task Scheduler, cron)
    # Or wrapped in a loop with time.sleep(SECONDS_IN_DAY) if run continuously (less ideal)