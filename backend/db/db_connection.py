import sqlite3
from flask import current_app, g
import os

DB_PATH = 'db/script_breakdown.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)

def init_db():
    """Initialize the database with schema."""
    db = sqlite3.connect(DB_PATH)
    with open('db/schema_sqlite.sql', 'r') as f:
        db.executescript(f.read())
    db.commit()
    db.close()

