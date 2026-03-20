"""Application package for the paper survey agent."""

from pathlib import Path

from dotenv import load_dotenv

# Load project-level .env before importing modules that use os.getenv().
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
