import sqlite3
import json
import logging
from typing import Dict, Optional, List, Any
from .config import (
    UserProfile,
    TICKET_DB_PATH, FEEDBACK_DB_PATH, AUTH_DB_PATH,
    DB_PARENT_DIR, DEFAULT_HIERARCHY_LEVEL
)

logger = logging.getLogger(__name__)


def init_all_databases():
    try:
        DB_PARENT_DIR.mkdir(parents=True, exist_ok=True)
        init_auth_db()
        init_ticket_db()
        init_feedback_db()
        logger.info("✅ All databases initialized/verified successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise


def init_auth_db():
    """
    UserAccessProfile stores:
    - user_hierarchy_level (int)
    - departments (JSON list of department tags)
    - projects_membership (JSON list of project tags)
    - contextual_roles (JSON dict: {"context_tag": ["ROLE_1", "ROLE_2"]})
      Context_tag can be a project_tag or a department_tag.
    """
    with sqlite3.connect(AUTH_DB_PATH, timeout=10, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS UserAccessProfile (
                user_email TEXT PRIMARY KEY,
                user_hierarchy_level INTEGER DEFAULT 0 NOT NULL,
                departments TEXT DEFAULT '[]' NOT NULL,
                projects_membership TEXT DEFAULT '[]' NOT NULL,
                contextual_roles TEXT DEFAULT '{}' NOT NULL
            )
        ''')
        conn.commit()
        logger.info(f"Auth DB initialized at {AUTH_DB_PATH}")


def init_ticket_db():
    with sqlite3.connect(TICKET_DB_PATH, timeout=10, check_same_thread=False) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_email TEXT NOT NULL,
                question TEXT NOT NULL,
                chat_history TEXT NOT NULL,
                suggested_team TEXT NOT NULL,
                selected_team TEXT NOT NULL,
                status TEXT DEFAULT 'Open',
                FOREIGN KEY (user_email) REFERENCES UserAccessProfile(user_email) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        logger.info(f"Ticket DB initialized at {TICKET_DB_PATH}")


def init_feedback_db():
    with sqlite3.connect(FEEDBACK_DB_PATH, timeout=10, check_same_thread=False) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_email TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                rating TEXT CHECK(rating IN ('👍', '👎')) NOT NULL,
                FOREIGN KEY (user_email) REFERENCES UserAccessProfile(user_email) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        logger.info(f"Feedback DB initialized at {FEEDBACK_DB_PATH}")


def save_ticket(user_email: str, question: str, chat_history: str,
                suggested_team: str, selected_team: str) -> Optional[int]:
    try:
        with sqlite3.connect(TICKET_DB_PATH, timeout=10, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tickets
                (user_email, question, chat_history, suggested_team, selected_team)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_email, question, chat_history, suggested_team, selected_team))
            conn.commit()
            ticket_id = cursor.lastrowid
        logger.info(f"Ticket saved for user {user_email}.")
        return ticket_id
    except sqlite3.IntegrityError as e:
        logger.error(f"Ticket save failed for {user_email} (FK issue?): {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Ticket save failed for {user_email}: {e}", exc_info=True)
        return None


def save_feedback(user_email: str, question: str, answer: str, rating: str) -> bool:
    try:
        with sqlite3.connect(FEEDBACK_DB_PATH, timeout=10, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (user_email, question, answer, rating)
                VALUES (?, ?, ?, ?)
            ''', (user_email, question, answer, rating))
            conn.commit()
        logger.info(f"Feedback saved from user {user_email} with rating '{rating}'.")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Feedback save failed for {user_email} (FK issue?): {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Feedback save failed for {user_email}: {e}", exc_info=True)
        return False


def add_or_update_user_profile(email: str, profile_data: Dict[str, Any]) -> bool:
    try:
        hierarchy_level = int(profile_data.get("user_hierarchy_level", DEFAULT_HIERARCHY_LEVEL))
        departments_list = profile_data.get("departments", [])
        projects_membership_list = profile_data.get("projects_membership", [])
        contextual_roles_dict = profile_data.get("contextual_roles", {})

        departments_json = json.dumps(departments_list)
        projects_membership_json = json.dumps(projects_membership_list)
        contextual_roles_json = json.dumps(contextual_roles_dict)

        with sqlite3.connect(AUTH_DB_PATH, timeout=10, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO UserAccessProfile
                (user_email, user_hierarchy_level, departments, projects_membership, contextual_roles)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                email,
                hierarchy_level,
                departments_json,
                projects_membership_json,
                contextual_roles_json
            ))
            conn.commit()
        logger.info(f"User profile for {email} added/updated successfully.")
        return True
    except Exception as e:
        logger.error(f"Profile update failed for {email}: {e}", exc_info=True)
        return False


def get_user_profile(email: str) -> Optional[UserProfile]:
    try:
        with sqlite3.connect(AUTH_DB_PATH, timeout=10, check_same_thread=False) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM UserAccessProfile WHERE user_email = ?", (email,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"No profile found for {email} in database.")
                return None

            profile = dict(row)

            # Safely parse JSON fields
            for field_name, default_value in [("departments", []), ("projects_membership", []),
                                              ("contextual_roles", {})]:
                try:
                    loaded_value = json.loads(profile[field_name])
                    if field_name == "contextual_roles" and not isinstance(loaded_value, dict):
                        logger.warning(
                            f"Parsed '{field_name}' for {email} is not a dict, defaulting. Value: {loaded_value}")
                        profile[field_name] = default_value
                    elif field_name != "contextual_roles" and not isinstance(loaded_value, list):
                        logger.warning(
                            f"Parsed '{field_name}' for {email} is not a list, defaulting. Value: {loaded_value}")
                        profile[field_name] = default_value
                    else:
                        profile[field_name] = loaded_value
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        f"Could not parse '{field_name}' for {email}, defaulting. Raw: {profile.get(field_name)}")
                    profile[field_name] = default_value

            if "user_hierarchy_level" not in profile or not isinstance(profile["user_hierarchy_level"], int):
                logger.warning(
                    f"'user_hierarchy_level' for {email} invalid/missing, defaulting. Val: {profile.get('user_hierarchy_level')}")
                profile["user_hierarchy_level"] = DEFAULT_HIERARCHY_LEVEL

            return profile
    except Exception as e:
        logger.error(f"Profile retrieval failed for {email}: {e}", exc_info=True)
        return None


def _create_sample_users_if_not_exist():
    """
    Creates a set of sample users with clear, hardcoded data if they do not exist.
    This hardcoded approach is more readable and less error-prone than dynamic generation.
    """
    sample_users = {
        "staff.hr@example.com": {
            "user_hierarchy_level": 0,
            "departments": ["HR"],
            "projects_membership": [],
            "contextual_roles": {}
        },
        "lead.it.project_alpha@example.com": {
            "user_hierarchy_level": 2,
            "departments": ["IT"],
            "projects_membership": ["PROJECT_ALPHA", "PROJECT_INTERNAL_INFRA"],
            "contextual_roles": {
                "PROJECT_ALPHA": ["LEAD"],
                "IT": ["ADMIN_ROLE"]
            }
        },
        "exec.finance@example.com": {
            "user_hierarchy_level": 2,
            "departments": ["FINANCE"],
            "projects_membership": ["PROJECT_BUDGET_Q4"],
            "contextual_roles": {
                "FINANCE": ["DEPARTMENT_HEAD"]
            }
        },
        "general.user@example.com": {
            "user_hierarchy_level": 0,
            "departments": [],
            "projects_membership": [],
            "contextual_roles": {}
        },
        "admin.user@example.com": {
            "user_hierarchy_level": 3, # Matches ADMIN_HIERARCHY_LEVEL
            "departments": ["IT", "HR", "FINANCE", "LEGAL", "MARKETING", "OPERATIONS", "SALES"], # Full access
            "projects_membership": [],
            "contextual_roles": {}
        }
    }
    
    logger.info("Checking for and creating sample users if they don't exist...")
    for email, data in sample_users.items():
        if not get_user_profile(email):
            add_or_update_user_profile(email, data)
            logger.info(f"Created sample user: {email}")

def delete_user_profile(email: str) -> bool:
    """Deletes a user profile and all associated data via cascading deletes."""
    try:
        with sqlite3.connect(AUTH_DB_PATH, timeout=10, check_same_thread=False) as conn:
            cursor = conn.cursor()
            # The ON DELETE CASCADE for foreign keys in tickets and feedback tables
            # should handle associated data deletion automatically.
            cursor.execute("DELETE FROM UserAccessProfile WHERE user_email = ?", (email,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"User profile for {email} deleted successfully.")
                return True
            else:
                logger.warning(f"Attempted to delete profile for {email}, but user not found.")
                return False # Treat as success if idempotent deletion is desired
    except Exception as e:
        logger.error(f"Profile deletion failed for {email}: {e}", exc_info=True)
        return False
    


def get_recent_tickets(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetches the most recent tickets from the database.

    Args:
        limit: The maximum number of tickets to retrieve.

    Returns:
        A list of dictionaries, where each dictionary represents a ticket.
    """
    tickets = []
    try:
        with sqlite3.connect(TICKET_DB_PATH, timeout=10, check_same_thread=False) as conn:
            conn.row_factory = sqlite3.Row  # This allows accessing columns by name
            cursor = conn.cursor()
            # Fetch the most recent tickets first
            cursor.execute("SELECT * FROM tickets ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            # Convert sqlite3.Row objects to standard dictionaries
            tickets = [dict(row) for row in rows]
        logger.info(f"Successfully fetched {len(tickets)} recent tickets.")
    except Exception as e:
        logger.error(f"Failed to fetch recent tickets: {e}", exc_info=True)
    return tickets