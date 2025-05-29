from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from src.auth_service import fetch_user_access_profile, is_admin
from src.config import AuthCredentials, RAGRequest, SuggestTeamRequest, CreateTicketRequest, FeedbackRequest, TICKET_TEAMS, UserProfileData, AdminUserCreateRequest, AdminUserUpdateRequest, AdminUserDeleteRequest
from src.rag_processor import RAGService
from src.ticket_system import suggest_ticket_team, create_ticket
from src.feedback_system import record_feedback
from src.database_utils import init_all_databases, _create_sample_users_if_not_exist, add_or_update_user_profile, get_all_user_profiles, delete_user_profile, get_user_profile
import logging 
from pathlib import Path
import os
from typing import Dict, Optional, Any, List # Add List here

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
    logger.info("Starting database initialization...")
    try:
        init_all_databases()
        logger.info("All databases initialized successfully.")
        _create_sample_users_if_not_exist()
        logger.info("Sample user creation check completed.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        # Depending on the application's needs, you might want to re-raise the exception
        # or handle it in a way that prevents the app from starting if dbs are critical.

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- Admin Endpoints ---
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# Helper function to check if the requesting user is an admin
async def verify_admin(admin_email: str):
    """Fetches user profile and raises HTTPException if not admin."""
    user_profile = fetch_user_access_profile(admin_email)
    if not user_profile:
        logger.warning(f"Admin check failed: User {admin_email} not found.")
        raise HTTPException(status_code=401, detail=f"Unauthorized: User '{admin_email}' not found.") # 401 if admin email itself is invalid
    if not is_admin(user_profile):
        logger.warning(f"Admin check failed: User {admin_email} is not an admin.")
        raise HTTPException(status_code=403, detail=f"Forbidden: User '{admin_email}' does not have admin privileges.") # 403 if user exists but isn't admin
    # If successful, no exception is raised
    # Optionally return the user profile here if needed in the endpoint logic, but for just authorization, raising is sufficient.

@admin_router.get("/users", response_model=List[UserProfileData])
async def list_users(admin_email: str): # Get admin_email from query parameter for GET request
    await verify_admin(admin_email) # Check if the requesting user is an admin
    
    try:
        all_profiles = get_all_user_profiles()
        # The structure returned by get_all_user_profiles should match UserProfileData due to parsing in DB utils
        return all_profiles
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching users.")


@admin_router.post("/users", response_model=UserProfileData) # Return the created/updated profile
async def create_user(request: AdminUserCreateRequest):
    await verify_admin(request.admin_email) # Check if the requesting user is an admin

    # Check if user already exists explicitly before add_or_update
    existing_user = get_user_profile(request.user_profile.user_email)
    if existing_user:
        raise HTTPException(status_code=409, detail=f"User with email {request.user_profile.user_email} already exists. Use PUT to update.")

    try:
        # add_or_update_user_profile handles both add and update.
        # We'll use it for creation here.
        success = add_or_update_user_profile(
            request.user_profile.user_email,
            request.user_profile.model_dump() # Use .model_dump() for Pydantic V2, .dict() for V1
        )
        if success:
            # Fetch the newly created user to return it in the response
            created_profile = get_user_profile(request.user_profile.user_email)
            if created_profile:
                 # Database function already parses JSON, so structure should match UserProfileData
                 return UserProfileData(**created_profile)
            else:
                 # This case should ideally not happen if add_or_update was successful
                 raise HTTPException(status_code=500, detail="Failed to retrieve created user profile.")

        else:
            raise HTTPException(status_code=500, detail="Failed to create user profile in database.")
    except HTTPException as http_exc: # Re-raise HTTPExceptions we raised (like 409)
         raise http_exc
    except Exception as e:
        logger.error(f"Error creating user {request.user_profile.user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error creating user.")


@admin_router.put("/users/{target_email}", response_model=UserProfileData) # Return the updated profile
async def update_user(target_email: str, request: AdminUserUpdateRequest):
    await verify_admin(request.admin_email) # Check if the requesting user is an admin

    # Optional: Ensure target_email in path matches email in body payload
    if target_email != request.user_profile.user_email:
         logger.warning(f"Admin update mismatch: target_email {target_email} != body email {request.user_profile.user_email}")
         # Decide policy: Use path email or body email? Path is RESTful.
         # Let's use path email as the canonical identifier for the update.
         # We could raise an error, but for simplicity let's log and use path email.
         # If you want to strictly enforce matching emails, uncomment the next line:
         # raise HTTPException(status_code=400, detail="Email in path and body must match.")

    # Check if target user exists before attempting update
    existing_user = get_user_profile(target_email)
    if not existing_user:
        raise HTTPException(status_code=404, detail=f"User with email {target_email} not found.")


    try:
        # Use the target_email from the path for the update operation
        success = add_or_update_user_profile(
            target_email, # Use email from path
            request.user_profile.model_dump() # Use .model_dump() for Pydantic V2, .dict() for V1
        )
        if success:
            # Fetch the updated user to return it in the response
            updated_profile = get_user_profile(target_email)
            if updated_profile:
                return UserProfileData(**updated_profile)
            else:
                 # This case should ideally not happen if add_or_update was successful
                 raise HTTPException(status_code=500, detail="Failed to retrieve updated user profile.")
        else:
            raise HTTPException(status_code=500, detail="Failed to update user profile in database.")
    except HTTPException as http_exc: # Re-raise HTTPExceptions we raised (like 404)
         raise http_exc
    except Exception as e:
        logger.error(f"Error updating user {target_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error updating user.")


@admin_router.delete("/users/{target_email}")
async def delete_user(target_email: str, request: AdminUserDeleteRequest): # Admin email in body
    await verify_admin(request.admin_email) # Check if the requesting user is an admin

    # Optional: Prevent admin from deleting themselves? Add logic here if needed.
    # if request.admin_email.lower() == target_email.lower():
    #     raise HTTPException(status_code=400, detail="Admins cannot delete their own profile.")

    try:
        success = delete_user_profile(target_email)
        if success:
            return {"message": f"User profile for {target_email} deleted successfully."}
        else:
            raise HTTPException(status_code=404, detail=f"User with email {target_email} not found for deletion.")
    except Exception as e:
        logger.error(f"Error deleting user {target_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error deleting user.")

# --- End Admin Endpoints ---

app.include_router(admin_router)
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
    
