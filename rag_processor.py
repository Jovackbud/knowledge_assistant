import os
import logging
from pymilvus import utility
from typing import Dict, Any, List
from langchain_milvus import Milvus
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from config import (
    MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME,
    EMBEDDING_MODEL, LLM_MODEL
)
from auth_service import fetch_user_access_profile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, embeddings, vector_store, llm):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_template(
            "Answer based on context:\n{context}\nQuestion: {question}"
        )

    @classmethod
    def from_config(cls, force_recreate=False):
        embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
        vector_store = cls._init_vector_store(embeddings, force_recreate)
        llm = Ollama(model=LLM_MODEL)
        return cls(embeddings, vector_store, llm)

    @staticmethod
    def _init_vector_store(embeddings, force_recreate):
        try:
            if force_recreate and utility.has_collection(MILVUS_COLLECTION_NAME):
                utility.drop_collection(MILVUS_COLLECTION_NAME)

            return Milvus(
                embedding_function=embeddings,
                collection_name=MILVUS_COLLECTION_NAME,
                connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT}
            )
        except Exception as e:
            logger.error(f"Vector store init failed: {e}")
            raise

    def get_rag_chain(self, user_email: str):
        user_profile = fetch_user_access_profile(user_email)
        filter_expr = self._build_filter_expression(user_profile)

        retriever = self.vector_store.as_retriever(
            search_kwargs={"expr": filter_expr, "k": 5}
        )

        return (
                {"context": retriever, "question": RunnablePassthrough()}
                | self.prompt_template
                | self.llm
        )

    def _build_filter_expression(self, profile: Dict) -> str:
        if not profile or not profile.get("can_access_staff_docs", False):
            return "access_level > 999"  # Block all access

        filters = []
        if profile.get("is_board_member"):
            filters.append("access_level <= 3")
        if profile.get("roles_in_departments"):
            depts = ",".join([f'"{d}"' for d in profile["roles_in_departments"]])
            filters.append(f"department IN ({depts})")

        return " OR ".join(filters) if filters else "access_level <= 1"