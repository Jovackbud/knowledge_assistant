import logging
import json
import re
from pathlib import Path
from operator import itemgetter
from typing import Dict, Any, List, Optional

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import Pinecone as PineconeVectorStore
from flashrank import Ranker, RerankRequest

from .utils import sanitize_tag
from .services import shared_services

from .config import (
    UserProfile,
    PINECONE_INDEX_NAME, EMBEDDING_MODEL, RERANKER_MODEL, LLM_GENERATION_MODEL, USE_RERANKER,
    DEFAULT_DEPARTMENT_TAG, DEFAULT_PROJECT_TAG, DEFAULT_ROLE_TAG, RERANKER_SCORE_THRESHOLD  
)

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, embeddings: HuggingFaceEmbeddings, vector_store: PineconeVectorStore, llm: ChatGoogleGenerativeAI):
        self.embeddings = shared_services.embedding_model
        self.vector_store = vector_store
        self.llm = llm
        # We define a cache path on the persistent disk
        cache_path = Path("/usr/src/app/database/cache")
        cache_path.mkdir(exist_ok=True) # Ensure the directory exists
        self.reranker = None
        if USE_RERANKER:
            try:
                # We define a cache path on the persistent disk
                cache_path = Path("/usr/src/app/database/cache")
                cache_path.mkdir(exist_ok=True) # Ensure the directory exists
                self.reranker = Ranker(model_name=RERANKER_MODEL, cache_dir=str(cache_path))
                logger.info(f"RAG: Reranker '{RERANKER_MODEL}' initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Reranker, it will be disabled: {e}", exc_info=True)
                self.reranker = None
        else:
            logger.warning("RAG: Reranker is disabled via configuration.")

        try:
            prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
            system_prompt_path = prompts_dir / "rag_system_prompt.md"
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_prompt_content = f.read()
            
            rephrase_prompt_path = prompts_dir / "rephrase_question_prompt.md"
            with open(rephrase_prompt_path, "r", encoding="utf-8") as f:
                rephrase_prompt_content = f.read()
            
            self.rephrase_prompt = ChatPromptTemplate.from_template(rephrase_prompt_content)
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt_content),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}")
            ])
            logger.info("RAG: All prompts loaded successfully.")
        except FileNotFoundError as e:
            logger.error(f"FATAL: Prompt file not found: {e}. Please ensure it exists.")
            raise

    @classmethod
    def from_config(cls):
        """Initializes the RAGService from configuration and environment variables."""
        logger.info(f"RAGService Init: Embedding='{EMBEDDING_MODEL}', Pinecone Index='{PINECONE_INDEX_NAME}'")
        try:
            llm = ChatGoogleGenerativeAI(model=LLM_GENERATION_MODEL)
            logger.info("RAG: Successfully initialized Google Generative AI LLM.")
        except Exception as e:
            logger.error("RAG: Failed to initialize Google Generative AI LLM.", exc_info=True)
            raise RuntimeError(f"Google Generative AI LLM init failed: {e}")

        embeddings = shared_services.embedding_model
        vector_store = cls._init_vector_store(embeddings, PINECONE_INDEX_NAME)
        return cls(embeddings, vector_store, llm)

    @staticmethod
    def _init_vector_store(embeddings: HuggingFaceEmbeddings, index_name: str) -> PineconeVectorStore:
        """Initializes the Pinecone vector store."""
        logger.info(f"RAG: Connecting to Pinecone index: '{index_name}'.")
        try:
            vector_store = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings
            )
            logger.info("RAG: Pinecone vector store connected successfully.")
            return vector_store
        except Exception as e:
            logger.error(f"RAG: Pinecone vector store init failed for index '{index_name}': {e}", exc_info=True)
            raise

    def get_rag_chain(self, user_profile: Optional[UserProfile], chat_history: List[Dict[str, str]]):
        """
        Constructs a complete, history-aware, and permission-filtered RAG chain.
        """
        base_retriever = self.vector_store.as_retriever(
            search_kwargs={'filter': self._build_filter_expression(user_profile), 'k': 10}
        )

        def rerank_and_filter_documents(docs: List[Any], question: str) -> List[Any]:
            if not docs:
                return []
            
            # If reranker is disabled, just return the top 3 documents from the initial retrieval
            if not self.reranker:
                logger.info("Reranker is disabled, returning top 3 retrieved documents.")
                return docs[:3]

            if not all(hasattr(doc, 'page_content') and hasattr(doc, 'metadata') for doc in docs):
                logger.warning("Retrieved documents list contains invalid objects. Skipping reranking.")
                return []

            passages = [{"id": i, "text": doc.page_content, "meta": doc.metadata} for i, doc in enumerate(docs)]
            request = RerankRequest(query=question, passages=passages)
            reranked_results = self.reranker.rerank(request)
            
            # Get the original document objects based on the reranked IDs
            original_docs_map = {i: doc for i, doc in enumerate(docs)}
            
            high_confidence_results = [r for r in reranked_results if r.get("score", 0) >= RERANKER_SCORE_THRESHOLD]
            
            if high_confidence_results:
                final_results = high_confidence_results[:3]
            elif reranked_results:
                logger.warning(f"No docs met rerank threshold {RERANKER_SCORE_THRESHOLD}. Using best single doc.")
                final_results = reranked_results[:1]
            else:
                final_results = []
            
            # Map back to the original LangChain Document objects
            final_docs = [original_docs_map[d["id"]] for d in final_results]
            logger.info(f"Reranking complete. Initial: {len(docs)}, Final: {len(final_docs)}")
            return final_docs

        def format_docs(docs: List[Any]) -> str:
            if not docs:
                return "No relevant documents were found based on your query and access rights after filtering for relevance."
            return "\n\n---\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content'))

        rephrase_chain = self.rephrase_prompt | self.llm | StrOutputParser()

        def get_rephrased_question(input_dict: Dict[str, Any]):
            if input_dict.get("chat_history"):
                return rephrase_chain.invoke(input_dict)
            return input_dict["question"]

        conversational_rag_chain = (
            RunnablePassthrough.assign(rephrased_question=RunnableLambda(get_rephrased_question))
            | RunnablePassthrough.assign(
                docs=RunnableLambda(
                    lambda x: rerank_and_filter_documents(
                        docs=base_retriever.invoke(x["rephrased_question"]),
                        question=x["rephrased_question"]
                    )
                ).with_config(run_name="retriever_and_reranker_step")
            )
            | RunnablePassthrough.assign(context=lambda x: format_docs(x["docs"]))
            | {
                "context": itemgetter("context"),
                "question": itemgetter("question"),
                "chat_history": itemgetter("chat_history"),
                "docs": itemgetter("docs")
            }
            | self.prompt_template
            | self.llm
        )
        return conversational_rag_chain
    
    def _build_filter_expression(self, profile: Dict[str, Any]) -> Dict:
        """
        Builds a metadata filter expression for Pinecone based on user profile.
        """
        user_level = profile.get("user_hierarchy_level", -1)
        user_depts_sanitized = [sanitize_tag(d) for d in profile.get("departments", [])]
        user_projs_sanitized = [sanitize_tag(p) for p in profile.get("projects_membership", [])]
        sanitized_contextual_roles = {sanitize_tag(k): v for k, v in profile.get("contextual_roles", {}).items()}

        default_dept_tag = sanitize_tag(DEFAULT_DEPARTMENT_TAG)
        all_dept_roles = {DEFAULT_ROLE_TAG, *sanitized_contextual_roles.get(default_dept_tag, [])}
        for dept in user_depts_sanitized: all_dept_roles.update(sanitized_contextual_roles.get(dept, []))

        default_proj_tag = sanitize_tag(DEFAULT_PROJECT_TAG)
        all_proj_roles = {DEFAULT_ROLE_TAG, *sanitized_contextual_roles.get(default_proj_tag, [])}
        for proj in user_projs_sanitized: all_proj_roles.update(sanitized_contextual_roles.get(proj, []))
        
        final_filter = {
            "$and": [
                {"hierarchy_level_required": {"$lte": user_level}},
                {"$or": [
                    {"$and": [
                        {"department_tag": {"$in": user_depts_sanitized + [default_dept_tag]}},
                        {"role_tag_required": {"$in": list(all_dept_roles)}}
                    ]},
                    {"$and": [
                        {"project_tag": {"$in": user_projs_sanitized + [default_proj_tag]}},
                        {"role_tag_required": {"$in": list(all_proj_roles)}}
                    ]}
                ]}
            ]
        }
        logger.info(f"Built Pinecone filter for {profile.get('user_email')}: {json.dumps(final_filter)}")
        return final_filter