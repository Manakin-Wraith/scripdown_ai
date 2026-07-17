"""
Environment Variable Validator for ScripDown AI Backend

Validates that all required environment variables are set before the application starts.
This prevents runtime errors due to missing configuration.
"""

import os
import sys


# Required environment variables with descriptions
REQUIRED_VARS = {
    'SUPABASE_URL': 'Supabase project URL (e.g., https://xxx.supabase.co)',
    'SUPABASE_ANON_KEY': 'Supabase anonymous/public key for client operations',
    'SUPABASE_SERVICE_KEY': 'Supabase service role key for admin operations (bypasses RLS)',
    'RESEND_API_KEY': 'Resend email service API key for sending emails',
    'PAYFAST_MERCHANT_ID': 'PayFast merchant ID for checkout signing',
    'PAYFAST_MERCHANT_KEY': 'PayFast merchant key for checkout signing',
}

# Required only outside PAYFAST_SANDBOX mode: PayFast's own shared sandbox
# demo merchant (10000100) has no passphrase configured, so a real value
# can't be required for local sandbox testing — but a live deploy must set
# one, since signatures are enforced.
SANDBOX_EXEMPT_VARS = {
    'PAYFAST_PASSPHRASE': 'PayFast security passphrase — required outside PAYFAST_SANDBOX mode, signatures are enforced',
}

# Optional but recommended environment variables
RECOMMENDED_VARS = {
    'GEMINI_API_KEY': 'Google Gemini API key for AI analysis',
    'OPENAI_API_KEY': 'OpenAI API key (alternative to Gemini)',
    'SUPABASE_JWT_SECRET': 'Legacy HS256 JWT secret (optional — JWKS endpoint used by default)',
}


def validate_required_env():
    """
    Validate that all required environment variables are set.
    
    Exits the application with error code 1 if any required variables are missing.
    Prints warnings for missing recommended variables.
    """
    missing_required = []
    missing_recommended = []

    # Check required variables
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var)
        if not value:
            missing_required.append(f"  ❌ {var}: {description}")

    # Sandbox-exempt vars: required unless PAYFAST_SANDBOX=true
    if os.getenv('PAYFAST_SANDBOX', 'false').lower() != 'true':
        for var, description in SANDBOX_EXEMPT_VARS.items():
            value = os.getenv(var)
            if not value:
                missing_required.append(f"  ❌ {var}: {description}")

    # Check recommended variables
    for var, description in RECOMMENDED_VARS.items():
        value = os.getenv(var)
        if not value:
            missing_recommended.append(f"  ⚠️  {var}: {description}")
    
    # Handle missing required variables (critical)
    if missing_required:
        print("\n" + "="*70)
        print("❌ CRITICAL: Missing required environment variables")
        print("="*70)
        print("\n".join(missing_required))
        print("\n📝 Please set these in your .env file")
        print("   See backend/.env.example for reference")
        print("="*70 + "\n")
        sys.exit(1)
    
    # Handle missing recommended variables (warning only)
    if missing_recommended:
        print("\n" + "="*70)
        print("⚠️  WARNING: Missing recommended environment variables")
        print("="*70)
        print("\n".join(missing_recommended))
        print("\n📝 Application will start, but some features may not work")
        print("   Set these in your .env file for full functionality")
        print("="*70 + "\n")
    
    # Success message
    if not missing_required and not missing_recommended:
        print("✅ All environment variables validated successfully")


def get_env_summary():
    """
    Get a summary of environment variable status.
    
    Returns:
        dict: Summary with 'required', 'recommended', and 'missing' keys
    """
    summary = {
        'required': {},
        'recommended': {},
        'missing_required': [],
        'missing_recommended': []
    }
    
    for var in REQUIRED_VARS.keys():
        value = os.getenv(var)
        summary['required'][var] = bool(value)
        if not value:
            summary['missing_required'].append(var)
    
    for var in RECOMMENDED_VARS.keys():
        value = os.getenv(var)
        summary['recommended'][var] = bool(value)
        if not value:
            summary['missing_recommended'].append(var)
    
    return summary


if __name__ == '__main__':
    """Run validation when executed directly"""
    validate_required_env()
    print("\n✅ Environment validation passed!")
