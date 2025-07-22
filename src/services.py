import logging
from langchain_huggingface import HuggingFaceEmbeddings
from .config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class SharedServices:
    def __init__(self):
        self.embedding_model = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        logger.info("Initializing shared embedding model...")
        try:
            self.embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            logger.info("✅ Shared embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load shared embedding model: {e}", exc_info=True)
            raise

# Create a single, global instance of the services
shared_services = SharedServices()