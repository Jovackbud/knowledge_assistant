import logging
import json
from pymilvus import utility, connections, Collection
from operator import itemgetter
from typing import Dict, Any, List, Optional

from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
# --------------------------------

from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM as Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain.memory import ConversationBufferMemory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .config import (
    MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME,
    EMBEDDING_MODEL, LLM_MODEL,
    DEFAULT_DEPARTMENT_TAG, DEFAULT_PROJECT_TAG, DEFAULT_ROLE_TAG
)
from .auth_service import fetch_user_access_profile

logger = logging.getLogger(__name__)


class EmptyRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Any]:
        return []

    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> List[Any]:
        return []


class RAGService:
    def __init__(self, embeddings, vector_store, llm):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an internal Knowledge Assistant for the organization called African Institute for Artificial Intelligence (AI4AI)."
             "Answer the question based *only* on the provided context. "
             "If the context is empty or doesn't contain the answer, state that you don't have sufficient information from the documents.\n\n"
             "Context:\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
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
    def from_config(cls, force_recreate_collection=False):
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
        except Exception as e:
            raise RuntimeError(f"Ollama LLM '{LLM_MODEL}' init failed: {e}")

        return cls(embeddings, vector_store, llm)

    @staticmethod
    def _init_vector_store(embeddings, collection_name, force_recreate):
        try:
            if force_recreate and utility.has_collection(collection_name):
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

                if not connections.has_connection("default"):
                    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)

                try:
                    milvus_coll_obj = Collection(collection_name, using="default")
                    if not milvus_coll_obj.has_index():
                        logger.info(f"RAG: Loading Milvus collection '{collection_name}' into memory.")
                        milvus_coll_obj.load()
                        logger.info(f"RAG: Collection '{collection_name}' loaded.")
                except Exception as e:
                    logger.error(f"RAG: Failed to access or load collection '{collection_name}': {e}", exc_info=True)
                    raise

            return vector_store
        except Exception as e:
            logger.error(f"RAG: Milvus vector store init failed for '{collection_name}': {e}", exc_info=True)
            raise
    
    def get_rag_chain(self, user_profile: Optional[Dict[str, Any]], chat_history: List[Dict[str, str]]):

        # 1. Create the base retriever and the reranking compressor
        base_retriever = self.vector_store.as_retriever(
            search_kwargs={"param": {"expr": self._build_filter_expression(user_profile)}, "k": 10}
        )
        compressor = FlashrankRerank(top_n=3)
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=base_retriever
        )

        # 2. Re-insert the missing format_docs helper function
        def format_docs(docs: List[Any]) -> str:
            if not docs:
                return "No relevant documents found based on your query and access rights."
            return "\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content'))
        
        # 3. Create the memory object from the chat history
        message_history = InMemoryChatMessageHistory()
        for msg in chat_history:
            if msg.get("role") == "user":
                message_history.add_user_message(msg.get("content", ""))
            elif msg.get("role") == "assistant":
                message_history.add_ai_message(msg.get("content", ""))
        
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            chat_memory=message_history,
            return_messages=True
        )

        # 4. Construct the final RAG chain
        rag_chain = (
            RunnablePassthrough.assign(
                context=(lambda x: format_docs(compression_retriever.invoke(x["question"])))
            ).assign(
                chat_history=(lambda x: memory.load_memory_variables(x).get("chat_history", []))
            )
            | self.prompt_template
            | self.llm
            | StrOutputParser()
        )

        # We return the retriever and the chain separately
        return rag_chain, compression_retriever

    def _build_filter_expression(self, profile: Dict[str, Any]) -> str:
        user_level = profile.get("user_hierarchy_level", -1)
        user_depts = profile.get("departments", [])
        user_projs = profile.get("projects_membership", [])
        user_contextual_roles = profile.get("contextual_roles", {})

        hierarchy_filter = f"hierarchy_level_required <= {user_level}"

        if not user_depts:
            department_filter = f'department_tag == "{DEFAULT_DEPARTMENT_TAG}"'
        else:
            depts_json_array = json.dumps(user_depts)
            department_filter = f'(department_tag == "{DEFAULT_DEPARTMENT_TAG}" OR department_tag IN {depts_json_array})'

        if not user_projs:
            project_filter = f'project_tag == "{DEFAULT_PROJECT_TAG}"'
        else:
            projs_json_array = json.dumps(user_projs)
            project_filter = f'(project_tag == "{DEFAULT_PROJECT_TAG}" OR project_tag IN {projs_json_array})'

        role_conditions = [f'role_tag_required == "{DEFAULT_ROLE_TAG}"']

        for context_tag, roles_in_context in user_contextual_roles.items():
            if not roles_in_context: continue

            roles_json_array = json.dumps(roles_in_context)
            project_role_condition = f'(project_tag == "{context_tag}" AND role_tag_required IN {roles_json_array})'
            department_role_condition = f'(department_tag == "{context_tag}" AND role_tag_required IN {roles_json_array})'
            role_conditions.append(f"({project_role_condition} OR {department_role_condition})")

        if len(role_conditions) == 1:
            role_filter = role_conditions[0]
        else:
            role_filter = f"({' OR '.join(f'({cond})' for cond in role_conditions)})"

        final_filter = f"({hierarchy_filter}) AND ({department_filter}) AND ({project_filter}) AND ({role_filter})"
        return final_filter