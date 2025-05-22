import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"  # Force legacy Keras
os.environ["KERAS_3"] = "0"

import logging
import json
from pymilvus import utility, connections, Collection
from typing import Dict, Any, List
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever

from config import (
    MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME,
    EMBEDDING_MODEL, LLM_MODEL,
    DEFAULT_DEPARTMENT_TAG, DEFAULT_PROJECT_TAG, DEFAULT_ROLE_TAG
)
from auth_service import fetch_user_access_profile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EmptyRetriever(BaseRetriever):  # type: ignore
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Any]:  # type: ignore[override]
        return []

    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> List[Any]:  # type: ignore[override]
        return []


class RAGService:
    def __init__(self, embeddings, vector_store, llm):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_template(
            "You are a Company Knowledge Assistant. Answer the question based *only* on the provided context. "
            "If the context is empty or doesn't contain the answer, state that you don't have sufficient information from the documents.\n\n"
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer:"
        )
        self._ensure_milvus_connection()

    def _ensure_milvus_connection(self):
        try:
            if not connections.has_connection("default"):
                logger.info(f"RAG: Attempting Milvus connection {MILVUS_HOST}:{MILVUS_PORT}")
                connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
                logger.info("RAG: Milvus connected.")
        except Exception as e:
            logger.error(f"RAG: Milvus connection failed: {e}", exc_info=True)
            raise ConnectionError(f"RAG Service: Milvus connection failed: {e}")

    @classmethod
    def from_config(cls, force_recreate_collection=False):  # Not used by RAG service itself but for consistency
        logger.info(
            f"RAGService Init: Embedding='{EMBEDDING_MODEL}', LLM='{LLM_MODEL}', Collection='{MILVUS_COLLECTION_NAME}'")
        try:
            if not connections.has_connection("default"):
                connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
        except Exception as e:
            raise ConnectionError(f"RAGService.from_config: Milvus connection failed: {e}")

        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vector_store = cls._init_vector_store(embeddings, MILVUS_COLLECTION_NAME, force_recreate_collection)

        try:
            llm = Ollama(model=LLM_MODEL)
            # Optional: llm.invoke("Hi") to test connection
        except Exception as e:
            raise RuntimeError(f"Ollama LLM '{LLM_MODEL}' init failed: {e}")

        return cls(embeddings, vector_store, llm)

    @staticmethod
    def _init_vector_store(embeddings, collection_name, force_recreate):
        # Document updater is responsible for creating collection with schema.
        # Here, we just connect to it. Langchain's Milvus might try to create if not exists.
        try:
            if force_recreate and utility.has_collection(collection_name):  # Should not be used by RAG normally
                logger.warning(f"RAG: Force recreate for '{collection_name}' (not typical for RAG service).")
                utility.drop_collection(collection_name)

            vector_store = Milvus(
                embedding_function=embeddings,
                collection_name=collection_name,
                connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
                auto_id=True,
            )
            logger.info(f"RAG: Milvus vector store connected for collection: '{collection_name}'.")

            if utility.has_collection(collection_name):
                logger.info(f"RAG: Checking Milvus collection '{collection_name}'...")

                connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)

                if not connections.has_connection("default"):
                    raise ConnectionError("Milvus connection failed: No active connection found after connect().")

                try:
                    milvus_coll_obj = Collection(collection_name, using="default")
                    if not milvus_coll_obj.has_index():
                        logger.info(f"RAG: Loading Milvus collection '{collection_name}' into memory.")
                        milvus_coll_obj.load()
                        logger.info(f"RAG: Collection '{collection_name}' loaded.")
                except Exception as e:
                    logger.error(f"RAG: Failed to access or load collection '{collection_name}': {e}", exc_info=True)
                    raise

            # else: Collection should be created by document_updater.py
            return vector_store
        except Exception as e:
            logger.error(f"RAG: Milvus vector store init failed for '{collection_name}': {e}", exc_info=True)
            raise

    def get_rag_chain(self, user_email: str):
        user_profile = fetch_user_access_profile(user_email)

        if not user_profile:
            logger.warning(f"No user profile for {user_email}. Using empty retriever.")
            retriever = EmptyRetriever()
        else:
            filter_expr = self._build_filter_expression(user_profile)
            logger.info(f"User '{user_email}' filter expression: {filter_expr}")
            retriever = self.vector_store.as_retriever(
                search_kwargs={"param": {"expr": filter_expr}, "k": 3}  # k = num docs
            )

        def format_docs(docs: List[Any]) -> str:
            if not docs:
                return "No relevant documents found based on your query and access rights."
            return "\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content'))

        return (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | self.prompt_template
                | self.llm
                | StrOutputParser()
        )

    def _build_filter_expression(self, profile: Dict[str, Any]) -> str:
        user_level = profile.get("user_hierarchy_level", -1)  # Default to -1 (no access) if missing
        user_depts = profile.get("departments", [])
        user_projs = profile.get("projects_membership", [])
        user_contextual_roles = profile.get("contextual_roles", {})  # Dict: {"CONTEXT_TAG": ["ROLE_A", "ROLE_B"]}

        # 1. Hierarchy filter
        hierarchy_filter = f"hierarchy_level_required <= {user_level}"

        # 2. Department filter
        if not user_depts:  # User has no specific department memberships
            department_filter = f'department_tag == \"{DEFAULT_DEPARTMENT_TAG}\"'
        else:
            depts_json_array = json.dumps(user_depts)  # Creates '["DEPT1", "DEPT2"]'
            department_filter = f'(department_tag == "{DEFAULT_DEPARTMENT_TAG}" OR department_tag IN {depts_json_array})'

        # 3. Project filter
        if not user_projs:
            project_filter = f'project_tag == "{DEFAULT_PROJECT_TAG}"'
        else:
            projs_json_array = json.dumps(user_projs)
            project_filter = f'(project_tag == "{DEFAULT_PROJECT_TAG}" OR project_tag IN {projs_json_array})'

        # 4. Role filter (most complex)
        # Document is accessible if (its role_tag is default) OR (user has the required role in the doc's context)
        role_conditions = [f'role_tag_required == "{DEFAULT_ROLE_TAG}"']  # Base case: doc needs no specific role

        # Iterate through user's contextual roles to build specific grant conditions
        # Example: user_contextual_roles = {"PROJECT_ALPHA": ["LEAD_ROLE"], "HR_DEPARTMENT": ["REVIEWER_ROLE"]}
        for context_tag, roles_in_context in user_contextual_roles.items():
            if not roles_in_context: continue  # Skip if no roles for this context

            roles_json_array = json.dumps(roles_in_context)  # e.g., '["LEAD_ROLE"]'

            # Condition: (doc's project_tag matches this context_tag AND doc's role_tag is one of user's roles for this project)
            # It's important that context_tag (from user profile) matches project_tag or department_tag from config.
            # We assume context_tag in user_profile can be either a project name or a department name.
            project_role_condition = f'(project_tag == "{context_tag}" AND role_tag_required IN {roles_json_array})'
            department_role_condition = f'(department_tag == "{context_tag}" AND role_tag_required IN {roles_json_array})'

            # User has role X in context Y. Doc needs role X and is in context Y (either as proj or dept).
            role_conditions.append(f"({project_role_condition} OR {department_role_condition})")

        if len(role_conditions) == 1:  # Only the default role condition
            role_filter = role_conditions[0]
        else:  # Multiple conditions (default OR specific grants)
            role_filter = f"({' OR '.join(f'({cond})' for cond in role_conditions)})"

        # Combine all major filters with AND
        final_filter = f"({hierarchy_filter}) AND ({department_filter}) AND ({project_filter}) AND ({role_filter})"

        return final_filter