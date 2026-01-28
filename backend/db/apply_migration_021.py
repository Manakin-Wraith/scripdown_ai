#!/usr/bin/env python3
"""
Apply Migration 021: Add Email Reply Tracking to Feedback
Adds last_reply_sent timestamp to track when admin replies are sent
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from supabase_client import get_supabase_admin

def apply_migration():
    """Apply migration 021"""
    print("=" * 80)
    print("APPLYING MIGRATION 021: Add Email Reply Tracking")
    print("=" * 80)
    
    supabase = get_supabase_admin()
    
    # Read migration file
    migration_file = Path(__file__).parent / 'migrations' / '021_add_feedback_reply_tracking.sql'
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print("\nExecuting SQL:")
    print("-" * 80)
    print(sql)
    print("-" * 80)
    
    try:
        # Execute the migration
        result = supabase.rpc('exec_sql', {'sql': sql}).execute()
        
        print("\n✅ Migration 021 applied successfully!")
        print("\nChanges:")
        print("  - Added last_reply_sent column to feedback_submissions")
        print("  - Created index on last_reply_sent for performance")
        print("  - Added column documentation")
        
    except Exception as e:
        print(f"\n❌ Error applying migration: {e}")
        print("\nYou may need to apply this migration manually via Supabase SQL Editor:")
        print(f"  1. Go to: https://supabase.com/dashboard/project/YOUR_PROJECT/sql")
        print(f"  2. Copy the SQL from: {migration_file}")
        print(f"  3. Execute it in the SQL editor")
        sys.exit(1)

if __name__ == '__main__':
    apply_migration()
