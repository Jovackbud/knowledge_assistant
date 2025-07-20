import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Security, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED
from fastapi.security import APIKeyHeader

# --- Local Imports ---
from .auth_service import fetch_user_access_profile, update_user_permissions_by_admin, remove_user_by_admin
from .rag_processor import RAGService
from .ticket_system import suggest_ticket_team, create_ticket
from .feedback_system import record_feedback
from .database_utils import init_all_databases, get_recent_tickets
from .security import create_access_token, get_current_active_user, AuthException
from .document_updater import synchronize_documents

# --- Configuration and Models ---
from .config import (
    AuthCredentials, RAGRequest, SuggestTeamRequest, CreateTicketRequest, FeedbackRequest,
    TICKET_TEAMS, ADMIN_HIERARCHY_LEVEL, KNOWN_DEPARTMENT_TAGS
)

# --- App Setup ---
app = FastAPI(title="Company Knowledge Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service: Optional[RAGService] = None

# --- Path and Logging Configuration ---
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
STATIC_DIR = PROJECT_ROOT / "static"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI Dependencies for Security ---

def get_current_user_profile(token: str = Header(None, alias="Authorization")) -> Dict[str, Any]:
    if token is None or not token.lower().startswith("bearer "):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated: Missing or invalid token format.")
    
    token_value = token.split(" ")[1]
    try:
        user_profile = get_current_active_user(token=token_value)
        return user_profile
    except AuthException as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=e.detail, headers={"WWW-Authenticate": "Bearer"})

def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user_profile)) -> Dict[str, Any]:
    user_level = current_user.get("user_hierarchy_level")
    if user_level != ADMIN_HIERARCHY_LEVEL:
        logger.warning(
            f"Admin access denied for user '{current_user.get('user_email')}'. "
            f"Level: {user_level}, Required: {ADMIN_HIERARCHY_LEVEL}"
        )
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden: User does not have admin privileges.")
    
    logger.info(f"Admin access granted for user '{current_user.get('user_email')}'.")
    return current_user

# --- Security for Scheduled Sync Endpoint ---
api_key_header = APIKeyHeader(name="X-Sync-Token", auto_error=False)
SYNC_SECRET_TOKEN = os.getenv("SYNC_SECRET_TOKEN")

async def get_api_key(api_key: str = Security(api_key_header)):
    if not SYNC_SECRET_TOKEN:
        logger.error("SYNC_SECRET_TOKEN is not set in the environment. Sync endpoint is disabled.")
        raise HTTPException(status_code=500, detail="Sync service is not configured.")
    if api_key != SYNC_SECRET_TOKEN:
        logger.warning("Invalid or missing sync token provided.")
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid or missing sync token")
    return api_key

# --- App Lifecycle Events ---

@app.on_event("startup")
async def startup_event():
    global rag_service
    logger.info("--- Application Startup ---")
    try:
        init_all_databases()
        rag_service = RAGService.from_config()
        logger.info("--- Startup Complete ---")
    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        raise

# --- Static Files and Root Endpoint ---

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    html_file_path = STATIC_DIR / "index.html"
    if html_file_path.exists():
        return FileResponse(str(html_file_path))
    raise HTTPException(status_code=404, detail="index.html not found")

# --- Authentication Endpoint ---

@app.post("/auth/login")
async def login(credentials: AuthCredentials):
    try:
        user_profile = fetch_user_access_profile(credentials.email)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found or credentials incorrect.")

        access_token = create_access_token(data={"sub": user_profile["user_email"]})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_profile": user_profile
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Internal server error during login for {credentials.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during login.")

# --- Core RAG Endpoint ---
# --- UPGRADED: Implements the history-aware retriever logic ---
@app.post("/rag/chat")
async def rag_chat(request: RAGRequest, current_user: Dict[str, Any] = Depends(get_current_user_profile)):
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG Service is not available.")
    
    user_email = current_user.get("user_email")
    logger.info(f"Chat request received from authenticated user: {user_email}")

    full_chat_history = request.chat_history + [{"role": "user", "content": request.prompt}]

    try:
        conversational_rag_chain = rag_service.get_rag_chain(current_user, full_chat_history)
        
        async def stream_generator():
            try:
                chain_input = {
                    "question": request.prompt,
                    "chat_history": request.chat_history
                }
                
                final_sources = []
                async for event in conversational_rag_chain.astream_events(chain_input, version="v1"):
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        chunk_content = event["data"]["chunk"].content
                        if chunk_content:
                            yield f"data: {json.dumps({'answer_chunk': chunk_content})}\n\n"
                    elif kind == "on_chain_end":
                        final_docs = event["data"]["output"].get("docs", [])
                        final_sources = list(set([doc.metadata.get("source", "Unknown") for doc in final_docs]))

                if final_sources:
                    yield f"data: {json.dumps({'sources': final_sources})}\n\n"

            except Exception as e:
                logger.error(f"Error during RAG stream for user {user_email}: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': 'An error occurred during generation.'})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in RAG service for user {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat request.")


# --- Ticket System Endpoints ---

@app.post("/tickets/suggest_team")
async def suggest_team_endpoint(request: SuggestTeamRequest, _: Dict[str, Any] = Depends(get_current_user_profile)):
    return {"suggested_team": suggest_ticket_team(request.question_text), "available_teams": TICKET_TEAMS}

@app.post("/tickets/create")
async def create_ticket_endpoint(request: CreateTicketRequest, current_user: Dict[str, Any] = Depends(get_current_user_profile)):
    if request.selected_team not in TICKET_TEAMS:
        raise HTTPException(status_code=400, detail=f"Invalid team selected.")

    ticket_id = create_ticket(
        user_email=current_user["user_email"],
        question=request.question_text,
        chat_history=request.chat_history_json,
        final_selected_team=request.selected_team
    )
    if ticket_id is not None:
        return {"message": "Ticket created successfully", "ticket_id": ticket_id}
    raise HTTPException(status_code=500, detail="Ticket creation failed in the database.")

# --- Feedback System Endpoint ---

@app.post("/feedback/record")
async def record_feedback_endpoint(request: FeedbackRequest, current_user: Dict[str, Any] = Depends(get_current_user_profile)):
    success = record_feedback(
        user_email=current_user["user_email"],
        question=request.question,
        answer=request.answer,
        rating=request.feedback_type
    )
    if success:
        return {"message": "Feedback recorded successfully"}
    raise HTTPException(status_code=500, detail="Error recording feedback.")

# --- Scheduled Sync Endpoint ---
@app.post("/admin/sync_documents", dependencies=[Depends(get_api_key)])
async def trigger_document_sync(background_tasks: BackgroundTasks):
    logger.info("Document synchronization triggered via secure endpoint.")
    background_tasks.add_task(synchronize_documents)
    return {"message": "Document synchronization process started in the background."}

# --- Admin Endpoints (Secured by get_current_admin_user) ---

class UserPermissionsRequest(BaseModel):
    target_email: str
    permissions: Dict[str, Any]

class UserRemovalRequest(BaseModel):
    target_email: str

# --- REFINED: Dependencies are no longer redundant ---
@app.get("/admin/config_tags")
async def get_config_tags(_: Dict[str, Any] = Depends(get_current_admin_user)):
    return {"known_department_tags": KNOWN_DEPARTMENT_TAGS}

@app.get("/admin/view_user_permissions/{target_email}")
async def admin_view_user_permissions(target_email: str, admin_user: Dict[str, Any] = Depends(get_current_admin_user)):
    logger.info(f"Admin '{admin_user['user_email']}' viewing permissions for '{target_email}'.")
    user_profile = fetch_user_access_profile(target_email)
    if not user_profile:
        raise HTTPException(status_code=404, detail=f"User profile for '{target_email}' not found.")
    return user_profile

@app.post("/admin/user_permissions")
async def admin_update_user_permissions(payload: UserPermissionsRequest, admin_user: Dict[str, Any] = Depends(get_current_admin_user)):
    logger.info(f"Admin '{admin_user['user_email']}' updating permissions for '{payload.target_email}'.")
    update_result = update_user_permissions_by_admin(
        target_email=payload.target_email,
        new_permissions=payload.permissions
    )
    if "error" in update_result:
        raise HTTPException(status_code=500, detail=update_result["error"])
    return update_result

@app.post("/admin/remove_user")
async def admin_remove_user(payload: UserRemovalRequest, admin_user: Dict[str, Any] = Depends(get_current_admin_user)):
    target_email = payload.target_email
    if target_email == admin_user['user_email']:
        raise HTTPException(status_code=400, detail="Admins cannot remove themselves.")
        
    logger.info(f"Admin '{admin_user['user_email']}' removing user '{target_email}'.")
    removal_result = remove_user_by_admin(target_email)
    if "error" in removal_result:
        status_code = 404 if "not found" in removal_result["error"] else 500
        raise HTTPException(status_code=status_code, detail=removal_result["error"])
    return removal_result


@app.get("/admin/recent_tickets")
async def view_recent_tickets(admin_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """
    Admin endpoint to view the most recent support tickets.
    """
    logger.info(f"Admin '{admin_user['user_email']}' is viewing recent tickets.")
    try:
        recent_tickets = get_recent_tickets(limit=30) # Fetch up to 30 tickets
        return recent_tickets
    except Exception as e:
        logger.error(f"Error fetching recent tickets for admin: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve recent tickets.")