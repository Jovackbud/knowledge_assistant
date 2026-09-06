import os
import json
import logging
from typing import Dict, Optional, List, Any, cast

# Import SQLAlchemy components
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.exc import SQLAlchemyError

from .config import (
    UserProfile, DEFAULT_HIERARCHY_LEVEL, USER_EMAIL_KEY, HIERARCHY_LEVEL_KEY, DEPARTMENTS_KEY,
    PROJECTS_KEY, CONTEXTUAL_ROLES_KEY, IS_ADMIN_KEY
)

logger = logging.getLogger(__name__)

# --- Database Connection Setup ---
# Get the database connection URL from environment variables.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("FATAL: DATABASE_URL environment variable is not set.")

# Create a single, reusable engine. This is more efficient than connecting repeatedly.
try:
    engine: Engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 31}, pool_recycle=1800)
    logger.info("✅ Successfully created SQLAlchemy engine for PostgreSQL with extended timeout.")
except Exception as e:
    logger.error(f"❌ Failed to create SQLAlchemy engine: {e}", exc_info=True)
    raise

# --- Schema Initialization ---

def init_all_databases():
    """
    Connects to the database and ensures all necessary tables are created.
    This function is idempotent and safe to run on every startup.
    """
    try:
        with engine.connect() as connection:
            logger.info("Initializing/verifying database schema...")
            init_auth_db(connection)
            init_ticket_db(connection)
            init_ticket_replies_db(connection)
            init_feedback_db(connection)
            init_sync_state_db(connection)
            logger.info("✅ All database tables initialized/verified successfully.")
    except SQLAlchemyError as e:
        logger.error(f"❌ Database schema initialization failed: {e}", exc_info=True)
        raise

def init_auth_db(connection):
    """Initializes the UserAccessProfile table."""
    connection.execute(text('''
        CREATE TABLE IF NOT EXISTS UserAccessProfile (
            user_email TEXT PRIMARY KEY,
            user_hierarchy_level INTEGER DEFAULT 0 NOT NULL CHECK (user_hierarchy_level BETWEEN 0 AND 3),
            departments JSONB DEFAULT '[]'::jsonb NOT NULL,
            projects_membership JSONB DEFAULT '[]'::jsonb NOT NULL,
            contextual_roles JSONB DEFAULT '{}'::jsonb NOT NULL,
                            is_admin BOOLEAN DEFAULT FALSE NOT NULL
        )
    '''))
    connection.commit()
    logger.info("Auth table verified.")

def init_ticket_db(connection):
    """Initializes the tickets table with a foreign key to users."""
    connection.execute(text('''
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            user_email TEXT NOT NULL REFERENCES UserAccessProfile(user_email) ON DELETE CASCADE,
            question TEXT NOT NULL,
            chat_history TEXT NOT NULL,
            suggested_team TEXT NOT NULL,
            selected_team TEXT NOT NULL,
            status TEXT DEFAULT 'Open'
        )
    '''))
    connection.commit()
    logger.info("Tickets table verified.")

def init_ticket_replies_db(connection):
    """Initializes the ticket_replies table for admin-to-user reply threads."""
    connection.execute(text('''
        CREATE TABLE IF NOT EXISTS ticket_replies (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            admin_email TEXT NOT NULL,
            reply_text TEXT NOT NULL,
            email_sent BOOLEAN DEFAULT FALSE,
            "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    '''))
    connection.commit()
    logger.info("Ticket replies table verified.")

def init_feedback_db(connection):
    """Initializes the feedback table with a foreign key to users."""
    connection.execute(text('''
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            user_email TEXT NOT NULL REFERENCES UserAccessProfile(user_email) ON DELETE CASCADE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            rating TEXT CHECK(rating IN ('👍', '👎')) NOT NULL
        )
    '''))
    connection.commit()
    logger.info("Feedback table verified.")

def init_sync_state_db(connection):
    """Initializes the SyncState table for tracking document versions."""
    connection.execute(text('''
        CREATE TABLE IF NOT EXISTS SyncState (
            s3_key TEXT PRIMARY KEY,
            etag TEXT NOT NULL,
            last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    '''))
    connection.commit()
    logger.info("SyncState table verified.")

# --- Data Access Functions ---

def save_ticket(user_email: str, question: str, chat_history: str,
                suggested_team: str, selected_team: str) -> Optional[int]:
    sql = text("""
        INSERT INTO tickets (user_email, question, chat_history, suggested_team, selected_team)
        VALUES (:user_email, :question, :chat_history, :suggested_team, :selected_team)
        RETURNING id
    """)
    try:
        with engine.connect() as connection:
            result = connection.execute(sql, {
                "user_email": user_email, "question": question, "chat_history": chat_history,
                "suggested_team": suggested_team, "selected_team": selected_team
            }).scalar_one_or_none()
            connection.commit()
            logger.info(f"Ticket saved for user {user_email}.")
            return result
    except SQLAlchemyError as e:
        logger.error(f"Ticket save failed for {user_email}: {e}", exc_info=True)
        return None

def save_feedback(user_email: str, question: str, answer: str, rating: str) -> bool:
    sql = text("""
        INSERT INTO feedback (user_email, question, answer, rating)
        VALUES (:user_email, :question, :answer, :rating)
    """)
    try:
        with engine.connect() as connection:
            connection.execute(sql, {
                "user_email": user_email, "question": question,
                "answer": answer, "rating": rating
            })
            connection.commit()
            logger.info(f"Feedback saved from user {user_email} with rating '{rating}'.")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Feedback save failed for {user_email}: {e}", exc_info=True)
        return False

# In src/database_utils.py, replace the whole function

def add_or_update_user_profile(email: str, profile_data: UserProfile) -> bool:
    """
    Adds a new user or updates an existing one. This version uses shared constants
    for keys to prevent mismatches with the service layer.
    """
    sql = text("""
        INSERT INTO useraccessprofile (user_email, user_hierarchy_level, departments, projects_membership, contextual_roles, is_admin)
        VALUES (:email, :level, :depts, :projs, :roles, :is_admin)
        ON CONFLICT (user_email) DO UPDATE SET
            user_hierarchy_level = EXCLUDED.user_hierarchy_level,
            departments = EXCLUDED.departments,
            projects_membership = EXCLUDED.projects_membership,
            contextual_roles = EXCLUDED.contextual_roles,
            is_admin = EXCLUDED.is_admin
    """)
    try:
        with engine.connect() as connection:
            # By using the imported constants for keys, we guarantee they match the keys
            # used in auth_service when building the profile_data dictionary.
            params = {
                "email": email,
                "level": int(profile_data.get(HIERARCHY_LEVEL_KEY, DEFAULT_HIERARCHY_LEVEL)),
                "depts": json.dumps(profile_data.get(DEPARTMENTS_KEY, [])),
                "projs": json.dumps(profile_data.get(PROJECTS_KEY, [])),
                "roles": json.dumps(profile_data.get(CONTEXTUAL_ROLES_KEY, {})),
                "is_admin": profile_data.get(IS_ADMIN_KEY, False)
            }
            connection.execute(sql, params)
            connection.commit()
            logger.info(f"User profile for {email} added/updated successfully.")
            return True
    except Exception as e: # Broader exception to catch any potential issue during execution
        logger.error(f"Profile update/add failed for {email}: {e}", exc_info=True)
        return False

def get_user_profile(email: str) -> Optional[UserProfile]:
    sql = text("SELECT * FROM UserAccessProfile WHERE user_email = :email")
    try:
        with engine.connect() as connection:
            result = connection.execute(sql, {"email": email}).fetchone()
            if not result:
                logger.warning(f"No profile found for {email} in database.")
                return None
            # The database row can be directly converted to a dictionary-like object
            return cast(UserProfile, dict(result._mapping))
    except SQLAlchemyError as e:
        logger.error(f"Profile retrieval failed for {email}: {e}", exc_info=True)
        return None

def delete_user_profile(email: str) -> bool:
    sql = text("DELETE FROM UserAccessProfile WHERE user_email = :email")
    try:
        with engine.connect() as connection:
            result = connection.execute(sql, {"email": email})
            connection.commit()
            if result.rowcount > 0:
                logger.info(f"User profile for {email} deleted successfully.")
                return True
            else:
                logger.warning(f"Attempted to delete profile for {email}, but user not found.")
                return False
    except SQLAlchemyError as e:
        logger.error(f"Profile deletion failed for {email}: {e}", exc_info=True)
        return False

def get_recent_tickets(limit: int = 50) -> List[Dict[str, Any]]:
    sql = text('SELECT * FROM tickets ORDER BY "timestamp" DESC LIMIT :limit')
    tickets = []
    try:
        with engine.connect() as connection:
            result = connection.execute(sql, {"limit": limit}).fetchall()
            tickets = [dict(row._mapping) for row in result]
        logger.info(f"Successfully fetched {len(tickets)} recent tickets.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch recent tickets: {e}", exc_info=True)
    return tickets


def update_ticket_status(ticket_id: int, new_status: str) -> bool:
    """Updates the status of a ticket by ID. Returns True on success."""
    sql = text("UPDATE tickets SET status = :status WHERE id = :ticket_id")
    try:
        with engine.connect() as connection:
            result = connection.execute(sql, {"status": new_status, "ticket_id": ticket_id})
            connection.commit()
            if result.rowcount > 0:
                logger.info(f"Ticket #{ticket_id} status updated to '{new_status}'.")
                return True
            logger.warning(f"Ticket #{ticket_id} not found for status update.")
            return False
    except SQLAlchemyError as e:
        logger.error(f"Failed to update ticket #{ticket_id}: {e}", exc_info=True)
        return False


def save_ticket_reply(ticket_id: int, admin_email: str, reply_text: str, email_sent: bool) -> Optional[int]:
    """Saves an admin reply to the ticket_replies table. Returns the new reply ID."""
    sql = text("""
        INSERT INTO ticket_replies (ticket_id, admin_email, reply_text, email_sent)
        VALUES (:ticket_id, :admin_email, :reply_text, :email_sent)
        RETURNING id
    """)
    try:
        with engine.connect() as connection:
            result = connection.execute(sql, {
                "ticket_id": ticket_id,
                "admin_email": admin_email,
                "reply_text": reply_text,
                "email_sent": email_sent
            }).scalar_one_or_none()
            connection.commit()
            logger.info(f"Reply saved for ticket #{ticket_id} by {admin_email}.")
            return result
    except SQLAlchemyError as e:
        logger.error(f"Failed to save reply for ticket #{ticket_id}: {e}", exc_info=True)
        return None


def get_ticket_replies(ticket_id: int) -> List[Dict[str, Any]]:
    """Returns all replies for a ticket, oldest first."""
    sql = text('SELECT * FROM ticket_replies WHERE ticket_id = :ticket_id ORDER BY "timestamp" ASC')
    try:
        with engine.connect() as connection:
            result = connection.execute(sql, {"ticket_id": ticket_id}).fetchall()
            return [dict(row._mapping) for row in result]
    except SQLAlchemyError as e:
        logger.error(f"Failed to get replies for ticket #{ticket_id}: {e}", exc_info=True)
        return []


def get_ticket_by_id(ticket_id: int) -> Optional[Dict[str, Any]]:
    """Returns a single ticket row by ID."""
    sql = text("SELECT * FROM tickets WHERE id = :ticket_id")
    try:
        with engine.connect() as connection:
            row = connection.execute(sql, {"ticket_id": ticket_id}).fetchone()
            return dict(row._mapping) if row else None
    except SQLAlchemyError as e:
        logger.error(f"Failed to get ticket #{ticket_id}: {e}", exc_info=True)
        return None


def create_sample_users_if_not_exist():
    sample_users = {
        "staff.hr@example.com": { "user_hierarchy_level": 0, "departments": ["HR"], "projects_membership": [], "contextual_roles": {} },
        "lead.it.project_alpha@example.com": { "user_hierarchy_level": 2, "departments": ["IT"], "projects_membership": ["PROJECT_ALPHA", "PROJECT_INTERNAL_INFRA"], "contextual_roles": { "PROJECT_ALPHA": ["LEAD"], "IT": ["ADMIN_ROLE"] } },
        "exec.finance@example.com": { "user_hierarchy_level": 2, "departments": ["FINANCE"], "projects_membership": ["PROJECT_BUDGET_Q4"], "contextual_roles": { "FINANCE": ["DEPARTMENT_HEAD"] } },
        "general.user@example.com": { "user_hierarchy_level": 0, "departments": [], "projects_membership": [], "contextual_roles": {} },
        "admin.user@example.com": { "user_hierarchy_level": 0, "departments": ["IT"], "is_admin": True, "projects_membership": [], "contextual_roles": {} }
    }
    logger.info("Checking for and creating sample users if they don't exist in external DB...")
    for email, data in sample_users.items():
        if not get_user_profile(email):
            add_or_update_user_profile(email, cast(UserProfile, data))
            logger.info(f"Created sample user: {email}")


def load_sync_state_from_db() -> Dict[str, str]:
    """Loads the document sync state (s3_key -> etag) from the database."""
    sql = text("SELECT s3_key, etag FROM SyncState")
    try:
        with engine.connect() as connection:
            result = connection.execute(sql).fetchall()
            # Use a dictionary comprehension for a clean and efficient conversion
            return {row.s3_key: row.etag for row in result}
    except SQLAlchemyError as e:
        logger.error(f"Failed to load sync state from database: {e}", exc_info=True)
        return {} # Return empty dict on error to force a full sync

def save_sync_state_to_db(state: Dict[str, str]):
    """Saves the current sync state to the database, overwriting the old state."""
    # This is an efficient way to sync: delete all old state and insert the new state.
    # It's robust and simpler than calculating individual diffs.
    delete_sql = text("DELETE FROM SyncState")
    insert_sql = text("INSERT INTO SyncState (s3_key, etag) VALUES (:key, :etag)")
    
    try:
        with engine.connect() as connection:
            # Use a transaction to ensure atomicity
            with connection.begin():
                connection.execute(delete_sql)
                if state: # Only try to insert if the state dict is not empty
                    # Execute all inserts in a single batch
                    connection.execute(insert_sql, [{"key": k, "etag": v} for k, v in state.items()])
            logger.info(f"Successfully saved sync state for {len(state)} documents to the database.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to save sync state to database: {e}", exc_info=True)