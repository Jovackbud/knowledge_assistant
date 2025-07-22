import logging
from typing import Optional, Dict

# Use the new descriptions from config
from .config import TICKET_TEAMS, TICKET_TEAM_DESCRIPTIONS
from .services import shared_services

# Import the necessary AI and math libraries
from langchain_huggingface import HuggingFaceEmbeddings
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class TeamSuggester:
    """
    An AI-powered class to suggest the most relevant support team for a given question.
    It works by converting team descriptions and the user's question into numerical
    representations (embeddings) and finding the best match based on semantic similarity.
    """
    def __init__(self):
        logger.info("Initializing AI Team Suggester...")
        try:
            # We initialize the model here. This happens only ONCE when the app starts.
            self.embedding_model = shared_services.embedding_model
            
            # Prepare the team descriptions and their corresponding embeddings
            self.team_names = list(TICKET_TEAM_DESCRIPTIONS.keys())
            self.team_descriptions = list(TICKET_TEAM_DESCRIPTIONS.values())
            
            # This is the key optimization: we pre-calculate the embeddings for our
            # team descriptions so we don't have to do it on every request.
            logger.info(f"Pre-calculating embeddings for {len(self.team_names)} teams...")
            self.team_embeddings = self.embedding_model.embed_documents(self.team_descriptions)
            logger.info("AI Team Suggester initialized successfully.")
            
        except Exception as e:
            logger.error(f"Failed to initialize TeamSuggester: {e}", exc_info=True)
            # If init fails, we'll fall back gracefully
            self.embedding_model = None
            self.team_embeddings = None

    def suggest(self, question: str) -> str:
        """
        Suggests the most appropriate team based on the question's content.
        """
        # Graceful fallback if initialization failed
        if not self.embedding_model or not self.team_embeddings:
            logger.warning("TeamSuggester not initialized. Falling back to 'General'.")
            return "General"

        try:
            # 1. Embed the user's question in real-time. This is very fast.
            question_embedding = self.embedding_model.embed_query(question)

            # 2. Calculate the similarity between the question and all team descriptions.
            # The result is a list of scores, e.g., [[0.1, 0.8, 0.3, 0.2]]
            similarities = cosine_similarity([question_embedding], self.team_embeddings)[0]

            # 3. Find the highest score and the corresponding team.
            # We set a minimum threshold to avoid nonsensical suggestions for vague questions.
            min_confidence_threshold = 0.3
            max_score = -1
            best_team_index = -1

            for i, score in enumerate(similarities):
                if score > max_score:
                    max_score = score
                    best_team_index = i

            if max_score >= min_confidence_threshold:
                suggested_team = self.team_names[best_team_index]
                logger.info(f"Team suggestion for question '{question[:30]}...': '{suggested_team}' with score {max_score:.2f}")
                return suggested_team
            else:
                # If no team is a confident match, fall back to General.
                logger.info(f"No team met confidence threshold for question '{question[:30]}...'. Max score: {max_score:.2f}. Defaulting to General.")
                return "General"

        except Exception as e:
            logger.error(f"Error during team suggestion: {e}", exc_info=True)
            return "General"

# Create a single, global instance of the suggester.
# This ensures the model is loaded only once when the application starts.
team_suggester = TeamSuggester()

# --- Main Functions (unchanged logic, just call the new class) ---

def suggest_ticket_team(question: str) -> str:
    """Suggest appropriate team based on question content using the AI suggester."""
    return team_suggester.suggest(question)

def create_ticket(user_email: str, question: str, chat_history: str, final_selected_team: str) -> Optional[int]:
    """Create new support ticket"""
    from .database_utils import save_ticket  # Local import to avoid circular dependency at module level if any

    suggested_by_system = suggest_ticket_team(question)
    ticket_id = save_ticket(
        user_email=user_email,
        question=question,
        chat_history=chat_history,
        suggested_team=suggested_by_system,
        selected_team=final_selected_team
    )
    if ticket_id:
        logger.info(f"Ticket created for user '{user_email}', system-suggested team: '{suggested_by_system}', user-selected team: '{final_selected_team}'. Question: '{question[:50]}...'")
    return ticket_id