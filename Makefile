.PHONY: api ui dev

api:
	uv run uvicorn dealscout.service.api:app --host 0.0.0.0 --port 8000 --reload

ui:
	uv run python -m dealscout.service.ui

dev:
	@echo "Run 'make api' and 'make ui' in two terminals."
