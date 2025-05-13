import sqlite3
import datetime
import json
import os
from config import TICKET_DB_PATH, FEEDBACK_DB_PATH, AUTH_DB_PATH


def init_all_databases():
    """Initializes all SQLite databases if they don't exist."""
    print("Initializing databases...")
    init_ticket_db()
    init_feedback_db()
    init_auth_db()
    print("All databases initialized.")


# --- Ticket DB Functions (from PoC) ---
def init_ticket_db():
    try:
        with sqlite3.connect(TICKET_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS tickets
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               timestamp
                               DATETIME
                               DEFAULT
                               CURRENT_TIMESTAMP,
                               user_role
                               TEXT,
                               question
                               TEXT,
                               chat_history
                               TEXT,
                               suggested_team
                               TEXT,
                               selected_team
                               TEXT,
                               status
                               TEXT
                               DEFAULT
                               'Open'
                           )
                           ''')
            conn.commit()
            # print(f"Ticket database initialized at {TICKET_DB_PATH}")
    except sqlite3.Error as e:
        print(f"Error initializing ticket database: {e}")


def save_ticket(user_role, question, chat_history, suggested_team, selected_team):
    try:
        with sqlite3.connect(TICKET_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO tickets (user_role, question, chat_history, suggested_team, selected_team)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (user_role, question, chat_history, suggested_team, selected_team))
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error saving ticket: {e}")
        return False


# --- Feedback DB Functions (from PoC) ---
def init_feedback_db():
    try:
        with sqlite3.connect(FEEDBACK_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS feedback
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               timestamp
                               DATETIME
                               DEFAULT
                               CURRENT_TIMESTAMP,
                               user_role
                               TEXT,
                               question
                               TEXT,
                               answer
                               TEXT,
                               rating
                               TEXT
                               CHECK (
                               rating
                               IN
                           (
                               '👍',
                               '👎'
                           ))
                               )
                           ''')
            conn.commit()
            # print(f"Feedback database initialized at {FEEDBACK_DB_PATH}")
    except sqlite3.Error as e:
        print(f"Error initializing feedback database: {e}")


def save_feedback(user_role, question, answer, rating):
    try:
        with sqlite3.connect(FEEDBACK_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO feedback (user_role, question, answer, rating)
                           VALUES (?, ?, ?, ?)
                           ''', (user_role, question, answer, rating))
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error saving feedback: {e}")
        return False


# --- Auth Profile DB Functions (New for Phase 1) ---
def init_auth_db():
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            # Simplified for Phase 1, will expand in Phase 2 for richer ABAC attributes
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS UserAccessProfile
                           (
                               user_email
                               TEXT
                               PRIMARY
                               KEY,
                               is_board_member
                               BOOLEAN
                               DEFAULT
                               FALSE,
                               is_executive_management
                               BOOLEAN
                               DEFAULT
                               FALSE,
                               roles_in_departments
                               TEXT
                               DEFAULT
                               '[]', -- JSON string for [{"department_name": "X", "level": "Y"}]
                               roles_in_projects
                               TEXT
                               DEFAULT
                               '[]', -- JSON string for [{"project_name": "A", "level": "B"}]
                               can_access_staff_docs
                               BOOLEAN
                               DEFAULT
                               TRUE  -- Main flag for Phase 1
                           )
                           ''')
            conn.commit()
            # print(f"Auth Profile database initialized at {AUTH_DB_PATH}")
    except sqlite3.Error as e:
        print(f"Error initializing auth profile database: {e}")


def add_or_update_user_profile(email, profile_data):
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            departments_json = json.dumps(profile_data.get('roles_in_departments', []))
            projects_json = json.dumps(profile_data.get('roles_in_projects', []))

            cursor.execute('''
                INSERT OR REPLACE INTO UserAccessProfile 
                (user_email, is_board_member, is_executive_management, roles_in_departments, roles_in_projects, can_access_staff_docs)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                email,
                bool(profile_data.get('is_board_member', False)),
                bool(profile_data.get('is_executive_management', False)),
                departments_json,
                projects_json,
                bool(profile_data.get('can_access_staff_docs', True))  # Ensure boolean
            ))
            conn.commit()
            # print(f"Auth Profile for {email} added/updated.")
            return True
    except sqlite3.Error as e:
        print(f"Database error adding/updating auth profile for {email}: {e}")
        return False
    except Exception as ex:
        print(f"Generic error adding/updating auth profile for {email}: {ex}")
        return False


def get_user_profile(email):
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # Access columns by name
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM UserAccessProfile WHERE user_email = ?", (email,))
            row = cursor.fetchone()
            if row:
                profile = dict(row)
                # Deserialize JSON strings back to Python lists/dicts
                try:
                    profile['roles_in_departments'] = json.loads(profile['roles_in_departments']) if profile[
                        'roles_in_departments'] else []
                    profile['roles_in_projects'] = json.loads(profile['roles_in_projects']) if profile[
                        'roles_in_projects'] else []
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON for user {email}. Defaulting to empty lists.")
                    profile['roles_in_departments'] = []
                    profile['roles_in_projects'] = []
                return profile
            return None
    except sqlite3.Error as e:
        print(f"Database error fetching auth profile for {email}: {e}")
        return None

# Initialize all databases when this module is imported
# init_all_databases() # Usually called from main app or a setup script