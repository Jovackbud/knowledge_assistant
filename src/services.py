import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class SharedServices:
    def __init__(self):
        # We are renaming the variable to be more explicit
        self.document_embedder = None
        self.query_embedder = None
        self._initialize_embedders()

    def _initialize_embedders(self):
        logger.info(f"Initializing shared Google embedding clients with model='{EMBEDDING_MODEL}'...")
        try:
            # Client optimized for embedding documents to be stored
            self.document_embedder = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL,
                task_type="RETRIEVAL_DOCUMENT"
            )

            # Client optimized for embedding search queries
            self.query_embedder = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL,
                task_type="RETRIEVAL_QUERY"
            )

            # --- Startup probe: fail fast if the model name is wrong/deprecated ---
            # A single cheap call catches 404/auth errors at boot, not mid-request.
            self.query_embedder.embed_query("probe")
            logger.info(f"✅ Embedding model '{EMBEDDING_MODEL}' validated and ready.")
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize or validate embedder (model='{EMBEDDING_MODEL}'): {e}. "
                "Check EMBEDDING_MODEL_NAME env var — likely set to a deprecated model name.",
                exc_info=True
            )
            raise

# Create a single, global instance of the services
shared_services = SharedServices()