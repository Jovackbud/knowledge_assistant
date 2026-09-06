import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks, Response, Cookie, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# --- Local Imports ---
from .auth_service import fetch_user_access_profile, update_user_permissions_by_admin, remove_user_by_admin
from .rag_processor import RAGService
from .ticket_system import suggest_ticket_team, create_ticket
from .feedback_system import record_feedback
from .database_utils import (
    init_all_databases, get_recent_tickets, update_ticket_status,
    save_ticket_reply, get_ticket_replies, get_ticket_by_id
)
from .security import create_access_token, get_current_active_user, AuthException
from .document_updater import synchronize_documents, list_admin_documents, upload_admin_document, delete_admin_document
from .utils import sanitize_tag
from .email_service import send_ticket_reply
import fastapi
from .services import shared_services

# --- Configuration and Models ---
from .config import (
    AuthCredentials, RAGRequest, SuggestTeamRequest, CreateTicketRequest, FeedbackRequest,
    UserPermissionsRequest, UserRemovalRequest, UserProfile,
    TICKET_TEAMS, ADMIN_HIERARCHY_LEVEL, KNOWN_DEPARTMENT_TAGS, ALLOWED_ORIGINS,
    FEEDBACK_HELPFUL, FEEDBACK_NOT_HELPFUL
)

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Path Configuration ---
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
STATIC_DIR = PROJECT_ROOT / "static"

# --- Sync concurrency guard ---
_sync_lock = asyncio.Lock()

# --- App Lifecycle (lifespan replaces deprecated on_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_service
    logger.info("--- Application Startup ---")
    try:
        init_all_databases()
        rag_service = RAGService.from_config()
        logger.info("--- Startup Complete ---")
    except Exception as e:
        logger.critical(f"FATAL: Application startup failed: {e}", exc_info=True)
        raise
    yield
    logger.info("--- Application Shutdown ---")


# --- App Setup ---
app = FastAPI(title="AI4AI Knowledge Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],  # FIXED: added DELETE and PATCH
    allow_headers=["*"],
)

rag_service: Optional[RAGService] = None  # single declaration

# --- FastAPI Dependencies for Security ---

def get_current_user_profile(access_token: Optional[str] = Cookie(None)) -> UserProfile:
    if access_token is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: Missing access token cookie."
        )
    try:
        user_profile = get_current_active_user(token=access_token)
        return user_profile
    except AuthException as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_user(current_user: UserProfile = Depends(get_current_user_profile)) -> UserProfile:
    if not current_user.get("is_admin"):
        logger.warning(f"Admin access denied for user '{current_user.get('user_email')}'.")
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden: User does not have admin privileges.")
    logger.info(f"Admin access granted for user '{current_user.get('user_email')}'.")
    return current_user

# --- Security for Scheduled Sync Endpoint ---
api_key_header = APIKeyHeader(name="X-Sync-Token", auto_error=False)
SYNC_SECRET_TOKEN = os.getenv("SYNC_SECRET_TOKEN")

async def get_api_key(api_key: str = Security(api_key_header)):
    if not SYNC_SECRET_TOKEN:
        logger.error("SYNC_SECRET_TOKEN is not set. Sync endpoint is disabled.")
        raise HTTPException(status_code=500, detail="Sync service is not configured.")
    if api_key != SYNC_SECRET_TOKEN:
        logger.warning("Invalid or missing sync token provided.")
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid or missing sync token")
    return api_key

# --- Static Files and Root Endpoint ---
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    html_file_path = STATIC_DIR / "index.html"
    if html_file_path.exists():
        return FileResponse(str(html_file_path))
    raise HTTPException(status_code=404, detail="index.html not found")

# --- Authentication Endpoints ---

@app.post("/auth/login")
async def login(credentials: AuthCredentials, response: Response):
    try:
        user_profile = fetch_user_access_profile(credentials.email)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found or credentials incorrect.")

        access_token = create_access_token(data={"sub": user_profile["user_email"]})

        # Set secure httpOnly cookie — all attributes mirrored for correct browser behaviour
        cookie_kwargs = dict(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="strict",
            secure=True,
            max_age=60 * 60 * 8,
            path="/"
        )
        response.set_cookie(**cookie_kwargs)
        return {"user_profile": user_profile}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Internal server error during login for {credentials.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during login.")

@app.post("/auth/logout")
async def logout(response: Response):
    """Clears the access_token cookie with all matching attributes."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,      # Must match set_cookie attributes or some browsers ignore deletion
        samesite="strict",
        secure=True
    )
    return {"message": "Logout successful"}

@app.post("/auth/me")
async def read_users_me(current_user: UserProfile = Depends(get_current_user_profile)):
    """Session validation endpoint used by the frontend on page load."""
    return {"user_profile": current_user}

# --- Core RAG Endpoint ---
@app.post("/rag/chat")
async def rag_chat(request: RAGRequest, current_user: Dict[str, Any] = Depends(get_current_user_profile)):
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG Service is not available.")

    user_email = current_user.get("user_email")
    logger.info(f"Chat request received from: {user_email}")

    try:
        conversational_rag_chain = rag_service.get_rag_chain(current_user, request.chat_history)

        async def stream_generator():
            try:
                chain_input = {
                    "question": request.prompt,
                    "chat_history": request.chat_history
                }
                final_sources = []
                async for event in conversational_rag_chain.astream_events(chain_input, version="v1"):
                    kind = event["event"]
                    name = event.get("name")

                    if kind == "on_chat_model_stream" and name == "final_answer_llm":
                        chunk_content = event["data"]["chunk"].content
                        if chunk_content:
                            yield f"data: {json.dumps({'answer_chunk': chunk_content})}\n\n"

                    if kind == "on_chain_end" and name == "retriever_and_reranker_step":
                        final_docs = event["data"].get("output", [])
                        if final_docs:
                            final_sources = list(set([doc.metadata.get("source", "Unknown") for doc in final_docs]))

                if final_sources:
                    yield f"data: {json.dumps({'sources': final_sources})}\n\n"

            except Exception as e:
                logger.error(f"Error during RAG stream for user {user_email}: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': 'An error occurred during generation.'})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error creating RAG chain for user {user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing chat request.")


# --- Ticket System Endpoints ---

@app.post("/tickets/suggest_team")
async def suggest_team_endpoint(request: SuggestTeamRequest, _: Dict[str, Any] = Depends(get_current_user_profile)):
    return {"suggested_team": suggest_ticket_team(request.question_text), "available_teams": TICKET_TEAMS}

@app.post("/tickets/create")
async def create_ticket_endpoint(request: CreateTicketRequest, current_user: Dict[str, Any] = Depends(get_current_user_profile)):
    if request.selected_team not in TICKET_TEAMS:
        raise HTTPException(status_code=400, detail="Invalid team selected.")

    ticket_id = create_ticket(
        user_email=current_user["user_email"],
        question=request.question_text,
        chat_history=json.dumps(request.chat_history),
        final_selected_team=request.selected_team
    )
    if ticket_id is not None:
        return {"message": "Ticket created successfully", "ticket_id": ticket_id}
    raise HTTPException(status_code=500, detail="Ticket creation failed in the database.")

# --- Feedback System Endpoint ---

@app.post("/feedback/record")
async def record_feedback_endpoint(request: FeedbackRequest, current_user: Dict[str, Any] = Depends(get_current_user_profile)):
    if request.feedback_type not in [FEEDBACK_HELPFUL, FEEDBACK_NOT_HELPFUL]:
        raise HTTPException(status_code=400, detail="Invalid feedback type provided.")
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
    if _sync_lock.locked():
        return {"message": "Sync already in progress. Skipped duplicate trigger."}
    async def _guarded_sync():
        async with _sync_lock:
            synchronize_documents()
    background_tasks.add_task(_guarded_sync)
    return {"message": "Document synchronization process started in the background."}

# --- Admin Document Management Endpoints ---

@app.get("/admin/documents")
async def get_admin_documents(admin_user: UserProfile = Depends(get_current_admin_user)):
    logger.info(f"Admin '{admin_user['user_email']}' requested document list.")
    docs = list_admin_documents()
    return {"documents": docs}

@app.post("/admin/documents")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department: str = fastapi.Form("GENERAL"),
    hierarchy_level: int = fastapi.Form(0),
    admin_user: UserProfile = Depends(get_current_admin_user)
):
    logger.info(f"Admin '{admin_user['user_email']}' uploading: {file.filename}")
    content = await file.read()

    safe_dept = sanitize_tag(department)
    path_prefix = f"departments/{safe_dept}/level_{hierarchy_level}"
    file_path = f"{path_prefix}/{file.filename}"

    success = upload_admin_document(file_path, content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload document to S3.")

    metadata = {"department_tag": safe_dept, "hierarchy_level_required": hierarchy_level}
    metadata_path = f"{path_prefix}/metadata.json"
    upload_admin_document(metadata_path, json.dumps(metadata).encode('utf-8'))

    if not _sync_lock.locked():
        async def _guarded_sync():
            async with _sync_lock:
                synchronize_documents()
        background_tasks.add_task(_guarded_sync)

    return {"message": f"Document '{file.filename}' uploaded to {path_prefix}. Sync started."}

@app.delete("/admin/documents/{doc_path:path}")
async def delete_document(
    doc_path: str,
    background_tasks: BackgroundTasks,
    admin_user: UserProfile = Depends(get_current_admin_user)
):
    logger.info(f"Admin '{admin_user['user_email']}' deleting: {doc_path}")
    success = delete_admin_document(doc_path)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete '{doc_path}' from S3.")

    if not _sync_lock.locked():
        async def _guarded_sync():
            async with _sync_lock:
                synchronize_documents()
        background_tasks.add_task(_guarded_sync)

    return {"message": f"Document '{doc_path}' deleted. Sync started."}

# --- Admin User Management Endpoints ---

@app.get("/admin/config_tags")
async def get_config_tags(_: UserProfile = Depends(get_current_admin_user)):
    return {"known_department_tags": KNOWN_DEPARTMENT_TAGS}

@app.get("/admin/view_user_permissions/{target_email}")
async def admin_view_user_permissions(target_email: str, admin_user: UserProfile = Depends(get_current_admin_user)):
    logger.info(f"Admin '{admin_user['user_email']}' viewing permissions for '{target_email}'.")
    user_profile = fetch_user_access_profile(target_email)
    if not user_profile:
        raise HTTPException(status_code=404, detail=f"User profile for '{target_email}' not found.")
    return user_profile

@app.post("/admin/user_permissions")
async def admin_update_user_permissions(payload: UserPermissionsRequest, admin_user: UserProfile = Depends(get_current_admin_user)):
    logger.info(f"Admin '{admin_user['user_email']}' updating permissions for '{payload.target_email}'.")
    update_result = update_user_permissions_by_admin(
        target_email=payload.target_email,
        new_permissions=payload.permissions
    )
    if "error" in update_result:
        raise HTTPException(status_code=500, detail=update_result["error"])
    return update_result

@app.post("/admin/remove_user")
async def admin_remove_user(payload: UserRemovalRequest, admin_user: UserProfile = Depends(get_current_admin_user)):
    target_email = payload.target_email
    if target_email == admin_user['user_email']:
        raise HTTPException(status_code=400, detail="Admins cannot remove themselves.")
    logger.info(f"Admin '{admin_user['user_email']}' removing user '{target_email}'.")
    removal_result = remove_user_by_admin(target_email)
    if "error" in removal_result:
        status_code = 404 if "not found" in removal_result["error"] else 500
        raise HTTPException(status_code=status_code, detail=removal_result["error"])
    return removal_result

# --- Admin Ticket Endpoints ---

@app.get("/admin/recent_tickets")
async def view_recent_tickets(admin_user: UserProfile = Depends(get_current_admin_user)):
    logger.info(f"Admin '{admin_user['user_email']}' viewing recent tickets.")
    try:
        return get_recent_tickets(limit=50)
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve recent tickets.")


class TicketStatusUpdate(BaseModel):
    status: str

VALID_TICKET_STATUSES = {"Open", "In Progress", "Resolved", "Closed"}

@app.patch("/admin/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    payload: TicketStatusUpdate,
    admin_user: UserProfile = Depends(get_current_admin_user)
):
    """Admin updates the status of a support ticket."""
    if payload.status not in VALID_TICKET_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {VALID_TICKET_STATUSES}")
    logger.info(f"Admin '{admin_user['user_email']}' setting ticket #{ticket_id} to '{payload.status}'.")
    success = update_ticket_status(ticket_id, payload.status)
    if not success:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found or update failed.")
    return {"message": f"Ticket #{ticket_id} updated to '{payload.status}'."}


class TicketReplyRequest(BaseModel):
    reply_text: str
    subject: str = "Your Support Ticket"


@app.get("/admin/tickets/{ticket_id}/replies")
async def get_replies(
    ticket_id: int,
    admin_user: UserProfile = Depends(get_current_admin_user)
):
    """Returns the reply history for a ticket."""
    replies = get_ticket_replies(ticket_id)
    # Convert datetime objects to ISO strings for JSON serialisation
    for r in replies:
        if hasattr(r.get("timestamp"), "isoformat"):
            r["timestamp"] = r["timestamp"].isoformat()
    return {"replies": replies}


@app.post("/admin/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: int,
    payload: TicketReplyRequest,
    admin_user: UserProfile = Depends(get_current_admin_user)
):
    """
    Send an email reply to the ticket creator and store the reply in the database.
    The reply is stored regardless of whether the email send succeeds,
    so no content is ever silently lost.
    """
    if not payload.reply_text.strip():
        raise HTTPException(status_code=400, detail="Reply text cannot be empty.")

    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")

    admin_email = admin_user["user_email"]
    user_email  = ticket["user_email"]

    # Attempt to send the email
    email_sent = send_ticket_reply(
        ticket_id=ticket_id,
        to_email=user_email,
        subject=payload.subject,
        reply_text=payload.reply_text,
        admin_name=admin_email,
    )

    # Always persist the reply — even if the email failed
    reply_id = save_ticket_reply(
        ticket_id=ticket_id,
        admin_email=admin_email,
        reply_text=payload.reply_text,
        email_sent=email_sent
    )

    if reply_id is None:
        raise HTTPException(status_code=500, detail="Reply could not be saved to the database.")

    if email_sent:
        return {"message": f"Reply sent to {user_email} and saved.", "reply_id": reply_id, "email_sent": True}
    else:
        return {
            "message": f"Reply saved but email could NOT be sent to {user_email}. Check SMTP configuration.",
            "reply_id": reply_id,
            "email_sent": False
        }


# --- Health Check ---
@app.get("/healthz")
async def health_check():
    logger.info("Health check hit.")
    return {"status": "ok"}