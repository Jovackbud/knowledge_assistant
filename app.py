# app.py
import streamlit as st
import time
from typing import Optional, List, Dict
from config import TICKET_TEAMS, LLM_MODEL
from rag_processor import RAGService
from ticket_system import suggest_ticket_team, create_ticket
from feedback_system import record_feedback
from auth_service import fetch_user_access_profile

# --- Type-Annotated Session State ---
if 'user_email' not in st.session_state:
    st.session_state.user_email: Optional[str] = None

if 'rag_service' not in st.session_state:
    st.session_state.rag_service: Optional[RAGService] = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history: List[Dict[str, str]] = []

# --- Streamlit UI Configuration ---
st.set_page_config(
    page_title="Company Knowledge Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🤖 Company Knowledge Assistant")
st.caption("Secure internal knowledge base with RBAC controls")

# --- Authentication Sidebar ---
with st.sidebar:
    st.header("🔐 Authentication")
    email = st.text_input("Work Email Address", key="auth_email")

    if st.button("Login / Refresh Session"):
        # Clear previous state completely
        st.session_state.clear()

        # Validate email format
        if not email or "@" not in email:
            st.error("❌ Invalid email format")
        else:
            try:
                profile = fetch_user_access_profile(email)
                if profile:
                    st.session_state.user_email = email
                    st.session_state.rag_service = RAGService.from_config()
                    st.success("✅ Authentication successful!")
                else:
                    st.error("⛔ No access profile found")
            except Exception as e:
                st.error(f"🔥 System error: {str(e)}")
                st.session_state.clear()

# --- Main Chat Interface ---
if st.session_state.user_email:
    # Display Chat History
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle User Input
    if prompt := st.chat_input("Ask your question..."):
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("▌")

            try:
                if not st.session_state.rag_service:
                    raise ValueError("RAG service not initialized")

                chain = st.session_state.rag_service.get_rag_chain(
                    st.session_state.user_email
                )
                full_response = chain.invoke(prompt)
            except Exception as e:
                full_response = f"⚠️ System Error: {str(e)}"

            response_placeholder.markdown(full_response)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": full_response
            })
else:
    st.warning("Please authenticate with your company email to continue")

# --- Ticket System Integration (To be implemented next) ---