from fastapi import FastAPI, HTTPException
from src.auth_service import fetch_user_access_profile
from src.config import AuthCredentials, RAGRequest, SuggestTeamRequest, CreateTicketRequest, FeedbackRequest, TICKET_TEAMS
from src.rag_processor import RAGService
from src.ticket_system import suggest_ticket_team, create_ticket
from src.feedback_system import record_feedback
from src.database_utils import init_all_databases, _create_sample_users_if_not_exist # Added
import logging # Added

app = FastAPI()

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.get("/")
async def root():
    return {"message": "FastAPI is running"}

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
            chat_history_json=request.chat_history_json,
            selected_team=request.selected_team
        )
        if ticket_id:
            return {"message": "Ticket created successfully", "ticket_id": ticket_id}
        else:
            # This case might indicate an issue within create_ticket that didn't raise an exception
            raise HTTPException(status_code=500, detail="Ticket creation failed for an unknown reason.")
    except HTTPException as http_exc: # Re-raise HTTPException
        raise http_exc
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Error creating ticket: {str(e)}")

# --- Feedback System Endpoint ---

@app.post("/feedback/record")
async def record_feedback_endpoint(request: FeedbackRequest):
    try:
        record_feedback(
            user_email=request.email,
            question=request.question,
            answer=request.answer,
            feedback_type=request.feedback_type
        )
        return {"message": "Feedback recorded successfully"}
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")
