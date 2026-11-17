from src.langgraphagenticai.ui.uiconfigfile import Config


def test_config_loads_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)          # a folder that has no ui config of its own
    config = Config()
    assert "Netra Agent" in config.get_usecase_options()
    assert config.get_groq_model_options()
    assert config.get_llm_options() == ["Groq"]
