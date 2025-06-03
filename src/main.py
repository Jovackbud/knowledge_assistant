from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Any
from fastapi.responses import FileResponse
from src.auth_service import fetch_user_access_profile, update_user_permissions_by_admin, remove_user_by_admin
from src.config import AuthCredentials, RAGRequest, SuggestTeamRequest, CreateTicketRequest, FeedbackRequest, TICKET_TEAMS, ADMIN_HIERARCHY_LEVEL # Added ADMIN_HIERARCHY_LEVEL
from src.rag_processor import RAGService
from src.ticket_system import suggest_ticket_team, create_ticket
from src.feedback_system import record_feedback
from src.database_utils import init_all_databases, _create_sample_users_if_not_exist # Added
from src.document_updater import synchronize_documents # Added import
import logging # Added
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

app = FastAPI()

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
STATIC_DIR = PROJECT_ROOT / "static"

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Attempting to mount static directory at: {str(STATIC_DIR)}")
logger.info(f"Does STATIC_DIR exist? {STATIC_DIR.exists()}")
logger.info(f"Is STATIC_DIR a directory? {STATIC_DIR.is_dir()}")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting application initialization...") # Changed log message slightly for broader scope
    try:
        logger.info("Initializing all databases...")
        init_all_databases()
        logger.info("All databases initialized successfully.")

        logger.info("Creating sample users if they don't exist...")
        _create_sample_users_if_not_exist()
        logger.info("Sample user creation check completed.")

        logger.info("Synchronizing documents...") # Added log
        synchronize_documents() # Added call
        logger.info("Document synchronization completed.")

    except Exception as e:
        logger.error(f"Application initialization failed: {e}", exc_info=True) # Changed log
        # Depending on the application's needs, you might want to re-raise the exception
        # or handle it in a way that prevents the app from starting if dbs are critical.

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
@app.get("/")
async def root():
    html_file_path = STATIC_DIR / "index.html"
    logger.info(f"Serving root HTML from: {str(html_file_path)}")
    if html_file_path.exists():
        return FileResponse(str(html_file_path))
    else:
        logger.error(f"Root index.html not found at {str(html_file_path)}")
        return HTTPException(status_code=404, detail="index.html not found")

@app.post("/auth/login")
async def login(credentials: AuthCredentials):
    try:
        user_profile = fetch_user_access_profile(credentials.email)
        if user_profile:
            return user_profile
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        # Log the exception e if a logger is configured
        raise HTTPException(status_code=500, detail="Internal server error during login")

@app.post("/rag/chat")
async def rag_chat(request: RAGRequest):
    try:
        # TODO: Explore initializing RAGService once at startup for optimization
        rag_service = RAGService.from_config()
        
        # Get the RAG chain for the user
        # This requires fetch_user_access_profile to be available and working
        user_profile = fetch_user_access_profile(request.email)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found for RAG service")

        chain = rag_service.get_rag_chain(user_profile) # Pass the entire profile
        
        # Invoke the chain with the user's prompt
        response = chain.invoke(request.prompt)
        
        return {"response": response}
    except HTTPException as http_exc: # Re-raise HTTPException
        raise http_exc
    except Exception as e:
        # Log the exception e if a logger is configured
        # Consider more specific error handling for RAGService initialization vs. chain invocation
        raise HTTPException(status_code=500, detail=f"Error in RAG service: {str(e)}")

# --- Ticket System Endpoints ---

@app.post("/tickets/suggest_team")
async def suggest_team_endpoint(request: SuggestTeamRequest):
    try:
        suggested_team = suggest_ticket_team(request.question_text)
        return {"suggested_team": suggested_team, "available_teams": TICKET_TEAMS}
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Error suggesting ticket team: {str(e)}")

@app.post("/tickets/create")
async def create_ticket_endpoint(request: CreateTicketRequest):
    try:
        # Basic validation for selected_team
        if request.selected_team not in TICKET_TEAMS:
            raise HTTPException(status_code=400, detail=f"Invalid team selected. Please choose from: {', '.join(TICKET_TEAMS)}")

        ticket_id = create_ticket(
            user_email=request.email,
            question=request.question_text,
            chat_history=request.chat_history_json,
            final_selected_team=request.selected_team
        )
        if ticket_id:
            return {"message": "Ticket created successfully", "ticket_id": ticket_id}
        else:
            # This case might indicate an issue within create_ticket that didn't raise an exception
            raise HTTPException(status_code=500, detail="Ticket creation failed for an unknown reason.")
    except HTTPException as http_exc: # Re-raise HTTPException
        raise http_exc
    except Exception as e:
        logger.error(f"Error creating ticket: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating ticket: {str(e)}")

# --- Feedback System Endpoint ---

@app.post("/feedback/record")
async def record_feedback_endpoint(request: FeedbackRequest):
    try:
        record_feedback(
            user_email=request.email,
            question=request.question,
            answer=request.answer,
            rating=request.feedback_type
        )
        return {"message": "Feedback recorded successfully"}
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")

# --- Admin System Endpoints ---

class UserPermissionsRequest(BaseModel):
    target_email: str
    permissions: Dict[str, Any] # e.g., {"user_hierarchy_level": 2, "departments": ["IT"]}

async def is_admin(user_email: str) -> bool:
    """
    Checks if the given user_email corresponds to an admin.
    An admin is defined as a user with user_hierarchy_level == ADMIN_HIERARCHY_LEVEL.
    """
    if not user_email:
        return False
    # fetch_user_access_profile is synchronous. As this `is_admin` function is async,
    # ideally, blocking IO like this would be run in a thread pool.
    # e.g., from fastapi.concurrency import run_in_threadpool
    # admin_profile = await run_in_threadpool(fetch_user_access_profile, user_email)
    # However, to maintain consistency with the /auth/login endpoint's direct call,
    # which is also an async def calling the synchronous fetch_user_access_profile,
    # we will call it directly here as well.
    admin_profile = fetch_user_access_profile(user_email)
    if admin_profile and admin_profile.get("user_hierarchy_level") == ADMIN_HIERARCHY_LEVEL:
        logger.info(f"Admin check: User '{user_email}' IS an admin (Level {ADMIN_HIERARCHY_LEVEL}).")
        return True
    
    current_level = admin_profile.get("user_hierarchy_level") if admin_profile else "N/A"
    logger.warning(f"Admin check: User '{user_email}' IS NOT an admin (Hierarchy Level: {current_level}, Required: {ADMIN_HIERARCHY_LEVEL}). Profile: {admin_profile}")
    return False

@app.post("/admin/user_permissions")
async def admin_update_user_permissions(
    payload: UserPermissionsRequest,
    x_user_email: str = Header(None, alias="X-User-Email") # Extract admin's email from header
):
    """
    Admin endpoint to update user permissions.
    The admin's email must be provided in the 'X-User-Email' header.
    """
    logger.info(f"Received request to update permissions for '{payload.target_email}' by user '{x_user_email}'.")

    if not x_user_email:
        logger.warning("Admin endpoint call missing X-User-Email header.")
        raise HTTPException(status_code=400, detail="X-User-Email header is required.")

    # Verify if the requesting user is an admin
    if not await is_admin(x_user_email):
        logger.warning(f"Unauthorized attempt to update permissions by non-admin user '{x_user_email}'.")
        raise HTTPException(status_code=403, detail="Forbidden: Requesting user is not an admin.")

    try:
        # Call the auth_service function to update permissions
        # This function is currently a placeholder
        update_result = update_user_permissions_by_admin(
            target_email=payload.target_email,
            new_permissions=payload.permissions
        )
        logger.info(f"Permissions update call for '{payload.target_email}' by admin '{x_user_email}' completed. Result: {update_result}")
        return update_result
    except Exception as e:
        logger.error(f"Error during admin update of permissions for '{payload.target_email}' by '{x_user_email}': {e}", exc_info=True)
        # Check if it's an HTTPException from a deeper call (like user not found if implemented in auth_service)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")
    


class UserRemovalRequest(BaseModel): # Optional: or just take email from path
    target_email: str

@app.post("/admin/remove_user") # Or use @app.delete("/admin/user/{target_email_in_path}")
async def admin_remove_user(
    payload: UserRemovalRequest, # If using POST with payload
    # target_email_in_path: str, # If using DELETE with path parameter
    x_user_email: str = Header(None, alias="X-User-Email")
):
    logger.info(f"Received request to remove user '{payload.target_email}' by admin '{x_user_email}'.")
    # target_email_to_remove = payload.target_email # if using POST payload

    if not x_user_email:
        raise HTTPException(status_code=400, detail="X-User-Email header is required.")

    if not await is_admin(x_user_email):
        raise HTTPException(status_code=403, detail="Forbidden: Requesting user is not an admin.")

    try:
        # removal_result = remove_user_by_admin(target_email_to_remove) # if using POST payload
        removal_result = remove_user_by_admin(payload.target_email) # if using POST payload
        
        if "error" in removal_result:
             # Determine appropriate status code, e.g. 404 if user not found, 500 otherwise
            status_code = 404 if "not exist" in removal_result["error"] or "not found" in removal_result["error"] else 500
            raise HTTPException(status_code=status_code, detail=removal_result["error"])
        
        return removal_result
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error during admin removal of user '{payload.target_email}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")
    
@app.get("/admin/view_user_permissions/{target_email}")
async def admin_view_user_permissions(
    target_email: str,
    x_user_email: str = Header(None, alias="X-User-Email")
):
    logger.info(f"Admin '{x_user_email}' attempting to view permissions for user '{target_email}'.")

    if not x_user_email:
        raise HTTPException(status_code=400, detail="X-User-Email header is required.")

    if not await is_admin(x_user_email):
        logger.warning(f"Unauthorized attempt to view permissions by non-admin user '{x_user_email}' for target '{target_email}'.")
        raise HTTPException(status_code=403, detail="Forbidden: Requesting user is not an admin.")

    if not target_email or "@" not in target_email:
        raise HTTPException(status_code=400, detail="Invalid target_email provided.")

    try:
        # fetch_user_access_profile already handles logging if user is not found
        user_profile = fetch_user_access_profile(target_email)
        if not user_profile:
            raise HTTPException(status_code=404, detail=f"User profile for '{target_email}' not found.")
        
        logger.info(f"Successfully fetched profile for '{target_email}' for admin viewing by '{x_user_email}'.")
        return user_profile # Returns the full profile
    except HTTPException as http_exc:
        raise http_exc # Re-raise known HTTP exceptions
    except Exception as e:
        logger.error(f"Error during admin viewing of permissions for '{target_email}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred while fetching user permissions: {str(e)}")