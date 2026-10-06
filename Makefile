VERSION := $(shell uv version --short)
SRC := llm_deepseek.py tests/
RUN := uv run --extra test --extra dev

.PHONY: install lint format test record check clean build publish tag deploy

install:
	uv sync --extra test --extra dev

lint:
	$(RUN) ruff check $(SRC)
	$(RUN) ruff format --check $(SRC)

format:
	$(RUN) ruff check --fix $(SRC)
	$(RUN) ruff format $(SRC)

test:
	$(RUN) python -m pytest tests/ -v --tb=short

# Re-record cassettes against the real API (auth header is filtered out).
record:
	@test -n "$$PYTEST_DEEPSEEK_API_KEY" || { echo "set PYTEST_DEEPSEEK_API_KEY"; exit 1; }
	$(RUN) python -m pytest tests/ -v --tb=short --record-mode=rewrite

check: lint test

clean:
	rm -rf dist/ build/ *.egg-info/

build: clean
	uv build
	uvx twine check dist/*

# twine reads credentials from ~/.pypirc (or TWINE_USERNAME/TWINE_PASSWORD).
publish: build
	uvx twine upload dist/*

tag:
	git tag -a v$(VERSION) -m "Release version $(VERSION)"
	git push origin v$(VERSION)

# Bump the version first: uv version --bump patch|minor|major
deploy: check publish tag
