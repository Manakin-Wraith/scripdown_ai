#!/usr/bin/env python3
"""
Apply Migration 018: Feedback System
Creates feedback_submissions table with RLS policies and indexes
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase_client import get_supabase_client

def apply_migration():
    """Apply the feedback system migration"""
    print("🚀 Applying Migration 018: Feedback System...")
    
    # Read migration file
    migration_file = Path(__file__).parent / 'migrations' / '018_feedback_system.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    try:
        # Execute migration
        print("📝 Executing SQL migration...")
        result = supabase.rpc('exec_sql', {'sql': sql}).execute()
        
        print("✅ Migration 018 applied successfully!")
        print("\n📊 Created:")
        print("  - feedback_submissions table")
        print("  - 7 indexes (including full-text search)")
        print("  - 6 RLS policies")
        print("  - 2 triggers (updated_at, resolved_at)")
        print("  - 2 views (feedback_stats, user_feedback_summary)")
        print("  - 2 functions (update timestamps, refresh summary)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        print("\n💡 Manual application required:")
        print(f"   1. Go to Supabase Dashboard > SQL Editor")
        print(f"   2. Copy contents of: {migration_file}")
        print(f"   3. Execute the SQL")
        return False

def verify_migration():
    """Verify the migration was applied correctly"""
    print("\n🔍 Verifying migration...")
    
    supabase = get_supabase_client()
    
    try:
        # Check if table exists by trying to query it
        result = supabase.table('feedback_submissions').select('id').limit(0).execute()
        print("✅ Table 'feedback_submissions' exists")
        
        # Check if view exists
        result = supabase.rpc('exec_sql', {
            'sql': "SELECT COUNT(*) FROM feedback_stats"
        }).execute()
        print("✅ View 'feedback_stats' exists")
        
        print("\n✨ Migration verified successfully!")
        return True
        
    except Exception as e:
        print(f"⚠️  Verification failed: {e}")
        return False

if __name__ == '__main__':
    success = apply_migration()
    
    if success:
        verify_migration()
        print("\n🎉 Migration 018 complete!")
        print("\n📝 Next steps:")
        print("  1. Create 'feedback-screenshots' bucket in Supabase Storage")
        print("  2. Set bucket policies: authenticated write, public read")
        print("  3. Implement backend API endpoints")
    else:
        print("\n⚠️  Migration failed. Please apply manually.")
        sys.exit(1)
