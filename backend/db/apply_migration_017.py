#!/usr/bin/env python3
"""
Apply migration 017: Fix payment_reference unique constraint
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.supabase_client import get_supabase_admin

def apply_migration():
    """Apply the migration to fix payment_reference constraint"""
    try:
        supabase = get_supabase_admin()
        
        print("Applying migration 017: Fix payment_reference constraint...")
        
        # Drop the problematic constraint
        print("1. Dropping unique_payment_reference constraint...")
        supabase.rpc('exec_sql', {
            'sql': 'ALTER TABLE script_credit_purchases DROP CONSTRAINT IF EXISTS unique_payment_reference;'
        }).execute()
        
        # Create partial unique index (only for non-NULL values)
        print("2. Creating partial unique index for non-NULL payment references...")
        supabase.rpc('exec_sql', {
            'sql': '''
                CREATE UNIQUE INDEX IF NOT EXISTS unique_payment_reference_not_null 
                ON script_credit_purchases(payment_reference) 
                WHERE payment_reference IS NOT NULL;
            '''
        }).execute()
        
        print("✓ Migration 017 applied successfully!")
        print("  - Removed constraint that prevented multiple NULL payment_references")
        print("  - Added partial index to enforce uniqueness only for non-NULL values")
        
    except Exception as e:
        print(f"✗ Error applying migration: {e}")
        sys.exit(1)

if __name__ == '__main__':
    apply_migration()
