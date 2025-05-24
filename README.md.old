# Service Assistant Project

This project is a service assistant application that uses a local LLM and a Milvus vector database to provide responses and manage information. It is designed to be run using Docker and Docker Compose.

## Prerequisites

*   **Docker Desktop:** Ensure Docker Desktop (or Docker Engine with Docker Compose CLI plugin) is installed and running on your system. Download from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).
*   **Local Milvus Image:** You need a local tarball of the Milvus standalone Docker image (version 2.5.x). For example, `milvus-standalone-v2.5.8.tar.gz` (adjust filename as per your actual file).
*   **Project Files:** Clone this repository.

## Setup Instructions

1.  **Place Milvus Image:**
    *   Put your Milvus standalone image tarball (e.g., `milvus-standalone-v2.5.8.tar.gz`) into a known directory in this project, for example, in the project root or a subdirectory like `local_images/`.

2.  **Load Local Milvus Image into Docker:**
    *   Open your terminal/command prompt.
    *   Navigate to the directory where you placed the Milvus image tarball.
    *   Load the image into Docker using the `docker load` command. For example:
        ```bash
        docker load -i milvus-standalone-v2.5.8.tar.gz 
        ```
    *   After loading, Docker should report the image name and tag (e.g., `milvusdb/milvus:v2.5.8-standalone`).
    *   **Important:** The `docker-compose.yml` file expects the Milvus image to be named `local-milvus-standalone:2.5`. If your loaded image has a different name/tag (like `milvusdb/milvus:v2.5.8-standalone`), you **must** either:
        *   Tag your loaded image to match:
            ```bash
            docker tag <current_image_name>:<current_tag> local-milvus-standalone:2.5
            ```
            (e.g., `docker tag milvusdb/milvus:v2.5.8-standalone local-milvus-standalone:2.5`)
        *   OR, update the `image` field in `docker-compose.yml` under the `milvus` service to match your loaded image's name and tag.

3.  **Create `.env.production` File:**
    *   In the root directory of the project, create a file named `.env.production`.
    *   Add the following environment variables to this file:
        ```env
        MILVUS_HOST=milvus
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

4.  **Place Documents (Optional):**
    *   The application expects documents in a folder specified by `DOCS_FOLDER` (default is `sample_docs_phase_1` inside the `/data` directory in the container, which is mounted from `./data/sample_docs_phase_1` on your host).
    *   If you're using the default, create `./data/sample_docs_phase_1/` and place your `.txt`, `.pdf`, or `.md` files there.

## Building and Running the Application

1.  **Build and Run Containers:**
    *   Open your terminal in the root directory of the project.
    *   Run the following command:
        ```bash
        docker-compose up --build
        ```
    *   This command will:
        *   Build the application Docker image (which includes installing Ollama and pulling the `gemma3:1b` LLM model). This can take some time, especially the first time.
        *   Start the Milvus container (using your loaded local image) and the application container.

2.  **Accessing the Application:**
    *   Once the containers are running, the Streamlit application should be accessible in your web browser at:
        [http://localhost:8501](http://localhost:8501)

## Local LLM and Vector Database

*   **LLM:** The application uses a locally running Ollama instance within the `app` Docker container, serving the `gemma3:1b` model.
*   **Vector Database:** Milvus standalone (version 2.5.x) runs in its own Docker container, using the local image you provided.

## Stopping the Application

*   To stop the containers, press `Ctrl+C` in the terminal where `docker-compose up` is running.
*   To remove the containers (and optionally the Milvus data volume), you can run:
    ```bash
    docker-compose down
    # To also remove the Milvus data volume (be careful, this deletes Milvus data):
    # docker-compose down -v 
    ```
