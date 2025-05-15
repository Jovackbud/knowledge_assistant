import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Document Configuration ---
DOCS_FOLDER = os.getenv("DOCS_FOLDER", "company_docs")
ALLOWED_EXTENSIONS = [".txt", ".pdf"]
Path(DOCS_FOLDER).mkdir(parents=True, exist_ok=True)

# --- Milvus Configuration ---
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "prod_knowledge_v1")
VECTOR_DIMENSION = 384  # all-MiniLM-L6-v2

# --- Text Processing ---
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "deepseek-r1:1.5b"

# --- Database Paths ---
DB_PARENT_DIR = "database"
Path(DB_PARENT_DIR).mkdir(exist_ok=True)
TICKET_DB_PATH = os.path.join(DB_PARENT_DIR, "tickets.db")
FEEDBACK_DB_PATH = os.path.join(DB_PARENT_DIR, "feedback.db")
AUTH_DB_PATH = os.path.join(DB_PARENT_DIR, "auth_profiles.db")

# --- Ticket System ---
TICKET_TEAMS = ["Helpdesk", "HR", "IT", "Legal", "General"]
TICKET_KEYWORD_MAP = {
    "hr": ["payroll", "leave", "benefits"],
    "it": ["password", "laptop", "network"],
    "helpdesk": ["login", "account", "password"]
}

print(f"✅ Configuration loaded | Docs: {DOCS_FOLDER} | DBs: {DB_PARENT_DIR}")