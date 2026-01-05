"""
Run email tracking table migration.
This creates the email_tracking table in Supabase.
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

from db.supabase_client import SupabaseDB

def run_migration():
    """Run the email tracking table migration."""
    
    print("🔧 Running email_tracking table migration...")
    print("=" * 50)
    
    # Read migration SQL
    migration_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'db', 
        'migrations', 
        'create_email_tracking.sql'
    )
    
    try:
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        print(f"📄 Migration file: {migration_path}")
        print(f"📝 SQL length: {len(sql)} characters")
        print("\n⚙️  Executing migration...")
        
        # Connect to Supabase
        db = SupabaseDB()
        
        # Execute SQL via RPC (Supabase doesn't support direct SQL execution)
        # We'll need to run this manually in Supabase SQL Editor
        print("\n⚠️  Note: Supabase Python client doesn't support direct SQL execution.")
        print("\n📋 Please run this migration manually:")
        print("\n1. Go to: https://supabase.com/dashboard/project/twzfaizeyqwevmhjyicz/sql")
        print("2. Copy the SQL from: backend/db/migrations/create_email_tracking.sql")
        print("3. Paste and run in the SQL Editor")
        print("\nOr use the Supabase CLI:")
        print("   supabase db push")
        
        print("\n✅ Instructions provided!")
        
    except FileNotFoundError:
        print(f"❌ Error: Migration file not found at {migration_path}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


if __name__ == '__main__':
    run_migration()
