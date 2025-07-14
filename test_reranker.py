# test_reranker.py
import sys
import os

# ─── Project Setup ────────────────────────────────────────────────────────────
# Add project root to path so `src` is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# ─── Imports ─────────────────────────────────────────────────────────────────
from langchain_community.cross_encoders.huggingface import HuggingFaceCrossEncoder
from src.rag_processor import RAGService

# ─── Configuration ────────────────────────────────────────────────────────────
TOP_K_RETRIEVE = 10    # how many documents to pull initially
TOP_N_RERANK   = 5     # how many to keep after reranking
BGE_MODEL      = "BAAI/bge-reranker-v2-m3"
DEVICE         = "cpu"  # or "cuda" if you have a GPU

# ─── Setup ───────────────────────────────────────────────────────────────────
print("Initializing RAG Service and BGE reranker...")
rag_service = RAGService.from_config()
retriever     = rag_service.vector_store.as_retriever(search_kwargs={"k": TOP_K_RETRIEVE})
reranker      = HuggingFaceCrossEncoder(
    model_name   = BGE_MODEL,
    model_kwargs = {"device": DEVICE}
)
print("Initialization complete.\n")

# ─── Testing Function ─────────────────────────────────────────────────────────
def test_query(query: str):
    print(f"\n=== Query: {query!r} ===")
    # 1) retrieve K docs
    initial_docs = retriever.get_relevant_documents(query)
    if not initial_docs:
        print("No documents retrieved.")
        return

    # 2) build (query, doc_text) pairs
    pairs = [(query, doc.page_content) for doc in initial_docs]

    # 3) score them with the cross-encoder
    scores = reranker.score(pairs)

    # 4) attach scores to metadata + sort
    for doc, score in zip(initial_docs, scores):
        doc.metadata["relevance_score"] = float(score)
    initial_docs.sort(key=lambda d: d.metadata["relevance_score"], reverse=True)

    # 5) keep top-N
    reranked = initial_docs[:TOP_N_RERANK]

    # 6) display
    print(f"Top {len(reranked)} results after reranking:")
    for idx, doc in enumerate(reranked, start=1):
        score  = doc.metadata["relevance_score"]
        source = doc.metadata.get("source", "unknown")
        print(f"  {idx:>2}. [{score:.4f}]  {source}")

# ─── Main Execution ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        test_query("Tell me about Project Alpha")
        test_query("Tell me about Project Beta")
        test_query("What are the company's performance review policies?")
        test_query("What is the plan for Project Omega?")
    finally:
        # clean shutdown
        print("\nCleaning up resources...")
        del rag_service, retriever, reranker
        print("Done.")
