import os
import tempfile

import streamlit as st

from src.langgraphagenticai.database import db_utils


def index_uploaded_pdf(uploaded_file, usecase: str) -> bool:
    """
    Index a PDF attached with the 📎 button of the chat box into the current
    conversation (creating the conversation if needed). Returns True on success.
    """
    from src.langgraphagenticai.rag import pdf_rag_utils

    if st.session_state.get("pdf_indexed_for") == (st.session_state.current_conversation_id, uploaded_file.name):
        return True  # same file re-sent with the next message

    with st.spinner(f"Reading and indexing {uploaded_file.name}…"):
        try:
            if st.session_state.current_conversation_id is None:
                user_id = st.session_state.authenticated_user["id"]
                title = db_utils.make_title(os.path.splitext(uploaded_file.name)[0])
                st.session_state.current_conversation_id = db_utils.create_conversation(user_id, usecase, title)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name
            try:
                n_chunks = pdf_rag_utils.build_index(
                    tmp_path, st.session_state.current_conversation_id, filename=uploaded_file.name
                )
            finally:
                os.remove(tmp_path)
        except Exception as e:
            st.error(f"Couldn't read that PDF: {e}")
            return False

    st.session_state.pdf_indexed_for = (st.session_state.current_conversation_id, uploaded_file.name)
    # shown by loadui on the next rerun (survives st.rerun)
    st.session_state.pending_toast = f"📎 {uploaded_file.name} is ready · {n_chunks} passages indexed"
    return True
