"""Application configuration loaded from the local .env file."""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ticket_assistant.db")
API_KEY = os.getenv("API_KEY")

