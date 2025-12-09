"""
Database migration runner for ScripDown AI
"""

import sqlite3
import os

# Database path
DB_PATH = 'db/script_breakdown.db'

def run_migration(migration_file, skip_errors=False):
    """
    Run a SQL migration file.
    
    Args:
        migration_file: Path to the migration SQL file
        skip_errors: If True, continue on errors (useful for idempotent migrations)
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False
    
    if not os.path.exists(migration_file):
        print(f"Error: Migration file not found at {migration_file}")
        return False
    
    try:
        # Read migration SQL
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Execute migration (split by semicolons for multiple statements)
        statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
        
        success_count = 0
        skip_count = 0
        
        for statement in statements:
            if statement and not statement.startswith('--'):
                try:
                    print(f"Executing: {statement[:60]}...")
                    cursor.execute(statement)
                    success_count += 1
                except sqlite3.OperationalError as e:
                    if skip_errors:
                        print(f"  ⚠ Skipped (already exists or error): {e}")
                        skip_count += 1
                    else:
                        raise
        
        conn.commit()
        conn.close()
        
        print(f"\n✓ Migration completed: {migration_file}")
        print(f"  - Executed: {success_count} statements")
        print(f"  - Skipped: {skip_count} statements")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


def run_all_migrations():
    """Run all pending migrations in order."""
    migrations_dir = 'db/migrations'
    
    if not os.path.exists(migrations_dir):
        print(f"Error: Migrations directory not found at {migrations_dir}")
        return False
    
    # Get all SQL files sorted by name
    migration_files = sorted([
        f for f in os.listdir(migrations_dir) 
        if f.endswith('.sql')
    ])
    
    print(f"Found {len(migration_files)} migration files")
    
    for migration_file in migration_files:
        full_path = os.path.join(migrations_dir, migration_file)
        print(f"\n{'='*50}")
        print(f"Running: {migration_file}")
        print('='*50)
        run_migration(full_path, skip_errors=True)
    
    print(f"\n{'='*50}")
    print("All migrations complete!")
    print('='*50)


if __name__ == '__main__':
    # Run the metadata migration
    migration_path = 'db/migrations/001_add_script_metadata.sql'
    run_migration(migration_path)
