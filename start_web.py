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

    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  .env file not found!")
        print("   Please copy .env.example to .env and add your API keys")
        print("   cp .env.example .env")
        return

    # Check if API keys are set
    from dotenv import load_dotenv
    load_dotenv()

    pexels_key = os.getenv('PEXELS_API_KEY')
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')

    if not pexels_key or not deepseek_key:
        print("⚠️  API keys not configured!")
        print("   Please edit .env file and add your API keys:")
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
