# AI4AI Knowledge Assistant

The AI4AI Knowledge Assistant is an enterprise retrieval-augmented generation (RAG) platform that securely connects internal teams to fragmented company data. By enforcing strict role-based and attribute-based access controls, it ensures that sensitive documentation is delivered accurately and safely to authorized personnel, streamlining internal support and reducing bottlenecks.

## Tech Stack

*   **Backend Framework:** FastAPI, Uvicorn
*   **AI Orchestration & Embeddings:** LangChain, Google Generative AI (Gemini 2.5 Flash Lite, Gemini Embedding 001)
*   **Vector Database:** Pinecone
*   **Relational Database:** PostgreSQL (Neon) via SQLAlchemy
*   **Document Storage:** AWS S3 / Cloudflare R2
*   **Reranking Model:** FlashRank (ms-marco-MiniLM-L-12-v2)
*   **Data Processing:** Boto3, PyPDF, Unstructured, Pandas, Openpyxl
*   **Security & Auth:** JWT (`python-jose`), `passlib`, `bcrypt`, `cryptography`
*   **Deployment:** Docker, Render

## System Architecture

The application is built on a service-oriented architecture designed for scalability and secure data retrieval:

*   **API Layer:** A FastAPI backend handles client requests, authentication, and API routing.
*   **Document Pipeline:** Documents are ingested from an S3-compatible bucket. A synchronization process detects updates using ETags, chunks the text, generates vector embeddings using Google Generative AI, and stores them in Pinecone.
*   **RAG Engine:** User queries are vectorized and compared against the Pinecone index. Retrieved document chunks are reranked locally using FlashRank before being sent to the Gemini language model to generate grounded responses.
*   **Access Control:** PostgreSQL maintains user profiles and hierarchy levels. Every document and user is tagged with granular metadata (Department, Project, Hierarchy Level). The vector search leverages metadata pre-filtering at the database level to guarantee data sovereignty.
*   **Ticket System Integration:** Unresolved queries are automatically classified using semantic similarity to route support tickets to specific teams (e.g., IT, HR, Legal).

## Prerequisites

*   Python 3.9+
*   PostgreSQL database instance
*   Pinecone account and API key
*   AWS account or S3-compatible storage (e.g., Cloudflare R2) credentials
*   Google Cloud Project with the Generative AI API enabled

## Local Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jovackbud/ai4ai-knowledge-assistant.git
    cd ai4ai-knowledge-assistant
    ```

2.  **Environment Setup:**
    Create a `.env` file in the root directory. You can use `.env.example` as a template:
    ```bash
    cp .env.example .env
    ```
    Populate the required environment variables (Database URL, S3 credentials, Pinecone API key, Google API key, JWT secret).

3.  **Virtual Environment & Dependencies:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    
    pip install -r requirements.txt
    ```

4.  **Run the Application:**
    Start the FastAPI server locally:
    ```bash
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    ```

## Usage Examples

*   **Querying the Assistant:** Send an authenticated POST request to the `/api/chat` endpoint with your query to receive an AI-generated, context-aware answer based on accessible documents.
*   **Document Sync:** Trigger a synchronization via the admin endpoint `/admin/sync_documents` to pull new files from S3, embed them, and update the Pinecone vector index.
*   **Ticket Creation:** If an answer requires human escalation, use the `/api/tickets` endpoint to log a support ticket, which automatically attaches the conversation history and suggests the relevant department.