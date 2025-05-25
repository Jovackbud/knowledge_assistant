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

from config import TICKET_TEAMS, LLM_MODEL, DEFAULT_ROLE_TAG
from rag_processor import RAGService
from ticket_system import suggest_ticket_team, create_ticket
from feedback_system import record_feedback
from auth_service import fetch_user_access_profile, get_or_create_test_user_profile


class AppSessionState:
    _DEFAULTS = {
        'user_email': None, 'user_profile_details': None, 'rag_service': None,
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
                # profile = get_or_create_test_user_profile(email_input) # For easy testing
                profile = fetch_user_access_profile(email_input)  # Production
                if profile:
                    session.user_email = email_input
                    session.user_profile_details = profile
                    try:
                        session.rag_service = RAGService.from_config()
                        st.success(f"✅ Auth successful: {session.user_email}")
                        logger.info(
                            f"User {session.user_email} logged in. Profile: {profile['user_hierarchy_level']},{profile['departments']},{profile['projects_membership']},{profile['contextual_roles']}")
                        st.rerun()
                    except Exception as rag_e:
                        st.error(f"🔥 RAG service init error: {rag_e}")
                        logger.error(f"RAG init fail for {session.user_email}: {rag_e}", exc_info=True)
                        session.clear_user_session()
                else:
                    st.error(f"⛔ No access profile for {email_input}.")
                    logger.warning(f"Login fail: No profile for {email_input}.")
            except Exception as e:
                st.error(f"🔥 Login system error: {e}")
                logger.error(f"Login error for {email_input}: {e}", exc_info=True)
                session.clear_user_session()

    if session.user_email and session.user_profile_details:
        st.sidebar.success(f"Logged in: {session.user_email}")
        with st.sidebar.expander("View Access Profile", expanded=False):
            st.write(f"**Hierarchy Lvl:** {session.user_profile_details.get('user_hierarchy_level')}")
            st.write(f"**Depts:** {', '.join(session.user_profile_details.get('departments', [])) or 'N/A'}")
            st.write(f"**Projects:** {', '.join(session.user_profile_details.get('projects_membership', [])) or 'N/A'}")
            context_roles_str = "; ".join([f"{ctx}: {', '.join(roles)}" for ctx, roles in
                                           session.user_profile_details.get('contextual_roles', {}).items()])
            st.write(f"**Context Roles:** {context_roles_str or 'N/A'}")
        if st.sidebar.button("Logout", key="logout_btn_key"):
            logger.info(f"User {session.user_email} logged out.")
            session.clear_user_session()
            st.rerun()
    elif not session.user_email:
        st.sidebar.info("Please login.")

if session.user_email and session.rag_service:
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
                chain = session.rag_service.get_rag_chain(session.user_email)
                full_response = chain.invoke(prompt)
                ph.markdown(full_response)
            except Exception as e:
                full_response = f"⚠️ System Error: {e}"
                ph.markdown(full_response)
                logger.error(f"RAG chain error for {session.user_email}, prompt '{prompt}': {e}", exc_info=True)
            session.current_answer = full_response
            session.chat_history.append({"role": "assistant", "content": full_response})
            st.rerun()

    if session.current_answer and not session.feedback_given_for_current_answer:
        st.markdown("---")
        cols = st.columns([1, 1, 5, 2])
        if cols[0].button("👍 Helpful", key="helpful_key"):
            if record_feedback(session.user_email, session.current_question, session.current_answer, "👍"):
                st.toast("Feedback saved!", icon="😊")
                session.feedback_given_for_current_answer = True;
                st.rerun()
            else:
                st.toast("Feedback save error.", icon="⚠️")
        if cols[1].button("👎 Not Helpful", key="nothelpful_key"):
            if record_feedback(session.user_email, session.current_question, session.current_answer, "👎"):
                st.toast("Feedback saved. Consider a ticket.", icon="😕")
                session.feedback_given_for_current_answer = True;
                st.rerun()
            else:
                st.toast("Feedback save error.", icon="⚠️")
        if cols[3].button("🎫 Create Ticket", key="ticket_btn_main_key", help="Need more help?"):
            session.show_ticket_form = True;
            st.rerun()

    if session.show_ticket_form:
        with st.form("ticket_form_key", clear_on_submit=True):
            st.subheader("📝 New Support Ticket")
            q_ticket = st.text_area("Issue/Question:", value=session.current_question or "", height=100,
                                    key="ticket_q_key")
            s_team = suggest_ticket_team(q_ticket)
            teams_list = TICKET_TEAMS[:]
            try:
                team_idx = teams_list.index(s_team)
            except ValueError:
                if "General" not in teams_list: teams_list.append("General")
                team_idx = teams_list.index("General")
            sel_team = st.selectbox("Team:", options=teams_list, index=team_idx, key="ticket_team_key")

            submit_col, cancel_col = st.columns(2)
            submit_ok = submit_col.form_submit_button("Submit Ticket")
            cancel_form = cancel_col.form_submit_button("Cancel")

            if submit_ok:
                if not q_ticket.strip():
                    st.error("Description empty.")
                else:
                    hist = session.chat_history[-10:] # Capture last 10 messages for context
                    # Ensure chat history is serialized to JSON string
                    chat_history_json = json.dumps(hist) 
                    if create_ticket(session.user_email, q_ticket, chat_history_json, sel_team):
                        st.success(f"✅ Ticket created for '{sel_team}'!")
                        logger.info(f"Ticket by {session.user_email} for {sel_team}, Q: {q_ticket[:50]}")
                        session.show_ticket_form = False;
                        st.rerun()
                    else:
                        st.error("⚠️ Ticket creation failed."); logger.error(f"Ticket fail for {session.user_email}")
            if cancel_form: session.show_ticket_form = False; st.rerun()
elif not session.user_email:
    st.warning("🔑 Please authenticate in the sidebar.")
else:
    st.error("🛠️ Assistant service unavailable. Try login again or contact support.")