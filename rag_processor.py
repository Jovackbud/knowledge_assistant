import os
import glob
import logging
from typing import List, Dict, Any

# Milvus client imports
from pymilvus import connections, utility, Collection
from pymilvus.exceptions import ConnectionNotExistException, MilvusException

# Langchain imports
from langchain_milvus import Milvus
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_ollama import OllamaLLM as Ollama # Use new package
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

# Local imports
from config import (
    DOCS_FOLDER, ALLOWED_EXTENSIONS,
    MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP,
    EMBEDDING_MODEL, LLM_MODEL
)
# Use the REAL function now from auth_service
from auth_service import fetch_user_access_profile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants for Hierarchy Levels ---
LEVEL_LEAD = 2
LEVEL_STAFF_MEMBER = 1

# --- Milvus Connection (remains the same) ---
def connect_to_milvus() -> bool:
    try:
        if connections.get_connection_addr('default'):
            logger.debug("Milvus connection 'default' already exists.") # Changed to debug
            return True
    except ConnectionNotExistException:
         logger.info(f"Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT} using alias 'default'...")
         try:
             connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT, timeout=10)
             if connections.get_connection_addr('default'):
                 logger.info("Successfully connected to Milvus.")
                 return True
             else:
                 logger.error("Milvus connection attempt made, but 'default' alias still not found.")
                 return False
         except MilvusException as e:
             logger.error(f"Failed to connect to Milvus: {e}")
             return False
         except Exception as e:
             logger.error(f"An unexpected error occurred during Milvus connection: {e}")
             return False
    return False

# --- Metadata Extraction (remains the same from Task 2.1) ---
def extract_metadata_from_path(filepath: str) -> Dict[str, Any]:
    # ... (previous version) ...
    metadata = {"access_category": "restricted"} # Default restrictive access
    try:
        rel_path = os.path.relpath(filepath, DOCS_FOLDER)
        parts = os.path.normpath(rel_path).lower().split(os.sep)
        if len(parts) > 0: parts = parts[:-1]
        logger.debug(f"Parsing path parts for metadata: {parts}")
        if not parts:
             logger.warning(f"File '{os.path.basename(filepath)}' directly in DOCS_FOLDER. Restricted.")
             metadata = {"access_category": "restricted"} # Keep default restricted
        elif len(parts) >= 2 and parts[0] == "management":
            if parts[1] == "board": metadata = {"access_category": "board"}
            elif parts[1] == "executive": metadata = {"access_category": "executive"}
        elif len(parts) == 1:
            if parts[0] == "staff": metadata = {"access_category": "staff"}
            elif parts[0] == "volunteers": metadata = {"access_category": "volunteers"}
            elif parts[0] == "graduateassistants": metadata = {"access_category": "graduate_assistants"}
        elif len(parts) >= 1 and parts[0] not in ["projects", "management", "staff", "volunteers", "graduateassistants"]: # Department
            dept_name = parts[0].upper()
            dept_level = LEVEL_STAFF_MEMBER
            if len(parts) >= 2 and parts[1] == "lead": dept_level = LEVEL_LEAD
            if len(parts) >= 3 and parts[1] == "projects": # Nested Project
                 project_name = parts[2].upper()
                 project_level = LEVEL_STAFF_MEMBER
                 if len(parts) >= 4 and parts[3] == "lead":
                      project_level = LEVEL_LEAD
                      dept_level = LEVEL_LEAD # Assume lead needed in both if project lead specified
                 metadata = {"department": dept_name, "min_dept_level": dept_level, "project": project_name, "min_project_level": project_level}
            else: # Department only
                 metadata = {"department": dept_name, "min_dept_level": dept_level}
        elif len(parts) >= 2 and parts[0] == "projects": # Top Level Project
             project_name = parts[1].upper()
             project_level = LEVEL_STAFF_MEMBER
             if len(parts) >= 3 and parts[2] == "lead": project_level = LEVEL_LEAD
             metadata = {"project": project_name, "min_project_level": project_level}
        metadata["source"] = os.path.basename(filepath)
        logger.debug(f"Extracted metadata for '{filepath}': {metadata}") # Debug level
    except Exception as e:
        logger.error(f"Error extracting metadata from path '{filepath}': {e}", exc_info=True)
        metadata = {"access_category": "restricted", "source": os.path.basename(filepath), "error": "parsing_failed"}
    return metadata


# --- Document Loading (remains the same from Task 2.1) ---
def load_documents() -> List[Document]:
    # ... (previous version using extract_metadata_from_path) ...
    logger.info(f"Loading documents from: {DOCS_FOLDER}")
    docs: List[Document] = []
    if not os.path.exists(DOCS_FOLDER):
        logger.warning(f"Document folder '{DOCS_FOLDER}' not found.")
        return docs
    for ext in ALLOWED_EXTENSIONS:
        for filepath in glob.glob(os.path.join(DOCS_FOLDER, "**", f"*{ext}"), recursive=True):
            if not os.path.isfile(filepath): continue
            metadata = extract_metadata_from_path(filepath)
            logger.debug(f"Attempting to load {os.path.basename(filepath)} with metadata: {metadata}")
            try:
                if ext == ".pdf": loader = PyPDFLoader(filepath)
                elif ext == ".txt": loader = TextLoader(filepath, encoding='utf-8')
                else: continue
                loaded_docs_from_file = loader.load()
                for doc in loaded_docs_from_file:
                    doc.metadata = {**doc.metadata, **metadata}
                docs.extend(loaded_docs_from_file)
            except Exception as e:
                logger.error(f"Error loading file '{filepath}': {e}", exc_info=True)
    logger.info(f"Total documents loaded with metadata: {len(docs)}")
    if docs: logger.debug(f"Sample metadata from first loaded doc: {docs[0].metadata}")
    return docs


# --- Text Splitting & Embeddings (remain the same) ---
text_splitter = RecursiveCharacterTextSplitter(
chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)
# embeddings = SentenceTransformerEmbeddings(...) # Initialized in RAGService

# --- RAG Template (remains the same) ---
rag_template_str = """
You are an internal knowledge assistant for African Institute for Artificial Intelligence (AI4AI).
        Answer the question(s) based ONLY on the following context provided. Do not output your reasoning or expose context information
        If the context is empty, states 'No relevant documents were found or accessible for your role. Kindly open a ticket', or does not contain the answer, state clearly: 'Based on the documents I can access, I cannot answer that question. Kindly open a ticket'
        Do not make up information or use external knowledge.
        Be concise and helpful.

    Context:
    {context}

    Question:
    {question}

    Answer:""" # Keep template from previous version

# --- Helper Function to parse roles (NEW for Phase 2) ---
def _parse_user_roles(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to parse roles from profile for easier use in filter construction."""
    parsed_roles = {
        "departments": {}, # { "HR": LEVEL_LEAD, "IT": LEVEL_STAFF_MEMBER }
        "projects": {}     # { "ALPHA": LEVEL_STAFF_MEMBER, "BETA": LEVEL_LEAD }
    }
    # Safely get roles, default to empty list if key missing or None
    dept_roles = profile.get('roles_in_departments') or []
    proj_roles = profile.get('roles_in_projects') or []

    for role in dept_roles:
        name = role.get("department_name", "").upper()
        level_str = role.get("level", "Staff").lower() # Default to Staff
        level = LEVEL_LEAD if level_str == "lead" else LEVEL_STAFF_MEMBER
        if name:
            # Store the highest level if user has multiple entries for same dept
            parsed_roles["departments"][name] = max(level, parsed_roles["departments"].get(name, 0))

    for role in proj_roles:
        name = role.get("project_name", "").upper()
        level_str = role.get("level", "Member").lower() # Default to Member
        level = LEVEL_LEAD if level_str == "lead" else LEVEL_STAFF_MEMBER
        if name:
            parsed_roles["projects"][name] = max(level, parsed_roles["projects"].get(name, 0))

    return parsed_roles

# --- Dynamic Filter Construction (NEW for Phase 2) ---
def construct_milvus_filter(user_profile: Dict[str, Any]) -> str:
    """
    Constructs the Milvus filter expression string based on user profile attributes.
    """
    if not user_profile:
        logger.warning("Cannot construct filter: user profile is empty.")
        return 'access_category == "___NO_ACCESS___"' # Block all

    # List to hold individual conditions that grant access (will be joined by OR)
    conditions = []

    # 1. General Staff/Public Access
    if user_profile.get("can_access_staff_docs"):
        # Documents tagged specifically as staff, volunteers, or grad assistants
        conditions.append('(access_category == "staff" or access_category == "volunteers" or access_category == "graduate_assistants")')

    # 2. Board Access
    if user_profile.get("is_board_member"):
        conditions.append('(access_category == "board")')

    # 3. Executive Management Access
    if user_profile.get("is_executive_management"):
        conditions.append('(access_category == "executive")')

    # 4. Department & Project Access
    parsed_roles = _parse_user_roles(user_profile)
    user_departments = parsed_roles["departments"] # {"HR": 2, "IT": 1}
    user_projects = parsed_roles["projects"]       # {"ALPHA": 1, "BETA": 2}

    # Department-only access
    dept_conditions = []
    for dept_name, user_level in user_departments.items():
        # User can access docs in their department if doc level <= user level
        # We also need to ensure the doc is NOT project-specific unless user also has project access
        # This condition targets docs that ONLY have department metadata
        dept_conditions.append(f'(department == "{dept_name}" and min_dept_level <= {user_level} and project IS NULL)')
        # Simpler alternative: access if dept matches and level is sufficient. Let project checks handle project docs.
        # dept_conditions.append(f'(department == "{dept_name}" and min_dept_level <= {user_level})')
    if dept_conditions:
        conditions.append(f'({" or ".join(dept_conditions)})')


    # Project-only access (Projects/{ProjectName}/...)
    proj_conditions = []
    for proj_name, user_level in user_projects.items():
        # User can access docs in their project if doc level <= user level
        # This condition targets docs that ONLY have project metadata (not department-specific projects)
        proj_conditions.append(f'(project == "{proj_name}" and min_project_level <= {user_level} and department IS NULL)')
        # Simpler alternative:
        # proj_conditions.append(f'(project == "{proj_name}" and min_project_level <= {user_level})')
    if proj_conditions:
        conditions.append(f'({" or ".join(proj_conditions)})')


    # Combined Department AND Project Access ({DeptName}/Projects/{ProjectName}/...)
    # This requires the user to have *both* the department and project role at sufficient levels.
    combined_conditions = []
    for dept_name, user_dept_level in user_departments.items():
        for proj_name, user_proj_level in user_projects.items():
             # A document with BOTH dept and proj metadata requires the user to satisfy both
             combined_conditions.append(f'(department == "{dept_name}" and min_dept_level <= {user_dept_level} and project == "{proj_name}" and min_project_level <= {user_proj_level})')
    if combined_conditions:
         conditions.append(f'({" or ".join(combined_conditions)})') # User needs to match ONE of these combo rules

    # --- Final Assembly ---
    if not conditions:
        # If user has no roles/permissions granting access
        final_filter = 'access_category == "___NO_ACCESS___"' # Block all
    else:
        # Join all granting conditions with OR
        # A document chunk is retrieved if it satisfies ANY of these conditions
        final_filter = f"({' or '.join(conditions)})"

    logger.info(f"Constructed Milvus filter for {user_profile.get('user_email', 'N/A')}: {final_filter}")
    return final_filter


# --- RAGService Class (UPDATED get_rag_chain) ---
class RAGService:
    def __init__(self, embeddings, vector_store, llm, prompt_template, output_parser):
        # ... (init remains the same) ...
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm
        self.prompt_template = prompt_template
        self.output_parser = output_parser
        logger.info(f"RAGService initialized. Vector store is {'available' if self.vector_store else 'unavailable'}.")

    @classmethod
    def from_config(cls, force_recreate: bool = False):
        # ... (from_config remains the same) ...
        is_connected = connect_to_milvus()
        embeddings = None
        try:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
            logger.info("Embedding model loaded")
        except Exception as e: logger.error(f"Failed to load embedding model: {e}", exc_info=True)
        vector_store = None
        if is_connected and embeddings:
            vector_store = cls._initialize_vector_store(embeddings, force_recreate)
        else: logger.warning("Skipping vector store initialization...")
        llm = None
        try:
            logger.info(f"Initializing LLM: {LLM_MODEL}")
            llm = Ollama(model=LLM_MODEL)
            logger.info("LLM initialized")
        except Exception as e: logger.error(f"Failed to initialize LLM {LLM_MODEL}: {e}", exc_info=True)
        prompt = ChatPromptTemplate.from_template(rag_template_str)
        parser = StrOutputParser()
        return cls(embeddings, vector_store, llm, prompt, parser)

    @staticmethod
    def _initialize_vector_store(embeddings, force_recreate: bool):
        # ... (_initialize_vector_store remains the same using updated load_documents) ...
        collection_exists = False
        try:
            collection_exists = utility.has_collection(MILVUS_COLLECTION_NAME)
            logger.info(f"Collection '{MILVUS_COLLECTION_NAME}' exists: {collection_exists}")
        except Exception as e: logger.error(f"Failed check: {e}", exc_info=True)
        if force_recreate and collection_exists:
            try:
                logger.info(f"Dropping collection '{MILVUS_COLLECTION_NAME}'.")
                utility.drop_collection(MILVUS_COLLECTION_NAME)
                collection_exists = False
            except Exception as e: logger.error(f"Failed drop: {e}.", exc_info=True)
        vector_store_instance = None
        if collection_exists:
            logger.info(f"Loading collection: {MILVUS_COLLECTION_NAME}")
            try:
                vector_store_instance = Milvus(embeddings, MILVUS_COLLECTION_NAME, {"host": MILVUS_HOST, "port": MILVUS_PORT})
                coll = Collection(MILVUS_COLLECTION_NAME)
                if not coll.has_index():
                    logger.warning("Existing collection has no index. Creating.")
                    coll.create_index("vector", {"index_type":"IVF_FLAT","metric_type":"L2","params":{"nlist":128}})
                coll.load()
                logger.info("Loaded existing collection.")
            except Exception as e: logger.error(f"Error loading: {e}", exc_info=True)
        else:
            logger.info(f"Creating collection: {MILVUS_COLLECTION_NAME}")
            docs = load_documents()
            if not docs: logger.warning("No documents."); return None
            chunks = text_splitter.split_documents(docs)
            if not chunks: logger.warning("No chunks."); return None
            logger.info(f"Adding {len(chunks)} chunks.")
            if chunks: logger.debug(f"Sample chunk meta: {chunks[0].metadata}")
            try:
                vector_store_instance = Milvus.from_documents(chunks, embeddings, MILVUS_COLLECTION_NAME, {"host": MILVUS_HOST, "port": MILVUS_PORT})
                logger.info("Collection populated.")
                coll = Collection(MILVUS_COLLECTION_NAME); coll.flush()
                if not coll.has_index():
                    logger.info("Creating index.")
                    coll.create_index("vector", {"index_type":"IVF_FLAT","metric_type":"L2","params":{"nlist":128}})
                coll.load()
                logger.info("New collection created, indexed, loaded.")
            except Exception as e: logger.error(f"Error creating: {e}", exc_info=True)
        return vector_store_instance


    # --- UPDATED get_rag_chain ---
    def get_rag_chain(self, user_email: str):
        """Build and return the RAG chain using dynamic filters."""
        # 1. Check essential components
        if not self.vector_store:
            logger.error(f"RAG Chain Error ({user_email}): Vector store unavailable.")
            return RunnableLambda(lambda _: "Error: Knowledge base vector store is unavailable.")
        if not self.llm:
             logger.error(f"RAG Chain Error ({user_email}): LLM unavailable.")
             return RunnableLambda(lambda _: "Error: Language Model is unavailable.")
        if not self.embeddings:
             logger.error(f"RAG Chain Error ({user_email}): Embeddings unavailable.")
             return RunnableLambda(lambda _: "Error: Embedding model is unavailable.")

        # 2. Fetch REAL user profile
        user_profile = fetch_user_access_profile(user_email) # Use the real function

        # 3. Construct the dynamic filter
        filter_expr = construct_milvus_filter(user_profile) # Call the new function

        # 4. Create the retriever with the dynamic filter
        try:
            retriever = self.vector_store.as_retriever(
                 # Increase k slightly? More complex filters might benefit from more candidates initially
                 search_kwargs={'k': 5, 'expr': filter_expr}
             )
            logger.info(f"Retriever created for {user_email} with k=5.")
            # Optional: Add a quick test invocation of the retriever here for debugging
            # try:
            #     test_docs = retriever.invoke("test")
            #     logger.debug(f"Retriever test invocation returned {len(test_docs)} docs.")
            # except Exception as rt_err:
            #     logger.error(f"Retriever test invocation failed: {rt_err}")

        except Exception as e:
            logger.error(f"Failed to create retriever for {user_email} with filter '{filter_expr}': {e}", exc_info=True)
            return RunnableLambda(lambda _: "Error: Failed to configure document retriever.")

        # 5. Construct the final chain (same structure)
        rag_chain = (
            {"context": retriever | self._format_docs, "question": RunnablePassthrough()}
            | self.prompt_template
            | self.llm
            | self.output_parser
        )
        return rag_chain

    @staticmethod
    def _format_docs(docs: List[Document]) -> str:
        # ... (remains the same) ...
        if not docs: return "No relevant documents were found or accessible for your role."
        # ... (optional logging of context docs) ...
        return "\n\n".join(d.page_content for d in docs)