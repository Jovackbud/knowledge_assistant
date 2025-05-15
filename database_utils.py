import sqlite3
import json
import os
from typing import Dict, Optional, List
from config import TICKET_DB_PATH, FEEDBACK_DB_PATH, AUTH_DB_PATH


def init_all_databases():
    """Initialize all databases with proper error handling"""
    try:
        init_ticket_db()
        init_feedback_db()
        init_auth_db()
        print("✅ All databases initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def init_ticket_db():
    """Ticket database with foreign key support"""
    with sqlite3.connect(TICKET_DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
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
                FOREIGN KEY (user_email) REFERENCES UserAccessProfile(user_email)
            )
        ''')
        conn.commit()

def init_feedback_db():
    """Feedback database initialization"""
    with sqlite3.connect(FEEDBACK_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_email TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                rating TEXT CHECK(rating IN ('👍', '👎')),
                FOREIGN KEY (user_email) REFERENCES UserAccessProfile(user_email)
            )
        ''')
        conn.commit()

def init_auth_db():
    """Authentication database initialization"""
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS UserAccessProfile (
                user_email TEXT PRIMARY KEY,
                is_board_member BOOLEAN DEFAULT FALSE NOT NULL,
                is_executive_management BOOLEAN DEFAULT FALSE NOT NULL,
                roles_in_departments TEXT DEFAULT '[]' NOT NULL,
                roles_in_projects TEXT DEFAULT '[]' NOT NULL,
                can_access_staff_docs BOOLEAN DEFAULT TRUE NOT NULL
            )
        ''')
        conn.commit()

def save_ticket(user_email: str, question: str, chat_history: str,
               suggested_team: str, selected_team: str) -> bool:
    """Save ticket to database"""
    try:
        with sqlite3.connect(TICKET_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tickets 
                (user_email, question, chat_history, suggested_team, selected_team)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_email, question, chat_history, suggested_team, selected_team))
            conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ticket save failed: {e}")
        return False


def add_or_update_user_profile(email: str, profile_data: Dict) -> bool:
    """Upsert user profile with validation"""
    try:
        departments = json.dumps(profile_data.get("roles_in_departments", []))
        projects = json.dumps(profile_data.get("roles_in_projects", []))

        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO UserAccessProfile 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                email,
                bool(profile_data.get("is_board_member", False)),
                bool(profile_data.get("is_executive_management", False)),
                departments,
                projects,
                bool(profile_data.get("can_access_staff_docs", True))
            ))
            conn.commit()
        return True
    except Exception as e:
        print(f"❌ Profile update failed for {email}: {e}")
        return False


def get_user_profile(email: str) -> Optional[Dict]:
    """Retrieve profile with safe JSON parsing"""
    try:
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM UserAccessProfile WHERE user_email = ?", (email,))
            row = cursor.fetchone()
            if not row: return None

            profile = dict(row)
            profile["roles_in_departments"] = json.loads(profile["roles_in_departments"])
            profile["roles_in_projects"] = json.loads(profile["roles_in_projects"])
            return profile
    except Exception as e:
        print(f"❌ Profile retrieval failed: {e}")
        return None