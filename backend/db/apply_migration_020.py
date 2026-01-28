#!/usr/bin/env python3
"""
Apply Migration 020: Notifications System
Creates the notifications table for in-app notifications
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.supabase_client import get_supabase_admin

def apply_migration():
    """Apply the notifications system migration."""
    try:
        print("=" * 70)
        print("🔄 Applying Migration 020: Notifications System")
        print("=" * 70)
        
        # Read migration file
        migration_file = Path(__file__).parent / 'migrations' / '020_notifications_system.sql'
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        print("\n📄 Migration SQL loaded")
        print(f"   File: {migration_file}")
        
        # Get Supabase admin client
        print("\n🔌 Connecting to Supabase...")
        supabase = get_supabase_admin()
        
        # Execute migration
        print("\n⚙️  Executing migration...")
        result = supabase.rpc('exec_sql', {'sql': sql}).execute()
        
        print("\n✅ Migration applied successfully!")
        print("\n📊 Created:")
        print("   - notifications table")
        print("   - Indexes for user_id, read, created_at")
        print("   - RLS policies")
        
        print("\n" + "=" * 70)
        print("✅ MIGRATION 020 COMPLETE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error applying migration: {e}")
        print("\n💡 Manual application required:")
        print("   1. Go to Supabase Dashboard > SQL Editor")
        print("   2. Copy contents of backend/db/migrations/020_notifications_system.sql")
        print("   3. Execute the SQL")
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
