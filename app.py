import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import re
import base64
from pathlib import Path

import bcrypt
import streamlit as st

from src.langgraphagenticai.database import db_utils
from src.langgraphagenticai.main import load_langgraph_agenticai_app


def valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def render_auth_gate():
    db_utils.init_db()

    if "authenticated_user" not in st.session_state:
        st.session_state.authenticated_user = None

    if st.session_state.authenticated_user:
        return True  # already logged in

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 3rem !important;
        }
        .auth-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 6px;
        }
        .auth-header img {
            width: 40px;
            height: 40px;
            object-fit: contain;
            border-radius: 10px;
        }
        .auth-header h1 {
            font-size: 28px;
            margin: 0;
        }
        .auth-sub {
            text-align: center;
            color: #888;
            font-size: 13px;
            margin-bottom: 1.8rem;
        }
        div[data-testid="stForm"] {
            background-color: #111;
            border: 0.5px solid #1e1e1e;
            border-radius: 12px;
            padding: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    logo_path = Path(__file__).resolve().parent / "assets" / "logo.png"
    logo_html = ""
    if logo_path.exists():
        encoded = base64.b64encode(logo_path.read_bytes()).decode()
        logo_html = f'<img src="data:image/png;base64,{encoded}" />'

    _, center_col, _ = st.columns([1, 2.1, 1])

    with center_col:
        st.markdown(
            f"""
            <div class="auth-header">
                {logo_html}
                <h1>Netra AI</h1>
            </div>
            <p class="auth-sub">See Beyond. Sign in to continue.</p>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)

                if submitted:
                    user = db_utils.get_user_by_username(username.strip())
                    if not user:
                        st.error("No account found with that username.")
                    elif not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                        st.error("Incorrect password.")
                    else:
                        st.session_state.authenticated_user = {
                            "id": user["id"],
                            "username": user["username"],
                            "name": user["name"],
                        }
                        st.rerun()

        with tab_signup:
            with st.form("signup_form"):
                new_name = st.text_input("Full Name")
                new_username = st.text_input("Choose a Username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                signup_submitted = st.form_submit_button("Create Account", use_container_width=True)

                if signup_submitted:
                    if not new_name or not new_username or not new_email or not new_password:
                        st.error("Please fill in all fields.")
                    elif not valid_email(new_email):
                        st.error("Please enter a valid email address.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif db_utils.username_exists(new_username.strip()):
                        st.error("Username already taken.")
                    elif db_utils.email_exists(new_email.strip()):
                        st.error("An account with this email already exists.")
                    else:
                        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        db_utils.create_user(new_username.strip(), new_name.strip(), new_email.strip(), password_hash)
                        st.success("Account created! Please log in from the Login tab.")

    return False


if __name__ == "__main__":
    if render_auth_gate():
        load_langgraph_agenticai_app()