# AI4AI Knowledge Assistant

## Project Description

The AI4AI Knowledge Assistant is a comprehensive, enterprise-grade AI application designed to provide secure and intelligent access to internal company knowledge. It leverages Retrieval Augmented Generation (RAG) to answer user queries, incorporates a robust Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC) system for document access, and includes features like an AI-powered ticket system and user feedback mechanisms.

The backend is built with FastAPI, utilizing Google's Generative AI models for embeddings and language generation, Pinecone for vector storage, and an S3-compatible bucket (like AWS S3 or Cloudflare R2) for document storage. PostgreSQL serves as the persistent database for user profiles, sync states, tickets, and feedback.

## Features

*   **Retrieval Augmented Generation (RAG)**: Answers user questions by retrieving relevant information from a vast knowledge base, powered by Google Generative AI models.
*   **Dynamic Access Control (RBAC/ABAC)**:
    *   Documents are tagged with `department_tag`, `project_tag`, `hierarchy_level_required`, and `role_tag_required`.
    *   Users are assigned `user_hierarchy_level`, `departments`, `projects_membership`, and `contextual_roles`.
    *   Access to information is dynamically filtered based on the user's permissions, ensuring sensitive data is only accessible to authorized personnel.
*   **Document Synchronization**: Automatically syncs documents from an S3-compatible bucket to Pinecone, detecting new, updated, and deleted files using ETags. Supports `.txt`, `.pdf`, and `.md` file types.
*   **AI-Powered Ticket System**:
    *   Suggests the most relevant support team (e.g., IT, HR, Legal) for a user's question using semantic similarity.
    *   Allows users to create support tickets, recording the question, chat history, system-suggested team, and user-selected team.
*   **User Feedback Mechanism**: Enables users to provide feedback (thumbs up/down) on AI answers, helping to improve the system over time.
*   **Admin Panel**:
    *   Manage user permissions (hierarchy level, department/project memberships, contextual roles, admin status).
    *   View recent support tickets.
    *   Trigger manual document synchronization.
*   **Secure Authentication**: Implements JWT-based authentication using HTTP-only, secure cookies for session management.
*   **Scalable Architecture**: Designed for cloud deployment with containerization support, leveraging managed services like Pinecone, S3, and PostgreSQL.
*   **Health Check Endpoint**: A `/healthz` endpoint for monitoring application status.

## Technologies Used

*   **Backend Framework**: FastAPI
*   **Vector Database**: Pinecone
*   **Large Language Models (LLM) & Embeddings**: Google Generative AI (Gemini Flash, Text Embedding 004)
*   **Document Storage**: AWS S3 or S3-compatible (e.g., Cloudflare R2)
*   **Relational Database**: PostgreSQL (via SQLAlchemy)
*   **Orchestration & RAG**: LangChain
*   **Reranking**: FlashRank
*   **Authentication**: `python-jose`, `passlib`
*   **Cloud SDK**: Boto3 (for S3 interaction)
*   **Data Validation**: Pydantic
*   **Utilities**: NumPy, `python-dotenv`, `pathlib`, `re`, `logging`

## Getting Started

Follow these steps to set up and run the AI4AI Knowledge Assistant locally or prepare for deployment.

### Prerequisites

*   Python 3.9+
*   Docker (optional, for database setup)
*   An AWS account (or S3-compatible storage like Cloudflare R2)
*   A Pinecone account
*   A Google Cloud Project with Generative AI API enabled

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/ai4ai-knowledge-assistant.git
    cd ai4ai-knowledge-assistant
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    If `requirements.txt` is not provided, you can generate one or install manually:
    ```bash
    pip install fastapi uvicorn langchain-pinecone langchain-google-genai langchain-community langchain-text-splitters boto3 python-dotenv pydantic sqlalchemy psycopg2-binary python-jose passlib[bcrypt] flashrank numpy
    ```

### Environment Variables

Create a `.env` file in the root directory of the project and populate it with the following:

```env
# --- Database Configuration ---
DATABASE_URL="postgresql://user:password@host:port/dbname" # e.g., postgresql://postgres:mypassword@localhost:5432/ai4ai_db

# --- AWS S3 / R2 Configuration ---
AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
# For S3-compatible storage like R2, you might need an endpoint URL
AWS_ENDPOINT_URL="YOUR_S3_COMPATIBLE_ENDPOINT_URL" # e.g., https://<account_id>.r2.cloudflarestorage.com
S3_BUCKET_NAME="your-knowledge-bucket" # Name of your S3/R2 bucket
DOCS_FOLDER="sample_docs" # Local folder to simulate S3 structure for document updates. Can be 'remote_docs' for S3.

# --- Pinecone Configuration ---
PINECONE_API_KEY="YOUR_PINECONE_API_KEY"
PINECONE_ENVIRONMENT="YOUR_PINECONE_ENVIRONMENT" # e.g., us-east-1
PINECONE_INDEX_NAME="knowledge-assistant-v2"

# --- Google Generative AI Configuration ---
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY" # Used by langchain-google-genai
EMBEDDING_MODEL="models/text-embedding-004"
LLM_GENERATION_MODEL="gemini-2.5-flash-lite"
LLM_REPHRASE_MODEL="gemini-2.5-flash-lite"

# --- Reranker Configuration ---
USE_RERANKER="true" # Set to "false" to disable reranking
RERANKER_MODEL="ms-marco-MiniLM-L-12-v2" # Example model, refer to FlashRank docs

# --- JWT Authentication ---
JWT_SECRET_KEY="YOUR_SUPER_SECRET_RANDOM_KEY_AT_LEAST_32_CHARS" # Generate with: openssl rand -hex 32

# --- Admin Sync Token (for scheduled syncs) ---
SYNC_SECRET_TOKEN="YOUR_SECURE_SYNC_TOKEN" # A long, random string for the /admin/sync_documents endpoint

# --- CORS Configuration (for frontend) ---
RENDER_EXTERNAL_URL="https://ai4ai-knowledge-assistant.onrender.com/" 