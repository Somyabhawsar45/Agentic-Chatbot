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

            # max_retries: Groq's free tier allows only ~8,000 tokens/minute per model. When a burst
            # (e.g. Deep Research's parallel researchers) hits that, the API answers 429 with a
            # retry-after time of a few seconds; the client honours it, but the default of 2 retries
            # was not enough, so the whole run failed.
            llm = ChatGroq(api_key=groq_api_key, model=selected_groq_model, streaming=True, max_retries=6)

        except Exception as e:
            raise ValueError(f"Error Occurred With Exception: {e}")
        return llm