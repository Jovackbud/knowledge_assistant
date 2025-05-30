# Service Assistant Project

This project is a service assistant application that uses a local LLM and a Milvus vector database to provide responses and manage information. It is designed to be run using Docker and Docker Compose for production-like environments, but can also be run locally for development. The frontend is a simple HTML page served directly by FastAPI.

## Prerequisites

*   **Python 3.8+:** Ensure Python is installed.
*   **Docker Desktop:** (For Docker-based deployment) Ensure Docker Desktop (or Docker Engine with Docker Compose CLI plugin) is installed and running. Download from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).
*   **Project Files:** Clone this repository.
*   **Milvus Configuration Files:** (For Docker-based deployment) Ensure you have the `milvus` subdirectory in your project root, containing the necessary volume structure for Milvus (i.e., `milvus/volumes/etcd`, `milvus/volumes/minio`, `milvus/volumes/milvus`). The `docker-compose.yml` expects this structure for Milvus data persistence.

## Setup Instructions

### 1. Environment and Dependencies

*   **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
*   **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Milvus Setup (Required for RAG features)

The application's RAG (Retrieval Augmented Generation) capabilities depend on Milvus.

*   **Option A: Using Docker for Milvus (Recommended for Simplicity)**
    *   If you have Docker, you can run Milvus using the provided `docker-compose.yml`.
    *   To start the Milvus stack (and the application):
        ```bash
        docker-compose up -d --build
        ```
    *   If you only want to start the Milvus components (e.g., if running the app locally):
        ```bash
        docker-compose up -d etcd minio standalone
        ```
    *   Ensure your `.env.production` (or local environment variables) has `MILVUS_HOST=localhost` if running the FastAPI app locally and Milvus in Docker this way. If running the app within the main `docker-compose` setup, `MILVUS_HOST` should be `standalone`.

*   **Option B: Local Milvus Installation**
    *   Install Milvus natively on your system. Refer to the [official Milvus installation guide](https://milvus.io/docs/install_standalone-docker.md) (though this link is for Docker, find the appropriate guide for your OS if you prefer a native install).
    *   Ensure Milvus is running and accessible. You might need to adjust `MILVUS_HOST` and `MILVUS_PORT` environment variables accordingly.

### 3. Environment Variables

*   **Create `.env.production` File (or set environment variables):**
    *   In the root directory of the project, create a file named `.env.production` (or configure your system's environment variables).
    *   Add the following (adjust as needed):
        ```env
        MILVUS_HOST=localhost # Or 'standalone' if running app within the main docker-compose
        LLM_MODEL=gemma:2b    # Example model, ensure it's available via Ollama
        PYTHONUNBUFFERED=1
        DOCS_FOLDER=sample_docs_phase_1 # Relative to the './data' volume if using Docker for the app
        OLLAMA_BASE_URL=http://localhost:11434 # Default Ollama URL
        ```
    *   **Note on `LLM_MODEL`**: The application uses Ollama. When running the FastAPI app locally (outside the main `docker-compose` setup), you'll need to have Ollama installed, running, and the specified model pulled (e.g., `ollama pull gemma:2b`). If Ollama is running on a different host/port, update `OLLAMA_BASE_URL`. When using `docker-compose up --build`, the `app` service will handle Ollama.

### 4. Place Documents (Optional, for RAG)

*   The application expects documents in a folder (default is `./data/sample_docs_phase_1/`).
*   Create this directory and place your `.txt`, `.pdf`, or `.md` files there if you want to use the RAG features. The `init_all_databases()` function called on startup will attempt to process these.

## Running the Application

The application now runs as a single FastAPI service, which also serves the HTML frontend.

*   **Option A: Using Docker Compose (Recommended for Production-like Environment)**
    1.  **Configure `.env.production` for Docker:**
        *   Set `MILVUS_HOST=standalone`.
        *   The `LLM_MODEL` will be pulled by the `app` service's Ollama instance.
        *   `OLLAMA_BASE_URL` will be `http://localhost:11434` (Ollama runs in the same container as the app).
            ```env
            MILVUS_HOST=standalone
            LLM_MODEL=gemma:2b
            PYTHONUNBUFFERED=1
            DOCS_FOLDER=sample_docs_phase_1
            OLLAMA_BASE_URL=http://localhost:11434
            ```
    2.  **Build and Run Containers:**
        ```bash
        docker-compose up --build -d
        ```
        The `-d` flag runs the containers in detached mode.
    3.  **Accessing the Application:**
        *   The HTML frontend is accessible at: [http://localhost:8000](http://localhost:8000)
        *   API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
        *   API Documentation (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

*   **Option B: Local Development (without Docker for the app itself)**
    1.  **Ensure Prerequisites are Met:**
        *   Python installed, virtual environment activated, dependencies installed.
        *   Milvus is running and accessible (either via Docker or locally).
        *   Ollama is installed, running, and the desired model is pulled (e.g., `ollama pull gemma:2b`).
        *   Environment variables are set (e.g., in `.env.production` or system-wide), with `MILVUS_HOST=localhost` if Milvus is outside the app's direct environment.
    2.  **Run the FastAPI Application using the script:**
        ```bash
        bash scripts/start.sh
        ```
        This script uses Uvicorn to run the application.
    3.  **Accessing the Application:**
        *   The HTML frontend is accessible at: [http://localhost:8000](http://localhost:8000)
        *   API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
        *   API Documentation (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Adding New Users for Local Testing

User profiles for local testing and initial setup are managed within the `src/database_utils.py` file, specifically in the `_create_sample_users_if_not_exist` function.

To add a new user:

1.  **Edit `src/database_utils.py`**:
    Open the file and locate the `sample_users` dictionary within the `_create_sample_users_if_not_exist` function.
2.  **Add a New User Entry**:
    Add a new entry to the dictionary using the user's email as the key. Ensure that the department and project tags used are valid according to the system's configuration (typically defined or expected by other parts of the system, like document tagging).

    Here's an example structure for a new user:
    ```python
    "new.user@example.com": {
        "user_hierarchy_level": 0,  # Defines access level, e.g., 0 for general, higher for more access
        "departments": ["IT_DEPARTMENT"], # User's primary department(s)
        "projects_membership": ["PROJECT_BETA"], # Projects the user is part of
        "contextual_roles": {
            # Roles within specific projects or departments
            "PROJECT_BETA": ["DEVELOPER_ROLE"], 
            "IT_DEPARTMENT": ["HELPDESK_ROLE"] 
        }
    }
    ```
    *   `user_hierarchy_level`, `departments`, `projects_membership`, and `contextual_roles` collectively define the user's access rights and how information is filtered or presented to them. Ensure these values, especially the string tags for departments, projects, and roles, are consistent with how they are used elsewhere (e.g., in document metadata or access control logic).

3.  **Restart the FastAPI Application**:
    After saving your changes to `src/database_utils.py`, the FastAPI application needs to be restarted.
    *   If running with `docker-compose up`, you can restart the `app` service: `docker-compose restart app` or stop and restart all: `docker-compose down && docker-compose up --build -d`.
    *   If running with `bash scripts/start.sh` or `uvicorn` directly, stop the server (Ctrl+C) and run the start command again.

    Upon restart, the `_create_sample_users_if_not_exist` function will execute, and if the new user's email is not already in the user database, their profile will be added.

## Local LLM and Vector Database

*   **LLM:** The application uses Ollama. When run locally (Option B for running the app), ensure Ollama is installed and serving the model. When run with Docker (Option A), the `app` container runs its own Ollama instance and pulls the model specified in `.env.production`.
*   **Vector Database:** Milvus. Can be run via Docker (using the provided `docker-compose.yml`) or as a separate local installation. Data for Dockerized Milvus is persisted in `./milvus/volumes/`.

## Stopping the Application

*   **Local `start.sh` / Uvicorn:** Press `Ctrl+C` in the terminal where the script or Uvicorn is running.
*   **Docker Compose:**
    *   If running in detached mode (`-d`), use:
        ```bash
        docker-compose down
        ```
    *   If running in the foreground, press `Ctrl+C` in the terminal, then run `docker-compose down`.
    *   To also remove the Milvus data volumes (BE CAREFUL, this deletes Milvus data from `./milvus/volumes/`):
        ```bash
        # docker-compose down -v
        ```

## Project Structure (Simplified)

```
.
├── data/                    # Default directory for documents (e.g., sample_docs_phase_1)
│   └── sample_docs_phase_1/
│       └── example.txt
├── milvus/                  # Milvus data volumes (for Docker)
│   └── volumes/
├── scripts/                 # Helper scripts
│   └── start.sh             # Script to run the FastAPI app locally
├── src/                     # Source code
│   ├── __init__.py
│   ├── auth_service.py      # User authentication logic
│   ├── config.py            # Configuration models (Pydantic)
│   ├── database_utils.py    # Database initialization & utilities (incl. sample users)
│   ├── document_updater.py  # For processing and adding documents to Milvus
│   ├── feedback_system.py   # Feedback recording logic
│   ├── main.py              # FastAPI application entry point
│   ├── rag_processor.py     # RAG logic (Langchain, Milvus, Ollama)
│   └── ticket_system.py     # Ticketing logic
├── static/                  # Static frontend files
│   └── index.html           # HTML frontend served by FastAPI
├── .env.production          # Environment variables (user-created, gitignored)
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Dockerfile for the application
├── requirements.txt         # Python dependencies
└── README.md                # This file
```
