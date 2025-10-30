import pytest
import os


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["authorization"],
        # Ignore date-related headers to prevent cassette mismatches
        "ignore_headers": ["date", "set-cookie"],
        # Match requests based on method, scheme, host, port, path, and query
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
    }


@pytest.fixture(autouse=True)
def mock_deepseek_models(monkeypatch):
    """Mock get_deepseek_models to avoid API calls during tests (especially in CI)"""
    import llm_deepseek

    # Set a dummy API key so register_models doesn't exit early
    monkeypatch.setenv(
        "LLM_DEEPSEEK_KEY",
        os.environ.get("PYTEST_DEEPSEEK_API_KEY", "sk-dummy-key-for-testing"),
    )

    def mock_get_deepseek_models():
        return [
            {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
            {"id": "deepseek-reasoner", "object": "model", "owned_by": "deepseek"},
        ]

    monkeypatch.setattr(llm_deepseek, "get_deepseek_models", mock_get_deepseek_models)
