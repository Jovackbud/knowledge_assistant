```markdown
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
RENDER_EXTERNAL_URL="your-app-name.onrender.com" # Your deployed frontend URL (optional, local dev will use localhost)
```

**Note on S3/R2 Credentials:** If deploying to a service like Render that supports connecting to S3-compatible storage directly via environment variables, you might only need `S3_BUCKET_NAME`. Ensure `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_ENDPOINT_URL` (if not AWS S3) are correctly configured for your environment.

### Database Setup

The application automatically initializes the necessary tables (`UserAccessProfile`, `tickets`, `feedback`, `SyncState`) on startup if they don't exist.

**Example PostgreSQL Setup (using Docker):**

```bash
docker run --name ai4ai-postgres -e POSTGRES_USER=user -e POSTGRES_PASSWORD=password -e POSTGRES_DB=ai4ai_db -p 5432:5432 -d postgres:16-alpine
```
Then, update `DATABASE_URL` in `.env` to `postgresql://user:password@localhost:5432/ai4ai_db`.

### Document Preparation

1.  **Create your knowledge base:**
    *   In your S3 bucket (or `DOCS_FOLDER` if using local simulation), create a structure similar to your internal document hierarchy.
    *   Place `metadata.json` files in directories to define access permissions (e.g., `department_tag`, `project_tag`, `hierarchy_level_required`, `role_tag_required`). These metadata files are inherited by subdirectories unless overridden.
    *   Example `metadata.json`:
        ```json
        {
          "department_tag": "HR",
          "hierarchy_level_required": 1,
          "role_tag_required": "MANAGER"
        }
        ```
    *   Upload your `.txt`, `.pdf`, or `.md` documents.

### Initial Document Synchronization

The application will attempt to connect to Pinecone and your S3 bucket on startup. To perform the initial sync or any manual sync:

1.  **Run the FastAPI application** (see "Running the Application" below).
2.  **Trigger the sync endpoint** (e.g., via `curl` or Postman):
    ```bash
    curl -X POST "http://localhost:8000/admin/sync_documents" \
         -H "X-Sync-Token: YOUR_SECURE_SYNC_TOKEN_FROM_ENV"
    ```
    This will start a background task to download, process, embed, and upload documents to Pinecone.

### Running the Application

Start the FastAPI application using Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
The `--reload` flag is useful for local development as it restarts the server on code changes. For production, remove this flag.

The application will be accessible at `http://localhost:8000`.

## API Endpoints

The API includes endpoints for authentication, RAG queries, ticket management, feedback, and admin functions.

*   **`GET /`**: Serves the `index.html` frontend.
*   **`GET /healthz`**: Basic health check.
*   **`POST /auth/login`**: Authenticate a user and set an `access_token` cookie.
*   **`POST /auth/logout`**: Clear the `access_token` cookie.
*   **`POST /auth/me`**: Get the current authenticated user's profile.
*   **`POST /rag/chat`**: Main RAG endpoint to ask questions and get streamed AI responses.
*   **`POST /tickets/suggest_team`**: Suggests a support team based on a question.
*   **`POST /tickets/create`**: Creates a new support ticket.
*   **`POST /feedback/record`**: Records user feedback on an AI answer.
*   **`POST /admin/sync_documents`**: Triggers document synchronization (requires `X-Sync-Token` header).
*   **`GET /admin/config_tags`**: (Admin only) Returns configured department tags.
*   **`GET /admin/view_user_permissions/{email}`**: (Admin only) View a specific user's permissions.
*   **`POST /admin/user_permissions`**: (Admin only) Update a user's permissions.
*   **`POST /admin/remove_user`**: (Admin only) Remove a user.
*   **`GET /admin/recent_tickets`**: (Admin only) View recent support tickets.

## Admin Users and Sample Data

On first run, the database will be initialized, and several sample user profiles will be created if they don't exist:

*   `staff.hr@example.com`
*   `lead.it.project_alpha@example.com`
*   `exec.finance@example.com`
*   `general.user@example.com`
*   `admin.user@example.com` (This user has `is_admin: True` and can access admin endpoints)

You can use `admin.user@example.com` to log in and manage other users via the admin endpoints (e.g., setting a user as an admin or modifying their access rights).

## Directory Structure

*   `main.py`: The main FastAPI application entry point, defining all API routes and dependencies.
*   `config.py`: Centralized configuration for environment variables, constants, LLM models, Pinecone index, and Pydantic data models.
*   `utils.py`: Contains utility functions like `sanitize_tag` for normalizing strings.
*   `services.py`: Initializes and provides shared services across the application, such as Google Generative AI embedding models.
*   `database_utils.py`: Handles all database connections (SQLAlchemy), schema initialization, and CRUD operations for user profiles, tickets, feedback, and sync state.
*   `auth_service.py`: Contains the business logic for fetching, updating, and removing user access profiles.
*   `security.py`: Manages JWT token creation, decoding, and FastAPI security dependencies for authentication.
*   `document_updater.py`: Orchestrates the document synchronization process from S3/R2 to Pinecone, including downloading, loading, splitting, embedding, and upserting/deleting documents.
*   `rag_processor.py`: Implements the RAG (Retrieval Augmented Generation) pipeline, including prompt templating, retriever setup, reranking with FlashRank, and LLM integration.
*   `ticket_system.py`: Provides the AI-powered team suggestion logic and integrates with the database for ticket creation.
*   `feedback_system.py`: Handles the logic for recording user feedback on AI responses.
*   `prompts/`: A directory expected to contain `.md` files for LLM prompts (e.g., `rag_system_prompt.md`, `rephrase_question_prompt.md`).
*   `static/`: Contains static frontend files (e.g., `index.html`) served by FastAPI.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

This project is open-sourced under the MIT License.
```