import os
os.environ["STREAMLIT_WATCHED_MODULES"] = "false"

import streamlit as st
import time
import json
import logging
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("KnowledgeAssistantApp")

try:
    from database_utils import init_all_databases, _create_sample_users_if_not_exist

    init_all_databases()
    _create_sample_users_if_not_exist()
except Exception as e:
    logger.critical(f"CRITICAL: Database initialization failed: {e}", exc_info=True)
    st.error(f"Application critical error: Database initialization failed. Check logs. Error: {e}")
    st.stop()

from config import LLM_MODEL, DEFAULT_ROLE_TAG # Removed TICKET_TEAMS import, will get from API
# from rag_processor import RAGService # Removed RAGService import
# from ticket_system import suggest_ticket_team, create_ticket # Removed direct ticket system imports
# from feedback_system import record_feedback # Removed direct feedback system import
# Removed direct auth_service imports: fetch_user_access_profile, get_or_create_test_user_profile
import requests # Added for API calls

FASTAPI_BASE_URL = "http://localhost:8000" # Added: Make this configurable later


class AppSessionState:
    _DEFAULTS = {
        'user_email': None, 'user_profile_details': None, # 'rag_service': None, # Removed rag_service from session
        'chat_history': [], 'current_question': None, 'current_answer': None,
        'feedback_given_for_current_answer': False, 'show_ticket_form': False,
    }

    def __init__(self):
        for key, val in self._DEFAULTS.items():
            if key not in st.session_state: st.session_state[key] = val

    def __getattr__(self, name: str) -> Any:
        return st.session_state[name] if name in self._DEFAULTS else super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any):
        if name in self._DEFAULTS:
            st.session_state[name] = value
        else:
            super().__setattr__(name, value)

    def clear_user_session(self):
        for key, val in self._DEFAULTS.items(): st.session_state[key] = val
        logger.info("User session cleared.")


session = AppSessionState()

st.set_page_config(page_title="Company Knowledge Assistant", layout="wide", initial_sidebar_state="expanded")
st.title("🤖 Company Knowledge Assistant")
st.caption(f"Secure Internal Knowledge | LLM: {LLM_MODEL}")

with st.sidebar:
    st.header("🔐 Authentication")
    email_input = st.text_input("Work Email Address", key="auth_email_key", value=session.user_email or "",
                                placeholder="user@example.com")

    if st.button("Login / Refresh Session", key="login_btn_key"):
        if not email_input or "@" not in email_input:
            st.error("❌ Invalid email format.")
        else:
            session.clear_user_session()
            st.info(f"Attempting login: {email_input}...")
            try:
                login_url = f"{FASTAPI_BASE_URL}/auth/login"
                response = requests.post(login_url, json={"email": email_input})

                if response.status_code == 200:
                    profile = response.json()
                    session.user_email = email_input
                    session.user_profile_details = profile
                    # Removed RAGService initialization from here
                    st.success(f"✅ Auth successful: {session.user_email}")
                    logger.info(f"User {session.user_email} logged in. Profile keys: {list(profile.keys())}")
                    st.rerun()
                elif response.status_code == 404:
                    st.error(f"⛔ No access profile for {email_input}. User not found.")
                    logger.warning(f"Login fail (404): No profile for {email_input}.")
                else:
                    st.error(f"🔥 Login API error: {response.status_code} - {response.text}")
                    logger.error(f"Login API error for {email_input}: {response.status_code} - {response.text}")
                    session.clear_user_session()
            except requests.exceptions.ConnectionError as conn_e:
                st.error(f"🔥 Connection error: Could not connect to the authentication service. {conn_e}")
                logger.error(f"Connection error during login for {email_input}: {conn_e}", exc_info=True)
                session.clear_user_session()
            except Exception as e:
                st.error(f"🔥 An unexpected error occurred during login: {e}")
                logger.error(f"Unexpected login error for {email_input}: {e}", exc_info=True)
                session.clear_user_session()

    if session.user_email and session.user_profile_details:
        st.sidebar.success(f"Logged in: {session.user_email}")
        with st.sidebar.expander("View Access Profile", expanded=False):
            # Ensure keys match what the API returns. Example:
            st.write(f"**Hierarchy Lvl:** {session.user_profile_details.get('hierarchy_level', 'N/A')}") # Adjusted key
            st.write(f"**Depts:** {', '.join(session.user_profile_details.get('department_tags', [])) or 'N/A'}") # Adjusted key
            st.write(f"**Projects:** {', '.join(session.user_profile_details.get('project_tags', [])) or 'N/A'}") # Adjusted key
            # Context roles might need adjustment based on actual API response structure
            context_roles = session.user_profile_details.get('role_tags', []) # Adjusted key
            st.write(f"**Roles:** {', '.join(context_roles) or 'N/A'}") # Simplified display for roles
        if st.sidebar.button("Logout", key="logout_btn_key"):
            logger.info(f"User {session.user_email} logged out.")
            session.clear_user_session()
            st.rerun()
    elif not session.user_email:
        st.sidebar.info("Please login.")

# Changed condition: session.rag_service is no longer checked here
if session.user_email and session.user_profile_details: 
    for msg in session.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Ask your question...", key="chat_in_key"):
        session.current_question = prompt
        session.current_answer = None
        session.feedback_given_for_current_answer = False
        session.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            ph = st.empty()
            ph.markdown("Thinking... ▌")
            full_response = ""
            try:
                rag_url = f"{FASTAPI_BASE_URL}/rag/chat"
                payload = {"email": session.user_email, "prompt": prompt}
                api_response = requests.post(rag_url, json=payload)

                if api_response.status_code == 200:
                    full_response = api_response.json().get("response", "⚠️ No response content from API.")
                elif api_response.status_code == 404: # Specific handling for user not found in RAG
                    full_response = f"⚠️ RAG Error: User profile not found for {session.user_email}. Please re-login."
                    logger.warning(f"RAG API error 404 for {session.user_email}, prompt '{prompt}'")
                else:
                    full_response = f"⚠️ RAG API Error: {api_response.status_code} - {api_response.text}"
                    logger.error(f"RAG API error for {session.user_email}, prompt '{prompt}': {api_response.status_code} - {api_response.text}")
                ph.markdown(full_response)
            except requests.exceptions.ConnectionError as conn_e:
                full_response = f"⚠️ Connection Error: Could not connect to RAG service. {conn_e}"
                ph.markdown(full_response)
                logger.error(f"RAG connection error for {session.user_email}, prompt '{prompt}': {conn_e}", exc_info=True)
            except Exception as e:
                full_response = f"⚠️ System Error during RAG call: {e}"
                ph.markdown(full_response)
                logger.error(f"RAG system error for {session.user_email}, prompt '{prompt}': {e}", exc_info=True)
            
            session.current_answer = full_response
            session.chat_history.append({"role": "assistant", "content": full_response})
            st.rerun()

    if session.current_answer and not session.feedback_given_for_current_answer:
        st.markdown("---")
        cols = st.columns([1, 1, 5, 2])

        def _handle_feedback(feedback_type_str: str):
            feedback_url = f"{FASTAPI_BASE_URL}/feedback/record"
            payload = {
                "email": session.user_email,
                "question": session.current_question,
                "answer": session.current_answer,
                "feedback_type": feedback_type_str
            }
            try:
                response = requests.post(feedback_url, json=payload)
                if response.status_code == 200: # Assuming 200 for successful recording
                    st.toast(f"Feedback '{feedback_type_str}' saved!", icon="😊" if feedback_type_str == "👍" else "😕")
                    session.feedback_given_for_current_answer = True
                    st.rerun()
                else:
                    st.toast(f"Feedback save error (HTTP {response.status_code}): {response.text}", icon="⚠️")
                    logger.error(f"Feedback API error: {response.status_code} - {response.text}")
            except requests.exceptions.ConnectionError as conn_e:
                st.toast(f"Feedback save error: Connection error. {conn_e}", icon="⚠️")
                logger.error(f"Feedback connection error: {conn_e}", exc_info=True)
            except Exception as e:
                st.toast(f"Feedback save error: An unexpected error occurred. {e}", icon="⚠️")
                logger.error(f"Feedback unexpected error: {e}", exc_info=True)

        if cols[0].button("👍 Helpful", key="helpful_key"):
            _handle_feedback("👍")
        
        if cols[1].button("👎 Not Helpful", key="nothelpful_key"):
            _handle_feedback("👎")

        if cols[3].button("🎫 Create Ticket", key="ticket_btn_main_key", help="Need more help?"):
            session.show_ticket_form = True;
            st.rerun()

    if session.show_ticket_form:
        with st.form("ticket_form_key", clear_on_submit=True):
            st.subheader("📝 New Support Ticket")
            q_ticket = st.text_area("Issue/Question:", value=session.current_question or "", height=100,
                                    key="ticket_q_key")
            
            # Call /tickets/suggest_team API
            s_team = "General" # Default
            teams_list = ["General"] # Default
            team_idx = 0 # Default
            try:
                suggest_url = f"{FASTAPI_BASE_URL}/tickets/suggest_team"
                suggest_response = requests.post(suggest_url, json={"question_text": q_ticket})
                if suggest_response.status_code == 200:
                    suggest_data = suggest_response.json()
                    s_team = suggest_data.get("suggested_team", "General")
                    teams_list = suggest_data.get("available_teams", ["General"])
                    if not teams_list: teams_list = ["General"] # Ensure there's always a list
                else:
                    st.warning(f"Could not get team suggestion (HTTP {suggest_response.status_code}). Defaulting to General.")
                    logger.warning(f"Suggest team API error: {suggest_response.status_code} - {suggest_response.text}")
            except requests.exceptions.ConnectionError as conn_e:
                st.warning(f"Connection error for team suggestion: {conn_e}. Defaulting...")
                logger.error(f"Suggest team connection error: {conn_e}", exc_info=True)
            except Exception as e:
                st.warning(f"Error getting team suggestion: {e}. Defaulting...")
                logger.error(f"Suggest team general error: {e}", exc_info=True)

            try:
                if s_team in teams_list:
                    team_idx = teams_list.index(s_team)
                elif "General" in teams_list: # Fallback to General if suggested not in list
                    team_idx = teams_list.index("General")
                    s_team = "General"
                # If General is also not in teams_list (should not happen if API behaves), idx remains 0
            except ValueError: # Should not happen if teams_list is populated
                 if "General" in teams_list: team_idx = teams_list.index("General")
                 else: team_idx = 0 # Fallback, list might be empty
                 s_team = teams_list[team_idx] if teams_list else "General"


            sel_team = st.selectbox("Team:", options=teams_list, index=team_idx, key="ticket_team_key")

            submit_col, cancel_col = st.columns(2)
            submit_ok = submit_col.form_submit_button("Submit Ticket")
            cancel_form = cancel_col.form_submit_button("Cancel")

            if submit_ok:
                if not q_ticket.strip():
                    st.error("Description empty.")
                else:
                    hist = session.chat_history[-10:] # Capture last 10 messages for context
                    chat_history_json = json.dumps(hist)
                    
                    create_ticket_url = f"{FASTAPI_BASE_URL}/tickets/create"
                    payload = {
                        "email": session.user_email,
                        "question_text": q_ticket,
                        "chat_history_json": chat_history_json,
                        "selected_team": sel_team
                    }
                    try:
                        ticket_response = requests.post(create_ticket_url, json=payload)
                        if ticket_response.status_code == 200: # Assuming 200 for success
                            ticket_data = ticket_response.json()
                            st.success(f"✅ Ticket created for '{sel_team}'! Ticket ID: {ticket_data.get('ticket_id')}")
                            logger.info(f"Ticket by {session.user_email} for {sel_team}, Q: {q_ticket[:50]}, ID: {ticket_data.get('ticket_id')}")
                            session.show_ticket_form = False
                            st.rerun()
                        elif ticket_response.status_code == 400: # Specific for invalid team
                             st.error(f"⚠️ Ticket creation failed: {ticket_response.json().get('detail', 'Bad request')}")
                             logger.warning(f"Ticket creation fail (400) for {session.user_email}: {ticket_response.text}")
                        else:
                            st.error(f"⚠️ Ticket creation failed (HTTP {ticket_response.status_code}): {ticket_response.text}")
                            logger.error(f"Ticket creation fail for {session.user_email}: {ticket_response.status_code} - {ticket_response.text}")
                    except requests.exceptions.ConnectionError as conn_e:
                        st.error(f"⚠️ Ticket creation failed: Connection error. {conn_e}")
                        logger.error(f"Ticket creation connection error for {session.user_email}: {conn_e}", exc_info=True)
                    except Exception as e:
                        st.error(f"⚠️ Ticket creation failed: An unexpected error occurred. {e}")
                        logger.error(f"Ticket creation unexpected error for {session.user_email}: {e}", exc_info=True)

            if cancel_form: session.show_ticket_form = False; st.rerun()
elif not session.user_email:
    st.warning("🔑 Please authenticate in the sidebar.")
else:
    st.error("🛠️ Assistant service unavailable. Try login again or contact support.")