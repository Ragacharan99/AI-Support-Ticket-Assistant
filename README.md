# Ticket Assistant API

A minimal FastAPI service for creating and viewing support tickets. It uses SQLite through SQLAlchemy.

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.
Open `http://127.0.0.1:8000/` for the browser-based review queue.

## Endpoints

- `POST /tickets` creates a ticket.
- `GET /tickets` lists tickets, optionally filtered by `status`.
- `GET /tickets/{id}` gets one ticket.
- `GET /metrics` summarizes ticket volume, human review actions, AI agreement, and workflow timing.

## Tests

Install development dependencies and run the isolated test suite:

```bash
pip install -r requirements-dev.txt
pytest
```

Tests use an in-memory SQLite database and mock the AI service, so they do not modify the local database or call NVIDIA.

## Evaluation

After configuring `API_KEY` and `NVIDIA_MODEL` in `.env`, run the real-provider evaluation separately:

```bash
python -m eval.run_eval
```

It evaluates the 30 labeled tickets in `eval/tickets.json`, prints accuracy metrics and misclassifications, and writes detailed output to `eval/results.json`. It is deliberately not run by pytest.

By default, the runner evaluates an eight-ticket holdout set that is kept out of prompt-development decisions. Use `python -m eval.run_eval --include-development` only when you intentionally want results across all 30 labeled tickets.

## Demo data

To create approximately 15 varied tickets using the real configured AI provider, run:

```bash
python -m scripts.seed_demo
```

The script creates and reviews tickets with mixed review actions and deliberate human corrections, then `GET /metrics` has representative data to display.

