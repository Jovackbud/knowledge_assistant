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
        logger.info("Initializing shared Google embedding clients...")
        try:
            # Client optimized for embedding documents to be stored
            self.document_embedder = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL,
                task_type="retrieval_document"
            )
            
            # Client optimized for embedding search queries
            self.query_embedder = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL,
                task_type="retrieval_query"
            )
            logger.info("✅ Shared Google document and query embedders loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load shared Google embedders: {e}", exc_info=True)
            raise

# Create a single, global instance of the services
shared_services = SharedServices()