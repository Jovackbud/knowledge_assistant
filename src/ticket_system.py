import logging
import re
from typing import Optional
from database_utils import save_ticket
from config import TICKET_KEYWORD_MAP, TICKET_TEAMS

logger = logging.getLogger(__name__)

def suggest_ticket_team(question: str) -> str:
    """Suggest appropriate team based on question content"""
    question_lower = question.lower()
    for team, keywords in TICKET_KEYWORD_MAP.items():
        if any(re.search(rf'\b{kw}\b', question_lower) for kw in keywords):
            return team if team in TICKET_TEAMS else "General"
    return "General"

def create_ticket(user_email: str, question: str, chat_history: str, final_selected_team: str) -> bool:
    """Create new support ticket"""
    suggested_by_system = suggest_ticket_team(question)
    success = save_ticket(
        user_email=user_email,
        question=question,
        chat_history=chat_history,
        suggested_team=suggested_by_system, # The team suggested by the system
        selected_team=final_selected_team  # The team selected by the user in the UI
    )
    if success:
        logger.info(f"Ticket created for user '{user_email}', system-suggested team: '{suggested_by_system}', user-selected team: '{final_selected_team}'. Question: '{question[:50]}...'")
    return success