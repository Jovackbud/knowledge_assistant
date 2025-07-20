
import logging
import json
import os
import re
from pathlib import Path
from operator import itemgetter
from typing import Dict, Any, List, Optional

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.memory import ConversationBufferMemory

# --- New, harmonized imports for our managed services architecture ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import Pinecone as PineconeVectorStore
from flashrank import Ranker, RerankRequest

# --- Local Project Imports ---
from .config import (
    PINECONE_INDEX_NAME, EMBEDDING_MODEL, RERANKER_MODEL, LLM_GENERATION_MODEL,
    DEFAULT_DEPARTMENT_TAG, DEFAULT_PROJECT_TAG, DEFAULT_ROLE_TAG, RERANKER_SCORE_THRESHOLD  
)

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, embeddings: HuggingFaceEmbeddings, vector_store: PineconeVectorStore, llm: ChatGoogleGenerativeAI):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm

        # --- Initialize the reranker once ---
        logger.info(f"RAG: Initializing reranker model: '{RERANKER_MODEL}'")
        self.reranker = Ranker(model_name=RERANKER_MODEL, cache_dir="/tmp/flashrank_cache")
        logger.info("RAG: Reranker initialized successfully.")

        # --- Load prompt from external file ---
        try:
            prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
            system_prompt_path = prompts_dir / "rag_system_prompt.md"
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_prompt_content = f.read()
            logger.info(f"Successfully loaded system prompt from {system_prompt_path}")

            # --- NEW: Load the rephrasing prompt ---
            rephrase_prompt_path = prompts_dir / "rephrase_question_prompt.md"
            with open(rephrase_prompt_path, "r", encoding="utf-8") as f:
                rephrase_prompt_content = f.read()
            self.rephrase_prompt = ChatPromptTemplate.from_template(rephrase_prompt_content)
            logger.info(f"Successfully loaded rephrasing prompt from {rephrase_prompt_path}")

        except FileNotFoundError:
            logger.error(f"FATAL: System prompt file not found at {system_prompt_path}. Please ensure it exists.")
            raise

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt_content),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

    @classmethod
    def from_config(cls):
        """Initializes the RAGService from configuration and environment variables."""
        logger.info(f"RAGService Init: Embedding='{EMBEDDING_MODEL}', Pinecone Index='{PINECONE_INDEX_NAME}'")

        try:
            # Initialize connection to Google Gemini via API Key
            llm = ChatGoogleGenerativeAI(
                model=LLM_GENERATION_MODEL
            )
            logger.info("RAG: Successfully initialized connection via Google Generative AI API (Gemini).")
        except Exception as e:
            logger.error(
                "RAG: Failed to initialize Google Generative AI LLM. "
                "Ensure your GOOGLE_API_KEY environment variable is set correctly.",
                exc_info=True
            )
            raise RuntimeError(f"Google Generative AI LLM init failed: {e}")

        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vector_store = cls._init_vector_store(embeddings, PINECONE_INDEX_NAME)

        return cls(embeddings, vector_store, llm)

    @staticmethod
    def _init_vector_store(embeddings: HuggingFaceEmbeddings, index_name: str) -> PineconeVectorStore:
        """Initializes the Pinecone vector store."""
        logger.info(f"RAG: Connecting to Pinecone index: '{index_name}'.")
        try:
            # The Pinecone library will automatically use PINECONE_API_KEY and PINECONE_ENVIRONMENT from .env
            vector_store = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings
            )
            logger.info("RAG: Pinecone vector store connected successfully.")
            return vector_store
        except Exception as e:
            logger.error(f"RAG: Pinecone vector store init failed for index '{index_name}': {e}", exc_info=True)
            raise

    def get_rag_chain(self, user_profile: Optional[Dict[str, Any]], chat_history: List[Dict[str, str]]):
        """
        Constructs a complete, history-aware RAG chain.
        This version first rephrases the question based on history, then retrieves, reranks, and finally answers.
        """

        # 2. Define the base retriever that applies a user-specific permission filter.
        base_retriever = self.vector_store.as_retriever(
            search_kwargs={'filter': self._build_filter_expression(user_profile), 'k': 10}
        )

        # 3. Define the custom reranking and filtering function.
        def rerank_and_filter_documents(inputs: Dict[str, Any]) -> List[Any]:
            """
            Reranks retrieved documents with a "best effort" fallback.
            It first tries to filter by a high-confidence score, but if that fails,
            it returns the single top-ranked document to avoid silent failures.
            """
            question = inputs["question"]
            retrieved_docs = inputs["docs"]
            
            if not retrieved_docs:
                return []

            passages = [{
                "id": i, "text": doc.page_content,
                "meta": {"source": doc.metadata.get("source", "Unknown"), **doc.metadata}
            } for i, doc in enumerate(retrieved_docs)]

            request = RerankRequest(query=question, passages=passages)
            reranked_results = self.reranker.rerank(request)

            # 1. First, try to get documents that meet our high-confidence threshold.
            high_confidence_docs = [r for r in reranked_results if r.get("score", 0) >= RERANKER_SCORE_THRESHOLD]
            final_docs_data = []
            top_n = 3

            # 2. Check the results.
            if high_confidence_docs:
                # If we have high-confidence results, use them (up to top_n).
                final_docs_data = high_confidence_docs[:top_n]
            elif reranked_results:
            # If we have NO high-confidence results, but we do have *some* results,
            # implement the "best effort" fallback: take the single best document.
                logger.warning(
                    f"No documents met the threshold of {RERANKER_SCORE_THRESHOLD}. "
                    "Falling back to the single best document to avoid a silent failure."
                )
                final_docs_data = reranked_results[:1]

            # 3. Re-create LangChain Document objects to pass down the chain.
            if final_docs_data:
                final_docs = [type(retrieved_docs[0])(page_content=d["text"], metadata=d["meta"]) for d in final_docs_data]
            else:
                final_docs = []
            
            logger.info(f"Reranking complete. Initial: {len(retrieved_docs)} docs, "
                        f"Final: {len(final_docs)} docs. (Used threshold: {RERANKER_SCORE_THRESHOLD})")
            return final_docs

        # 4. Define a helper to format docs for the LLM, including source citations.
        def format_docs(docs: List[Any]) -> str:
            """
            Formats the retrieved documents into a single, clean block of text for the LLM.
            The source filenames are not included here, as the new prompt instructs the LLM
            to create a separate "Sources" section at the end of its response.
            """
            if not docs:
                return "No relevant documents were found based on your query and access rights after filtering for relevance."
            
            # Join the page content of all retrieved documents with a clear separator.
            # This gives the LLM a consolidated context to work from.
            return "\n\n---\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content'))

        # 5. Create the memory object from chat history.
        message_history = InMemoryChatMessageHistory()
        for msg in chat_history:
            if msg.get("role") == "user": message_history.add_user_message(msg.get("content", ""))
            elif msg.get("role") == "assistant": message_history.add_ai_message(msg.get("content", ""))
        
        memory = ConversationBufferMemory(
            memory_key="chat_history", chat_memory=message_history, return_messages=True
        )

        # 6. Construct the final RAG chain using LCEL.
        retrieval_and_rerank_chain = (
            {
                "docs": itemgetter("question") | base_retriever,
                "question": itemgetter("question")
            }
            | RunnableLambda(rerank_and_filter_documents)
        )

        # This chain prepares all the inputs needed for the final prompt
        context_chain = {
            "context": lambda x: format_docs(x["docs"]),
            "question": itemgetter("question"),
            "chat_history": lambda x: memory.load_memory_variables({"question": x["question"]}).get("chat_history", [])
        }

        # The final chain that will be streamed. Notice there is no StrOutputParser().
        # We want the raw streaming chunks from the LLM.
        answer_chain = (
            context_chain
            | self.prompt_template
            | self.llm
        )

        # We return the components separately to be handled by the API endpoint
        return retrieval_and_rerank_chain, answer_chain
    
    def _sanitize_tag(self, tag: str) -> str:
        """
        Normalizes a tag by removing all non-alphanumeric characters
        and converting it to uppercase.
        e.g., "Project-Beta" -> "PROJECTBETA"
        """
        if not isinstance(tag, str):
            return ""
        return re.sub(r'[^a-zA-Z0-9]', '', tag).upper()
    
    def _build_filter_expression(self, profile: Dict[str, Any]) -> Dict:
        """
        Builds a metadata filter expression for Pinecone based on user profile.
        This version sanitizes all tags to be purely alphanumeric and uppercase
        to ensure robust, case-insensitive, and character-insensitive matching.
        """
        user_level = profile.get("user_hierarchy_level", -1)
        user_depts = profile.get("departments", [])
        user_projs = profile.get("projects_membership", [])
        user_contextual_roles = profile.get("contextual_roles", {})

        # --- Sanitize all tags from the user's profile for comparison ---
        user_depts_sanitized = [self._sanitize_tag(d) for d in user_depts]
        user_projs_sanitized = [self._sanitize_tag(p) for p in user_projs]
        
        # Also sanitize the keys in the contextual roles dictionary
        sanitized_contextual_roles = {self._sanitize_tag(k): v for k, v in user_contextual_roles.items()}

        # --- Base condition: User's hierarchy level must be sufficient ---
        hierarchy_filter = {"hierarchy_level_required": {"$lte": user_level}}

        # --- Gather all roles based on SANITIZED tags ---
        # Note: DEFAULT_DEPARTMENT_TAG and DEFAULT_PROJECT_TAG are already clean
        all_dept_roles = set(sanitized_contextual_roles.get(self._sanitize_tag(DEFAULT_DEPARTMENT_TAG), []))
        for dept in user_depts_sanitized:
            all_dept_roles.update(sanitized_contextual_roles.get(dept, []))
        all_dept_roles.add(DEFAULT_ROLE_TAG)

        all_proj_roles = set(sanitized_contextual_roles.get(self._sanitize_tag(DEFAULT_PROJECT_TAG), []))
        for proj in user_projs_sanitized:
            all_proj_roles.update(sanitized_contextual_roles.get(proj, []))
        all_proj_roles.add(DEFAULT_ROLE_TAG)
        
        # Build the final logic using the sanitized lists.
        # We assume that the tags in Pinecone's metadata have ALREADY been sanitized
        # during the document update process.
        final_filter = {
            "$and": [
                hierarchy_filter,
                {
                    "$or": [
                        {
                            "$and": [
                                {"department_tag": {"$in": user_depts_sanitized + [self._sanitize_tag(DEFAULT_DEPARTMENT_TAG)]}},
                                {"role_tag_required": {"$in": list(all_dept_roles)}}
                            ]
                        },
                        {
                            "$and": [
                                {"project_tag": {"$in": user_projs_sanitized + [self._sanitize_tag(DEFAULT_PROJECT_TAG)]}},
                                {"role_tag_required": {"$in": list(all_proj_roles)}}
                            ]
                        }
                    ]
                }
            ]
        }
        logger.info(f"Built Pinecone filter for {profile.get('user_email')}: {json.dumps(final_filter)}")
        return final_filter