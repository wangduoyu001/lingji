# Windows DB Lifecycle Report

Research: SQLite file locks on Windows require explicit conn.close(), cursor.close(), TestClient context. Examples from FastAPI, sqlite3 docs, SQLAlchemy.

Minimal fix applied.