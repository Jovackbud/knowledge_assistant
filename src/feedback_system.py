import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"  # Force legacy Keras
os.environ["KERAS_3"] = "0"

from database_utils import save_feedback

def record_feedback(user_email, question, answer, rating):
    """Records user feedback."""
    print(f"Recording feedback: {rating} for question: '{question[:50]}...' by role '{user_email}'")
    success = save_feedback(
        user_email=user_email,
        question=question,
        answer=answer,
        rating=rating
    )
    if not success:
        print("Warning: Failed to save feedback to the database.")
    return success