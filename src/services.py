import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class SharedServices:
    def __init__(self):
        self.embedding_model = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        logger.info("Initializing shared embedding model...")
        try:
            self.embedding_model = GoogleGenerativeAIEmbeddings(model_name=EMBEDDING_MODEL)
            logger.info("✅ Shared Google embedding model client loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load shared Google embedding model: {e}", exc_info=True)
            raise

# Create a single, global instance of the services
shared_services = SharedServices()