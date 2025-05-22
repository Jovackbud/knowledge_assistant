import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"  # Force legacy Keras
os.environ["KERAS_3"] = "0"

import re
from typing import Optional
from database_utils import save_ticket
from config import TICKET_KEYWORD_MAP, TICKET_TEAMS

def suggest_ticket_team(question: str) -> str:
    """Suggest appropriate team based on question content"""
    question_lower = question.lower()
    for team, keywords in TICKET_KEYWORD_MAP.items():
        if any(re.search(rf'\b{kw}\b', question_lower) for kw in keywords):
            return team.capitalize() if team.capitalize() in TICKET_TEAMS else "General"
    return "General"

def create_ticket(user_email: str, question: str, chat_history: str) -> bool:
    """Create new support ticket"""
    suggested = suggest_ticket_team(question)
    return save_ticket(
        user_email=user_email,
        question=question,
        chat_history=chat_history,
        suggested_team=suggested,
        selected_team=suggested
    )