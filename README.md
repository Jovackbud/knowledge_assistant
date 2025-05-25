# Service Assistant Project

This project is a service assistant application that uses a local LLM and a Milvus vector database to provide responses and manage information. It is designed to be run using Docker and Docker Compose.

## Prerequisites

*   **Docker Desktop:** Ensure Docker Desktop (or Docker Engine with Docker Compose CLI plugin) is installed and running on your system. Download from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).
*   **Project Files:** Clone this repository.
*   **Milvus Configuration Files:** Ensure you have the `milvus` subdirectory in your project root, containing the necessary volume structure for Milvus (i.e., `milvus/volumes/etcd`, `milvus/volumes/minio`, `milvus/volumes/milvus`). The `docker-compose.yml` expects this structure for Milvus data persistence.

## Setup Instructions

1.  **Verify Milvus Volume Paths (Optional but Recommended):**
    *   The main `docker-compose.yml` is configured to use `./milvus/volumes/etcd`, `./milvus/volumes/minio`, and `./milvus/volumes/milvus` for storing Milvus stack data. Ensure these paths are appropriate for your setup. If your Milvus volume data is located elsewhere within the project, you may need to adjust these paths in the `docker-compose.yml` file under the `etcd`, `minio`, and `standalone` service definitions.

2.  **Create `.env.production` File:**
    *   In the root directory of the project, create a file named `.env.production`.
    *   Add the following environment variables to this file:
        ```env
        MILVUS_HOST=standalone  # Connects to the Milvus service named 'standalone'
        LLM_MODEL=gemma3:1b
        PYTHONUNBUFFERED=1
        # Optional: Specify a folder for your documents if different from the default 'sample_docs_phase_1'.
        # This path is relative to the '/data' volume mount in the container.
        # For example, if you have './production_documents' on your host that you want to use,
        # and you've updated the volume mount in docker-compose.yml for 'app' service to
        # `- ./production_documents:/data/production_documents_in_container`
        # then you might set:
        # DOCS_FOLDER=production_documents_in_container 
        # By default, it uses 'sample_docs_phase_1' which maps to './data/sample_docs_phase_1' via the ./data:/data mount.
        ```

3.  **Place Documents (Optional):**
    *   The application expects documents in a folder specified by `DOCS_FOLDER` (default is `sample_docs_phase_1` inside the `/data` directory in the container, which is mounted from `./data/sample_docs_phase_1` on your host).
    *   If you're using the default, create `./data/sample_docs_phase_1/` (if it doesn't exist) and place your `.txt`, `.pdf`, or `.md` files there.

## Building and Running the Application

1.  **Build and Run Containers:**
    *   Open your terminal in the root directory of the project.
    *   Run the following command:
        ```bash
        docker-compose up --build
        ```
    *   This command will:
        *   Build the application Docker image (which includes installing Ollama and pulling the `gemma3:1b` LLM model). This can take some time on the first run.
        *   Start the integrated Milvus stack (etcd, MinIO, Milvus standalone using image `milvusdb/milvus:v2.5.0`) and the application container.

2.  **Accessing the Application:**
    *   Once the containers are running (this might take a few minutes for Milvus to initialize fully), the Streamlit application should be accessible in your web browser at:
        [http://localhost:8501](http://localhost:8501)

## Local LLM and Vector Database

*   **LLM:** The application uses a locally running Ollama instance within the `app` Docker container, serving the `gemma3:1b` model.
*   **Vector Database:** A complete Milvus standalone stack (version `v2.5.0`, including etcd and MinIO) runs as part of the `docker-compose` setup. Its data is persisted in the `./milvus/volumes/` directory on your host machine.

## Stopping the Application

*   To stop the containers, press `Ctrl+C` in the terminal where `docker-compose up` is running.
*   To remove the containers (and optionally the Milvus data volumes), you can run:
    ```bash
    docker-compose down
    # To also remove the Milvus data volumes (BE CAREFUL, this deletes Milvus data from ./milvus/volumes/):
    # docker-compose down -v 
    ```
