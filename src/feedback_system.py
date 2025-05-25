import logging
from database_utils import save_feedback

logger = logging.getLogger(__name__)

def record_feedback(user_email, question, answer, rating):
    """Records user feedback."""
    logger.info(f"Recording feedback: {rating} for question: '{question[:50]}...' by user '{user_email}'")
    success = save_feedback(
        user_email=user_email,
        question=question,
        answer=answer,
        rating=rating
    )
    if not success:
        logger.warning("Failed to save feedback to the database.")
    return success