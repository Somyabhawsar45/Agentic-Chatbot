import os
import streamlit as st
from langchain_groq import ChatGroq

class GroqLLM:
    def __init__(self, user_contols_input):
        self.user_controls_input = user_contols_input

    def get_llm_model(self):
        try:
            groq_api_key = self.user_controls_input.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
            selected_groq_model = self.user_controls_input.get("selected_groq_model")

            if not groq_api_key:
                st.error("Please enter the Groq API key")
                return None

            llm = ChatGroq(api_key=groq_api_key, model=selected_groq_model,streaming=True)

        except Exception as e:
            raise ValueError(f"Error Occurred With Exception: {e}")
        return llm