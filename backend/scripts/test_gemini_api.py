#!/usr/bin/env python3
"""
Test Gemini API connection and list available models.
"""

import os
import sys

try:
    import google.generativeai as genai
    
    # Get API key
    api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY")
        sys.exit(1)
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    # Configure API
    genai.configure(api_key=api_key)
    
    print("\n📋 Listing available models...")
    
    # List models
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"   ✓ {model.name}")
    
    print("\n✅ API connection successful!")
    
except ImportError:
    print("❌ google-generativeai not installed")
    print("   Run: pip install google-generativeai")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
