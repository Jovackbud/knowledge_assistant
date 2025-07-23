import os
from typing import List, Dict, Any, TypedDict
from pathlib import Path
from dotenv import load_dotenv

from pydantic import BaseModel
# from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

# --- API & Server Configuration ---
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# Define the list of allowed origins for CORS.
if RENDER_EXTERNAL_URL:
    # Production environment
    ALLOWED_ORIGINS = [f"https://{RENDER_EXTERNAL_URL}"]
else:
    # Local development environment
    ALLOWED_ORIGINS = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

# --- Document Configuration ---
DOCS_FOLDER_NAME = os.getenv("DOCS_FOLDER", "sample_docs")
DOCS_FOLDER = Path(DOCS_FOLDER_NAME)
ALLOWED_EXTENSIONS = [".txt", ".pdf", ".md"]

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

# --- Reranker Configuration ---
USE_RERANKER = os.getenv("USE_RERANKER", "true").lower() in ("true", "1", "t")

# --- Vector Store Configuration ---
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "knowledge-assistant-v2")

ROLE_SPECIFIC_FOLDER_TAGS = {
    "lead_docs": "LEAD",
    "admin_files": "ADMIN",
    "manager_exclusive": "MANAGER", # More specific than hierarchy based manager
    "team_lead_private": "TEAM_LEAD"
}

# Numeric levels: Higher number means more privilege / more restricted access.
# These values can be used in 'metadata.json' files. The system does not automatically
# parse them from folder names.
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

# --- Text Processing ---
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBEDDING_MODEL = "models/gemini-embedding-001"
RERANKER_MODEL = "ms-marco-MiniLM-L-12-v2"
RERANKER_SCORE_THRESHOLD = 0.2
LLM_GENERATION_MODEL = "gemini-2.5-flash"

# --- Path for Synchronization State ---
SYNC_STATE_FILE = Path("/tmp/sync_state.json")

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

class UserPermissionsRequest(BaseModel):
    target_email: str
    permissions: Dict[str, Any]

class UserRemovalRequest(BaseModel):
    target_email: str

class UserProfile(TypedDict):
    user_email: str
    user_hierarchy_level: int
    departments: List[str]
    projects_membership: List[str]
    contextual_roles: Dict[str, List[str]]

# --- Constants for Dictionary Keys ---
USER_EMAIL_KEY = "user_email"
HIERARCHY_LEVEL_KEY = "user_hierarchy_level"
DEPARTMENTS_KEY = "departments"
PROJECTS_KEY = "projects_membership"
CONTEXTUAL_ROLES_KEY = "contextual_roles"

# --- Constants for Feedback Ratings ---
FEEDBACK_HELPFUL = "👍"
FEEDBACK_NOT_HELPFUL = "👎"


if __name__ == "__main__":
    print("--- Configuration Loaded ---")
    print(f"✅ Document Source Folder: '{DOCS_FOLDER_NAME}'")
    print(f"✅ Local Database Directory: '{DB_PARENT_DIR_NAME}'")
    print(f"✅ Pinecone Index Name: '{PINECONE_INDEX_NAME}'")
    print(f"✅ Embedding Model: '{EMBEDDING_MODEL}'")
    print("--------------------------")