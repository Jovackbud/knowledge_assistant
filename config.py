import os
from dotenv import load_dotenv
load_dotenv()
# --- Role Configuration (Simplified for ABAC focus) ---
# This will be less about predefined roles and more about attributes
# For now, we'll keep it minimal as user attributes come from UserAccessProfile DB
# ROLES = ["staff", "manager"] # Example, less critical now

# --- Document Configuration ---
DOCS_FOLDER = os.getenv("DOCS_FOLDER", "sample_docs_phase1") # For Phase 1 testing
ALLOWED_EXTENSIONS = [".txt", ".pdf"]

# --- RAG Configuration ---
# Milvus Connection Details
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "knowledge_base_v1")
VECTOR_DIMENSION = 384 # For all-MiniLM-L6-v2

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "all-MiniLM-L6-v2" # SentenceTransformer model
LLM_MODEL = "deepseek-r1:1.5b" # Ollama model (ensure this is the correct tag for the model you pulled)

# --- Database Configuration ---
# Parent directory for databases
DB_PARENT_DIR = "database"
TICKET_DB_PATH = os.path.join(DB_PARENT_DIR, "tickets.db")
FEEDBACK_DB_PATH = os.path.join(DB_PARENT_DIR, "feedback.db")
AUTH_DB_PATH = os.path.join(DB_PARENT_DIR, "auth_profiles.db")

# --- Ticket System Configuration (from PoC, can be adjusted later) ---
TICKET_TEAMS = ["Helpdesk", "HR", "IT", "Legal", "General"] # Manual list for now
TICKET_KEYWORD_MAP = {
    "hr": ["payroll", "leave", "benefits", "hiring", "policy", "pto", "salary", "employee"],
    "it": ["laptop", "password", "software", "printer", "network", "access", "computer", "wifi", "system"],
    "helpdesk": ["account", "order", "website", "login", "purchase", "service", "product issue", "billing", "faq", "contact", "support"],
}


# --- Create necessary directories ---
os.makedirs(DB_PARENT_DIR, exist_ok=True)
if not os.path.exists(DOCS_FOLDER):
    os.makedirs(DOCS_FOLDER)
    print(f"Created sample documents folder: {DOCS_FOLDER}")
    # Create a dummy file for initial testing if DOCS_FOLDER was just created
    with open(os.path.join(DOCS_FOLDER, "staff_doc_example.txt"), "w") as f:
        f.write("This is a sample document for staff. It contains general staff information. Staff benefits include dental care.")
    with open(os.path.join(DOCS_FOLDER, "another_doc_example.txt"), "w") as f:
        f.write("This is another generic document, also for staff in Phase 1.")

print(f"Configuration loaded. DOCS_FOLDER set to: {DOCS_FOLDER}")