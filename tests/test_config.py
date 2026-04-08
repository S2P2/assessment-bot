import os
import pytest
from unittest.mock import patch
from src.config import load_config, load_interview_data


def test_load_config_reads_env():
    env = {
        "OPENAI_API_KEY": "test-key-123",
        "MODEL": "openai/gpt-test",
        "OPENAI_BASE_URL": "http://localhost:8080",
    }
    with patch.dict(os.environ, env, clear=False):
        config = load_config()
    assert config["api_key"] == "test-key-123"
    assert config["model"] == "openai/gpt-test"
    assert config["base_url"] == "http://localhost:8080"


def test_load_config_defaults_model():
    env = {"OPENAI_API_KEY": "test-key-123"}
    with patch.dict(os.environ, env, clear=False), \
         patch("src.config.load_dotenv"):
        os.environ.pop("MODEL", None)
        config = load_config()
    assert config["model"] == "openai/qwen3.5:4b"


def test_load_config_missing_api_key():
    with patch.dict(os.environ, {}, clear=True), \
         patch("src.config.load_dotenv"):
        with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
            load_config()


def test_load_interview_data_returns_tuple():
    data, questions = load_interview_data("questions.json")
    assert data["interview_id"] == "it-skill-eval-v1"
    assert len(questions) == 3
    assert all("id" in q for q in questions)
    assert all("topic_name" in q for q in questions)


def test_load_interview_data_invalid_path():
    with pytest.raises(SystemExit):
        load_interview_data("nonexistent.json")
