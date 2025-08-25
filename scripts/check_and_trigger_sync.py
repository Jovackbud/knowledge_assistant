import os
import requests
import logging
import boto3
from botocore.exceptions import ClientError
from sqlalchemy import create_engine, text

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SyncChecker")

# --- Environment Variables ---
# These would be set as secrets in the Cloudflare Worker environment
DATABASE_URL = os.environ.get("DATABASE_URL")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")

# Your main app's webhook URL and token
RENDER_SYNC_WEBHOOK = os.environ.get("RENDER_SYNC_WEBHOOK")
SYNC_SECRET_TOKEN = os.environ.get("SYNC_SECRET_TOKEN")

# --- S3/R2 Functions (copied and simplified from document_updater) ---
def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        endpoint_url=AWS_ENDPOINT_URL,
        region_name="auto" # Important for R2
    )

def scan_s3_bucket(s3_client) -> dict:
    current_state = {}
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=S3_BUCKET_NAME):
            for obj in page.get('Contents', []):
                # We only care about files, not directories
                if not obj['Key'].endswith('/'):
                    current_state[obj['Key']] = obj['ETag'].strip('"')
    except ClientError as e:
        logger.error(f"Failed to scan S3 bucket '{S3_BUCKET_NAME}': {e}")
        return {} # Return empty on error
    return current_state

# --- Database Function (copied and simplified from database_utils) ---
def load_sync_state_from_db() -> dict:
    if not DATABASE_URL:
        logger.error("DATABASE_URL is not set.")
        return {}
        
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT s3_key, etag FROM syncstate")).fetchall()
            return {row.s3_key: row.etag for row in result}
    except Exception as e:
        logger.error(f"Failed to load sync state from database: {e}", exc_info=True)
        return {} # Return empty on error to be safe

# --- Main Logic ---
def check_for_changes_and_trigger_sync():
    """The main function for the serverless checker."""
    logger.info("Starting sync status check...")
    
    s3_client = get_s3_client()
    current_s3_state = scan_s3_bucket(s3_client)
    last_sync_state = load_sync_state_from_db()

    if not current_s3_state and last_sync_state:
        # This means S3 scan failed, but we have old state. Don't trigger.
        logger.warning("S3 scan returned no documents, but a previous sync state exists. Aborting to prevent accidental deletion.")
        return
    
    last_keys = set(last_sync_state.keys())
    current_keys = set(current_s3_state.keys())
    
    # Check for any changes
    deleted_keys = last_keys - current_keys
    new_keys = current_keys - last_keys
    updated_keys = {
        key for key in current_keys.intersection(last_keys)
        if current_s3_state[key] != last_sync_state.get(key)
    }

    if not any([deleted_keys, new_keys, updated_keys]):
        logger.info("✅ No changes detected in the knowledge base. No sync required.")
        return

    logger.warning(f"🔥 Changes detected! New: {len(new_keys)}, Updated: {len(updated_keys)}, Deleted: {len(deleted_keys)}. Triggering sync webhook...")

    try:
        headers = {"X-Sync-Token": SYNC_SECRET_TOKEN}
        response = requests.post(RENDER_SYNC_WEBHOOK, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        logger.info(f"🚀 Successfully triggered Render sync webhook. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to trigger Render sync webhook: {e}", exc_info=True)

# This part is for local testing of the script
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    # You would need to add RENDER_SYNC_WEBHOOK to your .env file for local testing
    check_for_changes_and_trigger_sync()