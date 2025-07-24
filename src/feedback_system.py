import logging
from .database_utils import save_feedback

from .config import FEEDBACK_HELPFUL, FEEDBACK_NOT_HELPFUL

logger = logging.getLogger(__name__)

def record_feedback(user_email, question, answer, rating):
    """Records user feedback with validation."""
    # ADD THIS VALIDATION BLOCK
    if rating not in [FEEDBACK_HELPFUL, FEEDBACK_NOT_HELPFUL]:
        logger.error(f"Invalid feedback rating received: '{rating}'. User: '{user_email}'. Aborting.")
        return False

    logger.info(f"Recording feedback: {rating} for question: '{question[:50]}...' by user '{user_email}'")
    success = save_feedback(
        user_email=user_email,
        question=question,
        answer=answer,
        rating=rating
    )
    if not success:
        # The log in save_feedback is already detailed, this is a high-level confirmation
        logger.warning(f"Call to save_feedback for user '{user_email}' returned False.")
    return success