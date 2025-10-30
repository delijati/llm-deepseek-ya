import pytest


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["authorization"],
        # Ignore date-related headers to prevent cassette mismatches
        "ignore_headers": ["date", "set-cookie"],
        # Match requests based on method, scheme, host, port, path, and query
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
    }
