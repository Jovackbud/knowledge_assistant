# scripts/bulk_add_users.py - UPDATED
import os
import sys
import logging
import argparse
from pathlib import Path
from typing import cast

# --- Setup Project Root Path ---
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# --- Third-party Imports ---
import pandas as pd
from dotenv import load_dotenv

# --- Local Application Imports ---
from src.database_utils import add_or_update_user_profile, get_user_profile
from src.config import (
    UserProfile,
    DEFAULT_HIERARCHY_LEVEL,
    USER_EMAIL_KEY, HIERARCHY_LEVEL_KEY, DEPARTMENTS_KEY,
    PROJECTS_KEY, CONTEXTUAL_ROLES_KEY, IS_ADMIN_KEY
)

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BulkUserAdd")

def create_users_from_file(filepath: Path, sheet_name: str, column_index: int):
    """
    Reads emails from an Excel or TXT file and creates new user profiles.
    Skips users that already exist in the database.
    """
    if not filepath.exists():
        logger.error(f"FATAL: The input file was not found at '{filepath}'.")
        return

    # --- Read emails from the specified file ---
    emails = []
    try:
        if filepath.suffix.lower() in ['.xlsx', '.xls']:
            logger.info(f"Reading from Excel file: '{filepath}', sheet: '{sheet_name}', column: {column_index}")
            # header=None tells pandas not to treat the first row as a header
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
            # Select the specified column, drop empty rows, ensure type is string, and convert to list
            emails = df[column_index].dropna().astype(str).tolist()
        elif filepath.suffix.lower() == '.txt':
            logger.info(f"Reading from TXT file: '{filepath}'")
            with open(filepath, 'r') as f:
                emails = [line.strip() for line in f if line.strip()]
        else:
            logger.error(f"Unsupported file type: '{filepath.suffix}'. Please use an Excel (.xlsx, .xls) or .txt file.")
            return
            
        # Final cleanup of emails
        emails = [email.strip() for email in emails if "@" in email]

    except Exception as e:
        logger.error(f"Failed to read or process the file '{filepath}': {e}", exc_info=True)
        return

    if not emails:
        logger.warning("No valid email addresses found in the file. Nothing to do.")
        return

    logger.info(f"Found {len(emails)} valid emails to process.")

    # --- Initialize counters for the final report ---
    added_count = 0
    skipped_count = 0
    error_count = 0

    # --- Process each email ---
    for email in emails:
        email = email.lower()
        try:
            if get_user_profile(email):
                logger.info(f"Skipping '{email}': User already exists.")
                skipped_count += 1
                continue
            
            # UPDATED: The default profile now includes the is_admin flag
            # and matches the UserProfile TypedDict structure.
            default_profile = {
                USER_EMAIL_KEY: email,
                HIERARCHY_LEVEL_KEY: DEFAULT_HIERARCHY_LEVEL, # 0 for staff
                DEPARTMENTS_KEY: [],
                PROJECTS_KEY: [],
                CONTEXTUAL_ROLES_KEY: {},
                IS_ADMIN_KEY: False # New users are not admins by default
            }
            
            # UPDATED: We cast the dict to UserProfile to match the function's strict type hint.
            success = add_or_update_user_profile(email, cast(UserProfile, default_profile))
            
            if success:
                logger.info(f"SUCCESS: Created new user profile for '{email}'.")
                added_count += 1
            else:
                logger.error(f"FAILURE: Could not create profile for '{email}'. Check database logs.")
                error_count += 1
        
        except Exception as e:
            logger.error(f"CRITICAL ERROR processing '{email}': {e}", exc_info=False)
            error_count += 1

    # --- Print a final summary report ---
    logger.info("--- Bulk User Creation Complete ---")
    logger.info(f"Total valid emails processed: {len(emails)}")
    logger.info(f"✅ New users added: {added_count}")
    logger.info(f"⏩ Users skipped (already existed): {skipped_count}")
    if error_count > 0:
        logger.error(f"❌ Errors encountered: {error_count}")
    logger.info("-----------------------------------")

def main():
    """
    Main function to parse command-line arguments and run the user creation process.
    """
    parser = argparse.ArgumentParser(description="Bulk add users to the application from an Excel or TXT file.")
    parser.add_argument("filepath", type=Path, help="Path to the input file (e.g., 'user_list.xlsx' or 'emails.txt').")
    parser.add_argument("--sheet-name", type=str, default=0, help="Name of the sheet to read from in an Excel file (defaults to the first sheet).")
    parser.add_argument("--column-index", type=int, default=1, help="The column index where emails are located (0 for first column, 1 for second, etc.). Defaults to 1 (the second column).")
    
    args = parser.parse_args()

    # Load environment variables from .env file in the project root
    load_dotenv(dotenv_path=project_root / '.env')
    
    if not os.getenv("DATABASE_URL"):
        logger.error("FATAL: DATABASE_URL is not set in your .env file.")
        return

    create_users_from_file(args.filepath, args.sheet_name, args.column_index)

if __name__ == "__main__":
    main()