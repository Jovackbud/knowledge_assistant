import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"  # Force legacy Keras
os.environ["KERAS_3"] = "0"

from typing import List, Dict

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Document Configuration ---
DOCS_FOLDER_NAME = os.getenv("DOCS_FOLDER", "sample_docs")
DOCS_FOLDER = Path(DOCS_FOLDER_NAME)
ALLOWED_EXTENSIONS = [".txt", ".pdf", ".md"]
DOCS_FOLDER.mkdir(parents=True, exist_ok=True)

# --- Document Metadata Defaults and Conventions ---
DEFAULT_DEPARTMENT_TAG = "GENERAL"
DEFAULT_PROJECT_TAG = "GENERAL"
DEFAULT_HIERARCHY_LEVEL = 0  # e.g., Staff/Member
DEFAULT_ROLE_TAG = "MEMBER" # Default role if no specific role folder found

# Known department tags for path parsing. Case-insensitive matching for path parts.
KNOWN_DEPARTMENT_TAGS = [
    "HR", "IT", "FINANCE",
    "LEGAL", "MARKETING", "OPERATIONS", "SALES"
]

# Mapping for role-specific folder names to role tags. Folder names are matched case-insensitively.
# Value is the role tag stored in metadata.
ROLE_SPECIFIC_FOLDER_TAGS = {
    "lead_docs": "LEAD",
    "admin_files": "ADMIN",
    "manager_exclusive": "MANAGER", # More specific than hierarchy based manager
    "team_lead_private": "TEAM_LEAD"
}

# Mapping for folder names to hierarchy levels. Matched case-insensitively.
# Numeric levels: Higher number means more privilege / more restricted access.
# Matched if a folder part contains the KEY (from this dict) and its _LEVEL_ (e.g., "STAFF_0_" or "MANAGER_1_"). Example: "STAFF_0_files", "confidential_MANAGER_1_docs".
HIERARCHY_LEVELS_CONFIG = {
    "STAFF": 0,
    "MEMBER": 0, # Alias for staff
    "MANAGER": 1,
    "SENIOR_MANAGER": 1, # Alias for manager or specific type
    "EXECUTIVE": 2,
    "DIRECTOR": 2, # Alias
    "BOARD": 3,
    "C_LEVEL": 3 # Alias
}
ADMIN_HIERARCHY_LEVEL = 3 # Define the admin hierarchy level

# Path structure examples:
# DOCS_FOLDER/PROJECT_X/file.pdf
# DOCS_FOLDER/PROJECT_X/lead_docs/plan.pdf
# DOCS_FOLDER/HR/PROJECT_Y/STAFF_0_GUIDELINES/onboarding.pdf
# DOCS_FOLDER/IT/PROJECT_Z/manager_exclusive/MANAGER_1_REPORTS/status.pdf

# --- Milvus Configuration ---
MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "adv_rbac_kb_v1") # New name for new structure
VECTOR_DIMENSION = 384

# --- Text Processing ---
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:1b")

# --- Database Paths ---
DB_PARENT_DIR_NAME = "database"
DB_PARENT_DIR = Path(DB_PARENT_DIR_NAME)
DB_PARENT_DIR.mkdir(exist_ok=True)

TICKET_DB_PATH = DB_PARENT_DIR / "tickets.db"
FEEDBACK_DB_PATH = DB_PARENT_DIR / "feedback.db"
AUTH_DB_PATH = DB_PARENT_DIR / "auth_profiles.db"
SYNC_STATE_FILE = DB_PARENT_DIR / "sync_state.json"

# --- Ticket System ---
TICKET_TEAMS = ["Helpdesk", "HR", "IT", "Legal", "General"]
TICKET_TEAM_DESCRIPTIONS = {
    "IT": "Issues related to company laptops, computers, software, installation, network connectivity, Wi-Fi, internet access, servers, VPNs, or printers.",
    "HR": "Questions about payroll, paychecks, compensation, vacation and leave policies, company benefits, employee onboarding, employment contracts, or company policy.",
    "Helpdesk": "Problems with account access, password resets, being locked out of systems, login errors, or general access permissions.",
    "Legal": "Matters concerning legal compliance, non-disclosure agreements (NDAs), contracts with third parties, data privacy, or official company statements."
    # "General" will be the fallback and does not need a description.
}

# --- API Models ---
from pydantic import BaseModel

class AuthCredentials(BaseModel):
    email: str

class RAGRequest(BaseModel):
    prompt: str
    chat_history: List[Dict[str, str]] = []

class SuggestTeamRequest(BaseModel):
    question_text: str

class CreateTicketRequest(BaseModel):
    question_text: str
    chat_history_json: str # Or use a more structured model like List[Dict[str, str]]
    selected_team: str

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    feedback_type: str # e.g., "👍" or "👎"


if __name__ == "__main__":
    print(f"✅ Config: Docs='{DOCS_FOLDER_NAME}', DBs='{DB_PARENT_DIR_NAME}', LLM='{LLM_MODEL}', MilvusColl='{MILVUS_COLLECTION_NAME}'")