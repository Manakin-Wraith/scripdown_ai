from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from db import db_connection
from routes.script_routes import script_bp
from routes.analysis_routes import analysis_bp
from routes.supabase_routes import supabase_bp
from routes.report_routes import report_bp
from routes.invite_routes import invite_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Database (SQLite - legacy, optional in production)
try:
    db_connection.init_app(app)
except Exception as e:
    print(f"Warning: SQLite DB not initialized: {e}")

# Register Blueprints
app.register_blueprint(script_bp)  # Legacy SQLite routes
app.register_blueprint(analysis_bp)
app.register_blueprint(supabase_bp)  # New Supabase routes at /api/*
app.register_blueprint(report_bp, url_prefix='/api/reports')  # Report generation routes
app.register_blueprint(invite_bp)  # Team invite routes

# Start analysis worker on app startup (only if not in production without SQLite)
try:
    from services.analysis_worker import start_worker
    start_worker()
except Exception as e:
    print(f"Warning: Analysis worker not started: {e}")

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "ScripDown Backend"}

if __name__ == '__main__':
    app.run(debug=True, port=5000)
