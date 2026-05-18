# DealScout

AI deal-flow analyst. Given a startup URL or pitch-deck PDF, produces a
structured investment memo with a Pass / Track / Meet recommendation.

Built on the OpenAI Agents SDK, pointed at Google Gemini via its
OpenAI-compatible endpoint. 

## Quickstart

```bash
uv sync
cp .env.example .env          # then add a real GEMINI_API_KEY
docker compose up -d langfuse # optional, traces at http://localhost:3000
uv run python -m dealscout.smoke
```

## Tests

```bash
uv run pytest tests/unit                       # fast, no network
uv run pytest tests/integration -m integration # real Gemini, needs a key
```
