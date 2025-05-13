import re
from config import TICKET_KEYWORD_MAP, TICKET_TEAMS
from database_utils import save_ticket  # Uses the DB util


def suggest_ticket_team(question: str):
    question_lower = question.lower()
    for team_key, keywords in TICKET_KEYWORD_MAP.items():
        # Standardize team name from config key (e.g., "hr" -> "HR")
        # Or ensure TICKET_TEAMS contains the display names
        display_team_name = team_key.upper() if team_key.upper() in TICKET_TEAMS else \
            team_key.capitalize() if team_key.capitalize() in TICKET_TEAMS else \
                "General"  # Fallback if mapping is odd

        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', question_lower):
                print(f"TicketSys: Keyword '{keyword}' matched for team '{display_team_name}'")
                return display_team_name
            elif keyword in question_lower:  # Fallback to substring
                print(f"TicketSys: Substring '{keyword}' matched for team '{display_team_name}'")
                return display_team_name

    print("TicketSys: No specific keywords matched, suggesting 'General'.")
    return "General" if "General" in TICKET_TEAMS else TICKET_TEAMS[0]


def create_ticket(user_role: str, question: str, chat_history_summary: str, suggested_team: str, selected_team: str):
    print(
        f"TicketSys: Creating ticket for team '{selected_team}' (Suggested: '{suggested_team}') by role '{user_role}'")
    success = save_ticket(
        user_role=user_role,
        question=question,
        chat_history=chat_history_summary,
        suggested_team=suggested_team,
        selected_team=selected_team
    )
    return success