#!/usr/bin/env python3
"""
Quick start script for the Catalog Generator web interface.
"""

import os
import sys
import subprocess

def main():
    """Start the web server"""
    print("🚀 Starting Catalog Generator Web Interface")
    print("=" * 50)

    # Try to load .env file if it exists (for local development)
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded .env file")

    # Check if API keys are set (either from .env or Railway environment)
    pexels_key = os.getenv('PEXELS_API_KEY')
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')

    if not pexels_key or not deepseek_key:
        print("⚠️  API keys not configured!")
        if os.path.exists('.env.example'):
            print("   For local development:")
            print("   cp .env.example .env")
            print("   Then edit .env and add your API keys")
        print("   For Railway deployment:")
        print("   Set PEXELS_API_KEY and DEEPSEEK_API_KEY in Railway Variables")
        print("   - PEXELS_API_KEY")
        print("   - DEEPSEEK_API_KEY")
        return

    print("✅ API keys configured")
    print("🌐 Starting web server...")

    # Start the web server
    try:
        subprocess.run([sys.executable, 'web_server.py'], check=True)
    except KeyboardInterrupt:
        print("\n👋 Web server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting web server: {e}")

if __name__ == '__main__':
    main()
