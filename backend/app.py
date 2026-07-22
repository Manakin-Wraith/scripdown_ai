from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
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
from routes.admin_routes import admin_bp
from routes.email_campaign_routes import campaign_bp
from routes.campaign_webhook_routes import webhook_bp
from routes.schedule_routes import schedule_bp
from routes.segment_routes import segment_bp
from routes.payfast_routes import payfast_bp
from routes.series_routes import series_bp

load_dotenv()

# Validate required environment variables before starting
from utils.env_validator import validate_required_env
validate_required_env()

app = Flask(__name__)

# Both Railway and a local ngrok tunnel sit exactly one reverse-proxy hop in
# front of this app. Without this, request.remote_addr is always the proxy's
# own address (e.g. ngrok's local relay, 127.0.0.1) — not the real client —
# which silently breaks any IP-based check (see payfast_routes.py's PayFast
# source-IP validation on the ITN webhook).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

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
app.register_blueprint(admin_bp)  # Admin routes at /api/admin/* (superuser only)
app.register_blueprint(webhook_bp)  # Campaign webhook routes at /api/campaigns/webhooks/* — must be before campaign_bp
app.register_blueprint(campaign_bp)  # Email campaign routes at /api/campaigns/* (superuser only)
app.register_blueprint(schedule_bp)  # Shooting schedule routes at /api/scripts/:id/schedules/*
app.register_blueprint(segment_bp)  # Timeline segment routes at /api/segments/* and /api/scripts/:id/segments
app.register_blueprint(payfast_bp)  # PayFast ITN webhook at /api/payfast/notify (public — PayFast calls it)
app.register_blueprint(series_bp)  # Series/season grouping routes at /api/series/*, /api/seasons/*, /api/scripts/:id/season

@app.route('/health')
def health_check():
    return {"status": "healthy", "service": "ScripDown Backend"}

if __name__ == '__main__':
    app.run(debug=True, port=5000)
