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

## Endpoints

- `POST /tickets` creates a ticket.
- `GET /tickets` lists tickets, optionally filtered by `status`.
- `GET /tickets/{id}` gets one ticket.

