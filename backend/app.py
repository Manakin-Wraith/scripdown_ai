from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Supabase routes only
from routes.supabase_routes import supabase_bp
from routes.report_routes import report_bp
from routes.invite_routes import invite_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# Register Blueprints (Supabase-based)
app.register_blueprint(supabase_bp)  # Main Supabase routes at /api/*
app.register_blueprint(report_bp, url_prefix='/api/reports')
app.register_blueprint(invite_bp)

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "ScripDown Backend"}

if __name__ == '__main__':
    app.run(debug=True, port=5000)
