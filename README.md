# Service Assistant Project

**In Simple Terms:**

This project is a service assistant application that uses a local LLM (via Ollama) and a Milvus vector database to provide responses and manage information.
-   **Documents get automatic 'access tags' based on their specific folder location.** For example, a document in `Docs/HR/StaffOnly/benefits_summary.pdf` gets tags like "HR Department" and "Staff Level Access." The more detailed the folder path, the more precise its access requirements become.
-   **People get 'access keys' based on their overall job level, departments, project teams, and specific functional roles.** A Manager's general key, for instance, will typically also unlock documents accessible to Staff within their specific department.
-   When someone asks a question, the system first **checks which documents their unique set of keys can unlock.**
-   Then, it **searches for the answer *only* in those permitted documents.** This ensures people only see information they're allowed to access.

## Features

*   AI-powered chat using local Large Language Models (LLMs) via Ollama.
*   Retrieval Augmented Generation (RAG) for answering questions based on a corpus of documents.
*   Role-based and path-based access control for documents.
*   Ticketing system integration (conceptual).
*   Feedback mechanism for responses.
*   Admin interface for user management (API-based).

## System Architecture

The application consists of:

*   **FastAPI Backend:** Serves the API, handles business logic, and manages user interactions. Also serves a simple static HTML frontend.
*   **Ollama:** Runs local LLMs (e.g., Gemma, Llama) for text generation. Integrated directly into the application container for Render deployment.
*   **Milvus:** Vector database used to store document embeddings for efficient similarity search in the RAG process. Typically run as a separate service stack for local development.
*   **SQLite:** Used for storing application data such as user profiles, tickets, and feedback.

The main workflow involves the user sending a query through the API. The FastAPI backend, using the RAG processor, converts the query into an embedding, searches Milvus for relevant document chunks (respecting user permissions), and then uses Ollama to generate a response based on the retrieved context.

## Permissions Model Overview

The system uses a sophisticated permissions model based on:

1.  **Path-Derived Metadata:** Document access tags (department, project, role, hierarchy level) are automatically derived from their folder path within the `DOCS_FOLDER`.
    *   **Specificity:** The most specific path takes precedence. E.g., rules for `Docs/HR/Staff/` override rules for `Docs/Staff/` for documents within the former.
    *   **Naming Conventions:** Strict adherence to folder naming conventions (defined in `src/config.py`) is crucial for accurate permission assignment.
2.  **User Profile Attributes:** User profiles store their department, projects, roles, and hierarchy level.
    *   **Access Levels:** Higher access levels (e.g., Manager) typically include permissions of lower levels (e.g., Staff) within the same context (department/project).
3.  **Cross-Functional Projects:** Users get access to project folders (e.g., `Docs/Projects/ProjectAlpha/`) if their profile includes membership for that project, regardless of their primary department.

## Prerequisites for Local Development

*   **Python 3.10+:** Ensure Python is installed.
*   **Docker Desktop:** Required for running Milvus and associated services locally using `docker-compose`. Download from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).
*   **Git:** For cloning the repository.
*   **Ollama (Optional, if not using the app's internal Ollama for local dev):** If you wish to run Ollama separately for local FastAPI development (outside the main `docker-compose up` which includes it in the `app` service), install it from [https://ollama.com/](https://ollama.com/) and pull your desired model (e.g., `ollama pull gemma:2b`).

## Setup and Running Locally

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Environment Variables:**
    *   Create a `.env` file in the project root (this is gitignored).
    *   Populate it with necessary variables. See `.env.example` if provided, or use the following template:
        ```env
        # Example .env for local development
        LLM_MODEL="gemma:2b" # Or any other model pulled in Ollama
        DOCS_FOLDER="sample_docs_phase_1" # Relative to project root, or an absolute path

        # For Milvus running via docker-compose from this project
        MILVUS_HOST="localhost" # Or "standalone" if app is run via `docker-compose up app`
        MILVUS_PORT="19530"

        # For Ollama if app service runs it (default in docker-compose)
        OLLAMA_BASE_URL="http://localhost:11434"

        PYTHONUNBUFFERED=1
        # Add other environment variables as defined in src/config.py if needed
        ```
    *   **Important:** If running the FastAPI app locally (`bash scripts/start.sh`) and Milvus via `docker-compose up etcd minio standalone`, set `MILVUS_HOST=localhost`. If running the entire stack including the app via `docker-compose up --build`, set `MILVUS_HOST=standalone` (as the app service can resolve Milvus by its service name).

3.  **Milvus Vector Database (via Docker Compose):**
    *   The `docker-compose.yml` file configures Milvus, Minio, and Etcd.
    *   Ensure you have the `milvus/volumes/` subdirectories created in your project root if they don't exist (`milvus/volumes/etcd`, `milvus/volumes/minio`, `milvus/volumes/milvus`). These are gitignored but required for persistent Milvus data.
    *   Start the Milvus stack:
        ```bash
        docker-compose up -d etcd minio standalone
        ```
    *   To stop them: `docker-compose down` (add `-v` to remove volumes).

4.  **Application Setup (Python Virtual Environment):**
    *   Create and activate a virtual environment:
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Windows: venv\Scripts\activate
        ```
    *   Install dependencies:
        ```bash
        pip install -r requirements.txt
        ```

5.  **Place Documents:**
    *   Create the folder specified by `DOCS_FOLDER` in your `.env` file (e.g., `./sample_docs_phase_1/`).
    *   Place your `.txt`, `.pdf`, or `.md` files there. The application will process these on startup.

6.  **Running the Application:**
    *   **Option A: Locally with Uvicorn (Milvus running separately in Docker)**
        *   Ensure Ollama is running locally if you haven't configured the app to use an external one.
        *   Run the FastAPI application:
            ```bash
            bash scripts/start.sh
            ```
    *   **Option B: Fully with Docker Compose (includes app, Milvus, and embedded Ollama)**
        *   This uses the `Dockerfile` to build the app image, which includes Ollama.
        *   Set `MILVUS_HOST=standalone` in your `.env` file.
        *   Build and run all services:
            ```bash
            docker-compose up --build -d app # This will also start dependent Milvus services
            ```
            Or `docker-compose up --build` to see logs.
    *   **Accessing the Application:**
        *   Web Interface: [http://localhost:8000/](http://localhost:8000/)
        *   API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
        *   API Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

```
.
├── .dockerignore          # Specifies intentionally untracked files that Docker should ignore
├── .env                   # Local environment variables (gitignored)
├── .gitignore             # Specifies intentionally untracked files that Git should ignore
├── Dockerfile             # Instructions for building the application Docker image
├── README.md              # This file
├── ADMIN_README.md        # Guide for non-technical administrators
├── docker-compose.yml     # Defines services for local development (app, Milvus, etc.)
├── requirements.txt       # Python dependencies
├── scripts/               # Utility scripts
│   ├── entrypoint.sh      # Entrypoint for Docker image (starts Ollama, pulls model, runs app)
│   ├── initialize.py    # Initialization logic (called by main app on startup)
│   └── start.sh           # Script to run FastAPI app locally using Uvicorn
├── src/                   # Source code for the application
│   ├── __init__.py
│   ├── auth_service.py    # Authentication and user profile logic
│   ├── config.py          # Application configuration and Pydantic models
│   ├── database_utils.py  # Database interaction utilities
│   ├── document_updater.py# Logic for processing and syncing documents to Milvus
│   ├── feedback_system.py # Feedback recording logic
│   ├── main.py            # FastAPI application entry point and API routes
│   ├── rag_processor.py   # RAG logic (Langchain, Milvus, Ollama interaction)
│   └── ticket_system.py   # Ticketing system logic
├── static/                # Static files (e.g., HTML for frontend)
│   └── index.html
└── milvus/                # Placeholder for Milvus volumes (gitignored, created locally)
    └── volumes/
```

## Deployment to Render

This application is designed to be deployed to Render as a Docker container.

1.  **Repository Setup:** Ensure your `Dockerfile`, `requirements.txt`, `scripts/entrypoint.sh`, `src/`, and `static/` directories are committed to your Git repository.

2.  **Render Service Creation:**
    *   On the Render Dashboard, create a new "Web Service".
    *   Connect your Git repository.
    *   **Runtime:** Select "Docker". Render will use the `Dockerfile` from your repository.

3.  **Environment Variables:**
    *   In your Render service settings, go to the "Environment" section.
    *   Add the following crucial environment variables:
        *   `LLM_MODEL`: The Ollama model to pull and use (e.g., `gemma:2b`). The `entrypoint.sh` script will attempt to pull this model on startup.
        *   `OLLAMA_BASE_URL`: Set this to `http://localhost:11434`. Since Ollama runs within the same container, the application can access it via localhost.
        *   `DOCS_FOLDER`: Path within the container where documents are stored/mounted (e.g., `/data/docs`).
        *   `DATA_DIR_PATH`: Path for databases (e.g. `/data/database`). `src/config.py` uses this to construct `TICKET_DB_PATH`, `FEEDBACK_DB_PATH`, etc.
        *   `PYTHONUNBUFFERED=1`: Good for seeing logs immediately.
        *   `MILVUS_HOST`, `MILVUS_PORT`: If you are using a managed Milvus service (e.g., Zilliz Cloud, or another Milvus instance accessible via the internet), set these accordingly. If Milvus is intended to run *within* this setup (not typical for production Render without complex private services), this guide would need extension. For now, this guide assumes a local/dev setup for Milvus or an external one for cloud deployment. **Note:** Running Milvus itself directly on Render's basic web service instances is not straightforward. Consider a managed vector database for production.
    *   Add any other environment variables your `src/config.py` might require.

4.  **Render Disks (Persistence):**
    *   **Ollama Models:**
        *   Path in container: `/root/.ollama/models` (this is where `entrypoint.sh` and Ollama will store models, as per `ENV OLLAMA_MODELS` in Dockerfile).
        *   Create a Render Disk and mount it to this path. This prevents re-downloading models on every deploy/restart.
    *   **Application Data (Databases & Documents):**
        *   Path in container for databases: `/data/database` (SQLite files like `tickets.db`, `auth_profiles.db` will be stored here, based on `DB_PARENT_DIR` in `src/config.py`).
        *   Path in container for documents: `/data/docs` (Set your `DOCS_FOLDER` environment variable to this, e.g., `DOCS_FOLDER=/data/docs/my_documents`).
        *   Create a Render Disk and mount it to `/data`. This single disk can hold both `database` and `docs` subdirectories.

5.  **Build and Deploy:**
    *   Render will automatically build your Docker image from the `Dockerfile` and deploy it.
    *   The `ENTRYPOINT` and `CMD` specified in your `Dockerfile` (`entrypoint.sh` and then `uvicorn`) will be used.

6.  **Health Check:**
    *   Render typically uses TCP health checks by default.
    *   You can configure an HTTP health check to target an endpoint like `/docs` (FastAPI's Swagger UI) or create a dedicated `/healthz` endpoint in `src/main.py` that returns a 200 OK.

7.  **Accessing Your Deployed App:** Render will provide you with a `*.onrender.com` URL for your service.

## Key Configuration & Management Points

*   **Folder Naming Conventions:** The accuracy of document permissions heavily relies on strict adherence to folder naming conventions defined in `src/config.py` (e.g., for departments, roles, hierarchy levels). Inconsistent naming will lead to incorrect permission assignments.
*   **User Profile Accuracy:** Ensure user profile data (department, project, role, hierarchy level) in the `auth_profiles.db` is accurate and up-to-date. This is critical for correct permission enforcement.
*   **Document Synchronization:** Documents placed in the `DOCS_FOLDER` (on the persistent disk) are processed and indexed by the application on startup (due to `synchronize_documents()` in `main.py`'s startup event).

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
