# Service Assistant Project

This project is a service assistant application that uses a local LLM and a Milvus vector database to provide responses and manage information. It is designed to be run using Docker and Docker Compose for production-like environments, but can also be run locally for development.

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
    *   If you have Docker, you can run Milvus using the provided `docker-compose.yml` or a standalone Milvus Docker instance.
    *   To start only the Milvus stack from the existing compose file:
        ```bash
        docker-compose up -d etcd minio standalone
        ```
    *   Ensure your `.env.production` (or local environment variables) has `MILVUS_HOST=localhost` if running the FastAPI app locally and Milvus in Docker this way.

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
        # DOCS_FOLDER=sample_docs_phase_1 # Relative to the './data' volume if using Docker for the app
        OLLAMA_BASE_URL=http://localhost:11434 # Default Ollama URL
        ```
    *   **Note on `LLM_MODEL`**: The application uses Ollama. Ensure Ollama is running and the specified model is pulled (e.g., `ollama pull gemma:2b`). If running the FastAPI app locally, you'll need to have Ollama installed and running separately. If Ollama is running on a different host/port, update `OLLAMA_BASE_URL`.

### 4. Place Documents (Optional, for RAG)

*   The application expects documents in a folder (default is `./data/sample_docs_phase_1/`).
*   Create this directory and place your `.txt`, `.pdf`, or `.md` files there if you want to use the RAG features. The `init_all_databases()` function called on startup will attempt to process these.

## Running the Application (Development/Local with HTML Frontend)

These instructions are for running the FastAPI application directly, serving the HTML frontend.

1.  **Ensure Prerequisites are Met:**
    *   Python installed.
    *   Virtual environment activated and dependencies installed (`pip install -r requirements.txt`).
    *   Milvus is running and accessible (see Milvus Setup above).
    *   Ollama is installed, running, and the desired model is pulled (e.g., `ollama pull gemma:2b`).
    *   Environment variables are set (e.g., in `.env.production` or system-wide).

2.  **Run the FastAPI Application:**
    *   Open your terminal in the root directory of the project.
    *   Use Uvicorn to run the application (it's included in `requirements.txt`):
        ```bash
        uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   `--reload`: Enables auto-reload when code changes, useful for development.
    *   `--host 0.0.0.0`: Makes the server accessible from your local network.
    *   `--port 8000`: Runs on port 8000.

3.  **Accessing the HTML Frontend:**
    *   Once the Uvicorn server is running, open your web browser.
    *   Navigate to: [http://127.0.0.1:8000](http://127.0.0.1:8000) or [http://localhost:8000](http://localhost:8000).
    *   This will load the `index.html` page, allowing you to interact with the login and chat functionalities.

4.  **Accessing API Documentation:**
    *   FastAPI automatically generates interactive API documentation.
    *   Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
    *   ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Building and Running with Docker (Production-like)

This section describes using Docker Compose for a more integrated setup, including the application, Milvus, and Ollama (if configured within Docker).

1.  **Verify Milvus Volume Paths (Optional but Recommended):**
    *   The main `docker-compose.yml` is configured to use `./milvus/volumes/etcd`, `./milvus/volumes/minio`, and `./milvus/volumes/milvus` for storing Milvus stack data. Ensure these paths are appropriate for your setup.

2.  **Configure `.env.production` for Docker:**
    *   When running the full stack with `docker-compose`, `MILVUS_HOST` should typically be `standalone` (the service name in `docker-compose.yml`).
    *   The `LLM_MODEL` will be pulled by the `app` service's Ollama instance.
    *   `OLLAMA_BASE_URL` for the app service will usually be `http://localhost:11434` as Ollama runs in the same container.
        ```env
        MILVUS_HOST=standalone
        LLM_MODEL=gemma:2b # Or your preferred model
        PYTHONUNBUFFERED=1
        DOCS_FOLDER=sample_docs_phase_1
        OLLAMA_BASE_URL=http://localhost:11434
        ```

3.  **Place Documents for Docker Volume Mount:**
    *   The `docker-compose.yml` mounts `./data:/app/data`.
    *   If using the default `DOCS_FOLDER=sample_docs_phase_1`, ensure your documents are in `./data/sample_docs_phase_1/` on your host.

4.  **Build and Run Containers:**
    *   Open your terminal in the root directory of the project.
    *   Run the following command:
        ```bash
        docker-compose up --build
        ```
    *   This command will:
        *   Build the application Docker image (which includes installing Ollama and pulling the specified `LLM_MODEL`). This can take some time on the first run.
        *   Start the integrated Milvus stack and the application container.
    *   **Note:** The `app` service in `docker-compose.yml` as provided in the original project description does *not* explicitly expose port 8000 for the FastAPI app. If you want to access the HTML frontend while running with `docker-compose up`, you'll need to add a port mapping to the `app` service in `docker-compose.yml`, for example:
        ```yaml
        services:
          app:
            # ... other app config ...
            ports:
              - "8000:8000" # Map host port 8000 to container port 8000
        ```
        After adding this, you can access the HTML frontend at `http://localhost:8000`.

5.  **Accessing via Docker (if port mapped):**
    *   If you've mapped the port for the `app` service in `docker-compose.yml` (e.g., to 8000), then the HTML frontend is at `http://localhost:8000`.
    *   The original project description mentioned Streamlit on port 8501. If Streamlit is still part of the Docker setup (and not replaced by the FastAPI frontend), it would be at its configured port.

## Local LLM and Vector Database

*   **LLM:** The application uses Ollama. When run locally, ensure Ollama is installed and serving the model. When run with Docker, the `app` container runs its own Ollama instance.
*   **Vector Database:** Milvus. Can be run via Docker (using the provided compose file) or as a separate local installation. Data for Dockerized Milvus is persisted in `./milvus/volumes/`.

## Stopping the Application

*   **Local Uvicorn:** Press `Ctrl+C` in the terminal where Uvicorn is running.
*   **Docker Compose:** Press `Ctrl+C` in the terminal where `docker-compose up` is running.
    *   To remove the containers (and optionally the Milvus data volumes):
        ```bash
        docker-compose down
        # To also remove the Milvus data volumes (BE CAREFUL, this deletes Milvus data from ./milvus/volumes/):
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
├── src/                     # Source code
│   ├── __init__.py
│   ├── auth_service.py      # User authentication logic
│   ├── config.py            # Configuration models (Pydantic)
│   ├── database_utils.py    # Database initialization & utilities
│   ├── feedback_system.py   # Feedback recording logic
│   ├── main.py              # FastAPI application entry point
│   ├── rag_processor.py     # RAG logic (Langchain, Milvus, Ollama)
│   └── ticket_system.py     # Ticketing logic
├── static/                  # Static frontend files
│   └── index.html           # HTML frontend
├── .env.production          # Environment variables (user-created)
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Dockerfile for the application
├── requirements.txt         # Python dependencies
└── README.md                # This file
```
