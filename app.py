import streamlit as st
import time

from config import TICKET_TEAMS, LLM_MODEL
from rag_processor import RAGService
from ticket_system import suggest_ticket_team, create_ticket
from feedback_system import record_feedback

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Company Knowledge Assistant", layout="wide")
st.title("🤖 Company Knowledge Assistant")
st.caption("Ask questions about company information.")

# --- Session State Initialization ---
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'rag_service' not in st.session_state:
    st.session_state.rag_service = None
if 'show_ticket_form' not in st.session_state:
    st.session_state.show_ticket_form = False
if 'last_question' not in st.session_state:
    st.session_state.last_question = ""
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- Sidebar ---
with st.sidebar:
    st.header("User Profile")
    email_input = st.text_input("Enter your email:", key="email_selector")
    if st.button("Set User"):
        st.session_state.user_email = email_input
        st.session_state.chat_history = []
        st.session_state.show_ticket_form = False
        st.session_state.last_question = ""
        # Initialize RAG service for this user context
        try:
            st.session_state.rag_service = RAGService.from_config()
            st.success(f"User set to {email_input} and RAG service initialized.")
        except Exception as e:
            st.error(f"Failed to initialize RAG service: {e}")
    st.divider()
    if not st.session_state.user_email:
        st.info("Please set your user email to start.", icon="👤")
    else:
        st.info(f"Current user: **{st.session_state.user_email}**")
    st.divider()
    st.caption(f"LLM Model: {LLM_MODEL}")
    st.caption("Vector DB: Milvus")

# --- Chat Interface ---
st.header("Chat Assistant")

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input area
chat_input_disabled = not st.session_state.user_email
if prompt := st.chat_input("Ask your question here...", disabled=chat_input_disabled):
    st.session_state.last_question = prompt
    st.session_state.show_ticket_form = False
    # Add user message to history
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...▌")

        # Real RAG call
        if st.session_state.rag_service:
            try:
                chain = st.session_state.rag_service.get_rag_chain(st.session_state.user_email)
                full_response = chain.invoke(prompt)
            except Exception as e:
                full_response = f"An error occurred during response generation: {e}"
        else:
            full_response = "Error: RAG service not initialized."

        message_placeholder.markdown(full_response)

        # Ticket trigger logic
        offer_ticket = False
        response_lower = full_response.lower()
        failure_phrases = ["i cannot answer", "unable to find", "no relevant documents"]
        if any(phrase in response_lower for phrase in failure_phrases):
            offer_ticket = True

        msg_id = f"msg_{len(st.session_state.chat_history)}"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": full_response,
            "msg_id": msg_id,
            "question": prompt,
            "offer_ticket": offer_ticket
        })
        st.rerun()

# --- Ticket Creation Form ---
if st.session_state.show_ticket_form:
    st.divider()
    st.subheader("Request Further Assistance?")
    suggested_team = suggest_ticket_team(st.session_state.last_question)
    try:
        default_index = TICKET_TEAMS.index(suggested_team)
    except ValueError:
        default_index = 0
    selected_team = st.selectbox(
        "Select Team:", options=TICKET_TEAMS, index=default_index, key="ticket_team_select"
    )
    history_summary = "\n".join([
        f"{msg['role'].capitalize()}: {msg['content'][:150]}..."
        for msg in st.session_state.chat_history[-5:]
    ])
    st.text_area("Ticket Details:", value=
    f"User Email: {st.session_state.user_email}\nQuestion: {st.session_state.last_question}\n\nRecent Chat:\n{history_summary}",
                 height=200, disabled=True)
    if st.button("Submit Ticket", key="submit_ticket_btn"):
        success = create_ticket(
            user_role=st.session_state.user_email,
            question=st.session_state.last_question,
            chat_history_summary=history_summary,
            suggested_team=suggested_team,
            selected_team=selected_team
        )
        if success:
            st.success(f"Ticket submitted to {selected_team}.")
            st.session_state.show_ticket_form = False
            time.sleep(1)
            st.rerun()
        else:
            st.error("Failed to submit ticket.")
