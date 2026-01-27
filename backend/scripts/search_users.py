#!/usr/bin/env python3
"""
Search for users in the database
"""

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from db.supabase_client import get_supabase_admin


def search_users(search_term: str):
    """Search for users by email or name."""
    try:
        supabase = get_supabase_admin()
        
        # Search by email (case-insensitive partial match)
        response = supabase.table('profiles').select('*').ilike('email', f'%{search_term}%').execute()
        
        if response.data:
            print(f"\n✅ Found {len(response.data)} user(s) matching '{search_term}':\n")
            for user in response.data:
                print(f"  📧 {user.get('email')}")
                print(f"     Name: {user.get('full_name', 'N/A')}")
                print(f"     ID: {user.get('id')}")
                print()
        else:
            # Try searching by name
            response = supabase.table('profiles').select('*').ilike('full_name', f'%{search_term}%').execute()
            
            if response.data:
                print(f"\n✅ Found {len(response.data)} user(s) with name matching '{search_term}':\n")
                for user in response.data:
                    print(f"  📧 {user.get('email')}")
                    print(f"     Name: {user.get('full_name', 'N/A')}")
                    print(f"     ID: {user.get('id')}")
                    print()
            else:
                print(f"\n❌ No users found matching '{search_term}'")
        
    except Exception as e:
        print(f"Error searching users: {e}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python search_users.py <search_term>")
        sys.exit(1)
    
    search_term = sys.argv[1].strip()
    search_users(search_term)
