from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Supabase routes only
from routes.supabase_routes import supabase_bp
from routes.report_routes import report_bp
from routes.invite_routes import invite_bp
from routes.analysis_routes import analysis_bp

load_dotenv()

app = Flask(__name__)

# Configure CORS for production
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://app.slateone.studio",
            "https://*.vercel.app"
        ],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Register Blueprints (Supabase-based)
app.register_blueprint(supabase_bp)  # Main Supabase routes at /api/*
app.register_blueprint(report_bp, url_prefix='/api/reports')
app.register_blueprint(invite_bp)
app.register_blueprint(analysis_bp)  # Analysis routes at /api/analysis/*

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "ScripDown Backend"}

if __name__ == '__main__':
    app.run(debug=True, port=5000)
