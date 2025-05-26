import os
import time
import json
import re
import logging
from pathlib import Path
from pymilvus import Collection, utility, connections, DataType, FieldSchema, CollectionSchema
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from typing import Dict, List, Tuple, Any, Optional

from config import (
    DOCS_FOLDER, ALLOWED_EXTENSIONS, MILVUS_COLLECTION_NAME, VECTOR_DIMENSION,
    CHUNK_SIZE, CHUNK_OVERLAP, SYNC_STATE_FILE,
    MILVUS_HOST, MILVUS_PORT, EMBEDDING_MODEL,
    DEFAULT_DEPARTMENT_TAG, DEFAULT_PROJECT_TAG, DEFAULT_HIERARCHY_LEVEL, DEFAULT_ROLE_TAG,
    KNOWN_DEPARTMENT_TAGS, ROLE_SPECIFIC_FOLDER_TAGS, HIERARCHY_LEVELS_CONFIG
)
# Import RAGService after config and basic utils to avoid circular dependencies if any
# from rag_processor import RAGService # No, RAGService needs SentenceTransformerEmbeddings, get it directly

from langchain_community.embeddings import SentenceTransformerEmbeddings
# from langchain_huggingface import SentenceTransformerEmbeddings

logger = logging.getLogger("DocumentUpdater")


def get_milvus_connection_args() -> Dict[str, Any]:
    return {"host": MILVUS_HOST, "port": MILVUS_PORT}


def connect_to_milvus():
    if not connections.has_connection("default"):
        logger.info(f"Updater: Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT}.")
        connections.connect(alias="default", **get_milvus_connection_args())


def parse_hierarchy_from_folder_name(folder_name_segment: str) -> Optional[int]:
    """Parses hierarchy level if folder name segment matches HIERARCHY_LEVELS_CONFIG patterns."""
    if not folder_name_segment: return None
    segment_upper = folder_name_segment.upper()
    for key, level in HIERARCHY_LEVELS_CONFIG.items():
        # Match if key AND level are in the segment, e.g., "MANAGER_1" in "CONFIDENTIAL_MANAGER_1_DOCS"
        if key.upper() in segment_upper and f"_{level}_" in segment_upper:
            return level
        # Simpler match: if just "MANAGER" is found, return manager's level
        if key.upper() in segment_upper and f"_{level}_" not in segment_upper and not any(
                str(l) in segment_upper for l in HIERARCHY_LEVELS_CONFIG.values()):
            # Avoids matching "STAFF" in "STAFF_0_TEAM_1" and returning 1 if "TEAM_1" is not a hierarchy key
            # This part is heuristic, might need refinement based on exact folder naming conventions
            pass  # Let a more specific match (with _level_) take precedence.
    return None


def extract_metadata_from_path(relative_path: str) -> Dict[str, Any]:
    """
    Extracts metadata from a relative file path based on configured conventions.
    Path segments are processed to identify department, project, role, and hierarchy.
    """
    path_obj = Path(relative_path)
    parts = list(path_obj.parts[:-1])  # Directory parts only

    metadata = {
        "department_tag": DEFAULT_DEPARTMENT_TAG,
        "project_tag": DEFAULT_PROJECT_TAG,
        "hierarchy_level_required": DEFAULT_HIERARCHY_LEVEL,
        "role_tag_required": DEFAULT_ROLE_TAG,
    }

    # Process parts to find known metadata types
    # A part could be a department, project, role folder, or hierarchy indicator.
    # Order of detection can matter.

    # Simple approach: iterate and assign first found, then refine
    # This is heuristic and depends on naming conventions not overlapping too much.
    # E.g. a project name shouldn't be "lead_docs" if that's a role folder.

    # Pass 1: Identify definite types (department, role, hierarchy)
    # Convert KNOWN_DEPARTMENT_TAGS and ROLE_SPECIFIC_FOLDER_TAGS keys to lowercase for case-insensitive matching
    known_dept_tags_lower = [tag.lower() for tag in KNOWN_DEPARTMENT_TAGS]
    role_folder_tags_lower = {key.lower(): value for key, value in ROLE_SPECIFIC_FOLDER_TAGS.items()}

    project_candidates = []

    for part in parts:
        part_lower = part.lower()
        # Check for Department
        if metadata["department_tag"] == DEFAULT_DEPARTMENT_TAG and part_lower in known_dept_tags_lower:
            original_dept_tag_index = known_dept_tags_lower.index(part_lower)
            metadata["department_tag"] = KNOWN_DEPARTMENT_TAGS[original_dept_tag_index]
            continue  # Part consumed as department

        # Check for Role Folder
        if metadata["role_tag_required"] == DEFAULT_ROLE_TAG and part_lower in role_folder_tags_lower:
            metadata["role_tag_required"] = role_folder_tags_lower[part_lower]
            continue  # Part consumed as role

        # Check for Hierarchy Level
        parsed_hierarchy = parse_hierarchy_from_folder_name(part)
        if parsed_hierarchy is not None:
            # Potentially update if a more restrictive level is found deeper in path, or take first.
            # For now, take the first one found that is not default.
            if metadata["hierarchy_level_required"] == DEFAULT_HIERARCHY_LEVEL or parsed_hierarchy > metadata[
                "hierarchy_level_required"]:
                metadata["hierarchy_level_required"] = parsed_hierarchy
            # Don't 'continue' yet, as a folder like "MANAGER_1_PROJECT_ALPHA_DOCS" might also indicate project.

        # If not a clear type, add to project candidates (if not too generic like "docs", "files")
        if part_lower not in ["docs", "files", "general", "confidential", "private", "shared"] and len(part) > 2:
            if not (
                    part_lower in known_dept_tags_lower or part_lower in role_folder_tags_lower or parsed_hierarchy is not None):
                project_candidates.append(part)

    # Assign Project Tag from candidates if not already set by a more complex logic
    # Heuristic: if only one candidate, or the most "project-like" one.
    # For now, if department is set and there's a candidate, it's likely a project.
    # If department is NOT set, the first significant candidate is likely the project.
    if project_candidates:
        if metadata["project_tag"] == DEFAULT_PROJECT_TAG:
            # Take the first "significant" part that wasn't classified as dept/role/hierarchy
            # This is highly dependent on folder structure discipline.
            # If `DOCS_FOLDER/PROJECT_X/file.pdf`, PROJECT_X is candidate.
            # If `DOCS_FOLDER/HR/PROJECT_Y/file.pdf`, PROJECT_Y is candidate after HR is parsed.
            metadata["project_tag"] = project_candidates[0]  # Simplistic: take first candidate

    # Ensure department is not also the project if structure is ambiguous
    if metadata["department_tag"] != DEFAULT_DEPARTMENT_TAG and metadata["department_tag"] == metadata["project_tag"]:
        metadata["project_tag"] = DEFAULT_PROJECT_TAG  # Avoid department being same as project

    # logger.debug(f"Extracted metadata for '{relative_path}': {metadata} from parts: {parts}")
    return metadata


def get_document_loader(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".txt":
            return TextLoader(file_path, encoding="utf-8")
        elif ext == ".pdf":
            return PyPDFLoader(file_path)
        elif ext == ".md":
            return UnstructuredMarkdownLoader(file_path)
        else:
            logger.warning(f"No loader for extension '{ext}' in '{file_path}'. Skipping.")
            return None
    except Exception as e:
        logger.error(f"Error initializing loader for {file_path}: {e}", exc_info=True)
        return None


def load_and_split_document(full_file_path: str, relative_path: str) -> List[Dict[str, Any]]:
    loader = get_document_loader(full_file_path)
    if not loader: return []
    try:
        documents = loader.load()
    except Exception as e:
        logger.error(f"Error loading document '{full_file_path}': {e}", exc_info=True)
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        length_function=len, is_separator_regex=False,
    )
    split_docs_lc = text_splitter.split_documents(documents)
    path_metadata = extract_metadata_from_path(relative_path)

    processed_chunks = []
    for i, doc_chunk_lc in enumerate(split_docs_lc):
        chunk_metadata = {"source": relative_path, "chunk_index": i, **path_metadata}
        # Add loader metadata if any, ensuring simple types
        if hasattr(doc_chunk_lc, 'metadata') and isinstance(doc_chunk_lc.metadata, dict):
            for key, value in doc_chunk_lc.metadata.items():
                if isinstance(value, (str, int, float, bool)) and key not in chunk_metadata:
                    chunk_metadata[key] = value

        page_content = doc_chunk_lc.page_content if isinstance(doc_chunk_lc.page_content, str) else str(
            doc_chunk_lc.page_content)
        processed_chunks.append({"page_content": page_content, "metadata": chunk_metadata})

    logger.info(f"Loaded & split '{full_file_path}' ({len(processed_chunks)} chunks). Path metadata: {path_metadata}")
    return processed_chunks


def create_milvus_collection_if_not_exists(collection_name: str, vector_dim: int):
    connect_to_milvus()
    if not utility.has_collection(collection_name):
        logger.info(f"Collection '{collection_name}' not found. Creating with new schema.")
        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65_535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="chunk_index", dtype=DataType.INT32),
            FieldSchema(name="department_tag", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="project_tag", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="hierarchy_level_required", dtype=DataType.INT32),  # INT32 more common than INT8
            FieldSchema(name="role_tag_required", dtype=DataType.VARCHAR, max_length=256),
        ]
        schema = CollectionSchema(fields=fields, description="KB Collection with advanced RBAC metadata")
        collection = Collection(collection_name, schema=schema, using='default')
        logger.info(f"Collection '{collection_name}' created.")
        index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        collection.create_index(field_name="vector", index_params=index_params)
        logger.info(f"Vector index created for '{collection_name}'.")
        # Scalar field indexing can be added here if needed for performance on very large datasets
        # collection.create_index(field_name="department_tag", index_name="idx_dept")
        # collection.create_index(field_name="project_tag", index_name="idx_proj")
        # collection.create_index(field_name="hierarchy_level_required", index_name="idx_hier")
        # collection.create_index(field_name="role_tag_required", index_name="idx_role")
    else:
        logger.info(f"Collection '{collection_name}' already exists.")
    collection = Collection(collection_name, using='default')
    logger.info(f"Loading collection '{collection_name}' for document update.")
    collection.load()


def synchronize_documents():
    logger.info("Starting document synchronization...")
    try:
        # 1. Connect & collection setup
        connect_to_milvus()
        create_milvus_collection_if_not_exists(MILVUS_COLLECTION_NAME, VECTOR_DIMENSION)

        # 2. Prepare embeddings and Milvus clients
        embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
        vector_store_lc = Milvus(
            embedding_function=embeddings,
            collection_name=MILVUS_COLLECTION_NAME,
            connection_args=get_milvus_connection_args(),
            auto_id=True,
            vector_field="vector"
        )
        milvus_collection_direct = Collection(MILVUS_COLLECTION_NAME, using='default')
        milvus_collection_direct.load()
        logger.info(f"Ensuring collection '{MILVUS_COLLECTION_NAME}' is loaded before sync.")

        # --- NEW: auto‐reset sync state if Milvus is empty ---
        try:
            num_entities = milvus_collection_direct.num_entities
        except Exception:
            num_entities = 0

        if num_entities == 0 and SYNC_STATE_FILE.exists():
            logger.info("Milvus empty but sync state present—resetting sync state to force full re-import.")
            try:
                SYNC_STATE_FILE.unlink()
            except Exception as e:
                logger.error(f"Failed to delete stale sync state file: {e}", exc_info=True)
        # -----------------------------------------------------

        # 3. Scan docs folder and load last sync state
        current_docs_state = scan_docs_folder()
        last_sync_state = load_sync_state()

        # 4. Handle deletions in Milvus
        process_deletions(last_sync_state, current_docs_state, milvus_collection_direct)

        # 5. Find and process new or updated files
        new_or_updated_files = find_new_or_updated_files(last_sync_state, current_docs_state)
        if new_or_updated_files:
            process_additions_or_updates(
                files_to_process_paths=new_or_updated_files,
                vector_store_lc=vector_store_lc,
                milvus_collection_direct=milvus_collection_direct
            )
        else:
            logger.info("No new or updated documents to process.")

        # 6. Save the fresh sync state
        save_sync_state(current_docs_state)
        logger.info("✅ Document synchronization completed successfully.")
    except Exception as e:
        logger.error(f"❌ Document synchronization failed: {e}", exc_info=True)


def scan_docs_folder() -> Dict[str, float]:
    logger.info(f"Scanning documents folder: '{DOCS_FOLDER}'")
    current_state = {}
    for root, _, files in os.walk(DOCS_FOLDER):
        for f_name in files:
            if os.path.splitext(f_name)[1].lower() in ALLOWED_EXTENSIONS:
                full_path = Path(root) / f_name
                relative_path = full_path.relative_to(DOCS_FOLDER).as_posix()  # Use POSIX for consistency
                try:
                    current_state[relative_path] = full_path.stat().st_mtime
                except FileNotFoundError:
                    logger.warning(f"File not found during scan (possibly deleted mid-scan): {full_path}")
                    continue
    logger.info(f"Found {len(current_state)} documents in '{DOCS_FOLDER}'.")
    return current_state


def load_sync_state() -> Dict[str, float]:
    if not SYNC_STATE_FILE.exists():
        logger.info(f"Sync state file '{SYNC_STATE_FILE}' not found. Assuming clean sync.")
        return {}
    try:
        with open(SYNC_STATE_FILE, 'r') as f:
            state = json.load(f)
        logger.info(f"Loaded sync state from '{SYNC_STATE_FILE}' ({len(state)} entries).")
        return state
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Could not load/parse sync state file '{SYNC_STATE_FILE}': {e}. Assuming clean sync.",
                       exc_info=True)
        return {}


def save_sync_state(state: Dict[str, float]):
    try:
        with open(SYNC_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
        logger.info(f"Saved current sync state to '{SYNC_STATE_FILE}'.")
    except IOError as e:
        logger.error(f"Failed to save sync state to '{SYNC_STATE_FILE}': {e}", exc_info=True)


def process_deletions(old_state: Dict[str, float], new_state: Dict[str, float], collection: Collection):
    deleted_files_paths = set(old_state.keys()) - set(new_state.keys())
    if not deleted_files_paths:
        logger.info("No documents to delete from Milvus.")
        return

    logger.info(f"Found {len(deleted_files_paths)} documents to delete: {deleted_files_paths}")
    delete_expr_list = [f'"{path}"' for path in deleted_files_paths]
    if not delete_expr_list: return
    delete_expr = f"source IN [{', '.join(delete_expr_list)}]"

    try:
        logger.info(f"Attempting Milvus deletion with expression: {delete_expr}")
        res = collection.delete(delete_expr)
        logger.info(
            f"Milvus deletion result: {res.delete_count} entities deleted for {len(deleted_files_paths)} files.")
        collection.flush()
        logger.info("Milvus collection flushed after deletions.")
    except Exception as e:
        logger.error(f"Error during Milvus deletion for '{delete_expr}': {e}", exc_info=True)


def find_new_or_updated_files(old_state: Dict[str, float], new_state: Dict[str, float]) -> List[str]:
    new_or_updated_paths = [
        rel_path for rel_path, current_mtime in new_state.items()
        if rel_path not in old_state or old_state[rel_path] < current_mtime
    ]
    logger.info(f"Found {len(new_or_updated_paths)} new or updated documents.")
    return new_or_updated_paths


def process_additions_or_updates(
        files_to_process_paths: List[str],
        vector_store_lc: Milvus,
        milvus_collection_direct: Collection
):
    if not files_to_process_paths: return

    all_texts_to_add, all_metadatas_to_add = [], []
    for rel_path in files_to_process_paths:
        full_path = DOCS_FOLDER / rel_path
        logger.info(f"Processing for addition/update: '{full_path}' (rel: '{rel_path}')")
        try:
            # Delete old chunks first for updated files
            delete_expr = f'source == "{rel_path}"'
            del_res = milvus_collection_direct.delete(delete_expr)
            if del_res.delete_count > 0:
                logger.info(f"Deleted {del_res.delete_count} old chunks for updated file '{rel_path}'.")
                milvus_collection_direct.flush()
        except Exception as e:
            logger.error(f"Failed to delete old chunks for '{rel_path}': {e}. Risk of duplicates.", exc_info=True)

        chunks_data = load_and_split_document(str(full_path), rel_path)
        for chunk_item in chunks_data:
            all_texts_to_add.append(chunk_item["page_content"])
            all_metadatas_to_add.append(chunk_item["metadata"])

    if all_texts_to_add:
        try:
            logger.info(f"Adding/updating {len(all_texts_to_add)} text chunks to Milvus '{MILVUS_COLLECTION_NAME}'.")
            vector_store_lc.add_texts(texts=all_texts_to_add, metadatas=all_metadatas_to_add)
            logger.info(f"Successfully added/updated {len(all_texts_to_add)} chunks.")
            milvus_collection_direct.flush()
            logger.info(f"Milvus collection '{MILVUS_COLLECTION_NAME}' flushed after additions/updates.")
        except Exception as e:
            logger.error(f"Failed to add texts to Milvus: {e}", exc_info=True)
    else:
        logger.info("No new text chunks from processed files to add to Milvus.")