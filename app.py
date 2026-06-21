import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

from src.langgraphagenticai.main import load_langgraph_agenticai_app

if __name__=="__main__":
    load_langgraph_agenticai_app()