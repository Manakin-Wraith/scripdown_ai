from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Supabase routes only
from routes.supabase_routes import supabase_bp
from routes.report_routes import report_bp
from routes.invite_routes import invite_bp
from routes.analysis_routes import analysis_bp
from routes.auth_routes import auth_bp
from routes.script_routes import script_bp
from routes.beta_routes import beta_bp
from routes.email_analytics_routes import analytics_bp

load_dotenv()

app = Flask(__name__)

# Configure CORS for production - allow all origins for now
# Flask-CORS handles preflight OPTIONS requests automatically
CORS(app, 
     origins=["http://localhost:5173", "http://localhost:3000", "https://app.slateone.studio"],
     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True,
     expose_headers=["Content-Type", "Authorization", "Content-Disposition"]
)

# Register Blueprints (Supabase-based)
app.register_blueprint(supabase_bp)  # Main Supabase routes at /api/*
app.register_blueprint(report_bp, url_prefix='/api/reports')
app.register_blueprint(invite_bp)
app.register_blueprint(analysis_bp)  # Analysis routes at /api/analysis/*
app.register_blueprint(auth_bp)  # Auth routes at /api/auth/*
app.register_blueprint(script_bp, url_prefix='/api')  # Script routes including stripboard PDF
app.register_blueprint(beta_bp)  # Beta launch routes at /api/beta/*
app.register_blueprint(analytics_bp)  # Email analytics routes at /api/email-analytics/*

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "ScripDown Backend"}

if __name__ == '__main__':
    app.run(debug=True, port=5000)
