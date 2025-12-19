#!/usr/bin/env python3
"""
Simple web server for Catalog Generator with web interface.
"""

import http.server
import socketserver
import json
import threading
import time
import os
from urllib.parse import urlparse, parse_qs
from app.services.catalog_builder import CatalogBuilder
from app.services.archive_service import ArchiveService
import subprocess
import sys
import uuid

# Shared progress store for all clients
progress_store = {}

class CatalogWebHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.catalog_builder = None
        self.archive_service = ArchiveService()
        super().__init__(*args, **kwargs)

    def handle(self):
        """Override handle to catch connection errors"""
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            # Client disconnected, ignore
            pass
        except Exception as e:
            print(f"Error handling request: {e}")
            # Don't re-raise, just log and continue

    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            self.serve_file('web/index.html', 'text/html')
        elif parsed_path.path == '/api/health':
            self.send_json_response({'status': 'healthy'})
        elif parsed_path.path == '/api/progress':
            self.handle_progress_sse()
        elif parsed_path.path.startswith('/catalogs/'):
            # Serve generated catalog files
            filename = parsed_path.path[len('/catalogs/'):]
            filepath = os.path.join('catalogs', filename)
            if os.path.exists(filepath):
                self.serve_file(filepath, 'application/zip')
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        if self.path == '/api/generate-catalog':
            self.handle_generate_catalog()
        else:
            self.send_error(404, "Not found")

    def handle_generate_catalog(self):
        try:
            # Initialize services - try to load .env for local development, but Railway provides env vars directly
            if os.path.exists('.env'):
                import dotenv
                dotenv.load_dotenv(override=True)

            pexels_key = os.getenv('PEXELS_API_KEY')
            deepseek_key = os.getenv('DEEPSEEK_API_KEY')

            if not pexels_key or not deepseek_key:
                self.send_json_response({
                    'success': False,
                    'error': 'API keys not configured. Please set PEXELS_API_KEY and DEEPSEEK_API_KEY environment variables.'
                }, 500)
                return

            catalog_builder = CatalogBuilder(pexels_key, deepseek_key)

            # Start catalog generation in a separate thread
            output_dir = f'catalogs/catalog_{int(time.time())}'
            generation_thread = threading.Thread(
                target=self._generate_catalog_async,
                args=(catalog_builder, output_dir)
            )
            generation_thread.daemon = True
            generation_thread.start()

            # Return immediate response
            self.send_json_response({
                'success': True,
                'message': 'Catalog generation started',
                'output_dir': output_dir
            })

        except Exception as e:
            print(f"Error generating catalog: {e}")
            self.send_json_response({
                'success': False,
                'error': str(e)
            }, 500)

    def _build_catalog_with_progress(self, catalog_builder, output_dir):
        """Build catalog with detailed progress tracking for each batch"""
        # Initialize progress
        progress_store.clear()
        progress_store.update({
            'status': 'initializing',
            'message': 'Starting catalog generation...',
            'theme': '',
            'total_images': 0,
            'batches': [],
            'current_batch': 0,
            'total_batches': 0,
            'completed_batches': 0,
            'downloaded_images': 0
        })

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Select random theme
        theme = catalog_builder.theme_selector()
        progress_store['theme'] = theme
        progress_store['status'] = 'fetching_images'
        progress_store['message'] = f'Selected theme: {theme}'
        print(f"Selected theme: {theme}")

        # Step 2: Get images for theme
        images = catalog_builder.pexels_client.get_images_for_theme(theme)
        progress_store['total_images'] = len(images)
        progress_store['message'] = f'Fetched {len(images)} images for theme: {theme}'
        print(f"Fetched {len(images)} images")

        if not images:
            raise ValueError("No images found for the selected theme")

        # Step 3: Generate catalog entries using batch processing (20 images per batch)
        progress_store['status'] = 'processing_batches'
        progress_store['message'] = "Generating catalog data using batch API calls (20 images per batch)..."
        print("Generating catalog data using batch API calls (20 images per batch)...")

        catalog_entries = []
        batch_size = 20
        total_batches = (len(images) + batch_size - 1) // batch_size
        progress_store['total_batches'] = total_batches
        progress_store['batches'] = [{'number': i+1, 'status': 'pending', 'images': 0, 'time': 0} for i in range(total_batches)]

        for i in range(0, len(images), batch_size):
            batch_images = images[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            # Update batch status
            progress_store['current_batch'] = batch_num
            progress_store['batches'][batch_num-1]['status'] = 'processing'
            progress_store['batches'][batch_num-1]['images'] = len(batch_images)
            progress_store['message'] = f'Processing batch {batch_num}/{total_batches} ({len(batch_images)} images)'

            print(f"🎯 Starting batch {batch_num}/{total_batches} ({len(batch_images)} images)")

            # Time the batch processing
            batch_start_time = time.time()
            batch_entries = catalog_builder.deepseek_client.generate_batch_catalog_entries(batch_images, theme)
            batch_end_time = time.time()

            processing_time = batch_end_time - batch_start_time
            catalog_entries.extend(batch_entries)

            # Update batch status
            progress_store['batches'][batch_num-1]['status'] = 'completed'
            progress_store['batches'][batch_num-1]['time'] = round(processing_time, 1)
            progress_store['completed_batches'] = batch_num

            progress_store['message'] = f'Completed batch {batch_num}/{total_batches} in {processing_time:.1f}s'

            print(f"✅ Completed batch {batch_num}/{total_batches} in {processing_time:.1f}s - Generated {len(batch_entries)} products")

        # Step 4: Download images
        progress_store['status'] = 'downloading_images'
        progress_store['message'] = f"Downloading {len(images)} images..."
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        for i, image in enumerate(images, 1):
            try:
                # Download image
                image_url = image['src']['original']
                filename = f"{i}-1.jpg"
                catalog_builder.pexels_client.download_image(image_url, filename, images_dir)

                progress_store['downloaded_images'] = i
                progress_store['message'] = f"Downloaded {i}/{len(images)} images"

                if i % 10 == 0 or i == len(images):
                    print(f"Downloaded {i}/{len(images)} images")

            except Exception as e:
                print(f"Error downloading image {i}: {e}")
                continue

        # Step 5: Save CSV catalog
        progress_store['status'] = 'creating_archive'
        progress_store['message'] = "Creating catalog archive..."
        csv_path = os.path.join(output_dir, "catalog.csv")
        catalog_builder._save_csv_catalog(catalog_entries, csv_path)

        progress_store['status'] = 'completed'
        progress_store['message'] = f"Catalog built successfully. {len(catalog_entries)} products created."

        print(f"Catalog built successfully. {len(catalog_entries)} products created.")
        return output_dir

    def _generate_catalog_async(self, catalog_builder, output_dir):
        """Generate catalog asynchronously with progress updates"""
        try:
            # Run the catalog building process
            catalog_dir = self._build_catalog_with_progress(catalog_builder, output_dir)

            # Create archive
            archive_name = f'catalog_{int(time.time())}.zip'
            archive_path = self.archive_service.create_catalog_archive(catalog_dir, archive_name)

            # Update progress with completion info
            progress_store['archive_url'] = f'/catalogs/{archive_name}'
            progress_store['archive_name'] = archive_name

            print(f"✅ Catalog generation completed: {archive_path}")

        except Exception as e:
            # Update progress with error
            progress_store['status'] = 'error'
            progress_store['message'] = f'Error: {str(e)}'
            print(f"❌ Catalog generation failed: {e}")

    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(os.path.getsize(filepath)))
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404, "File not found")

    def handle_progress_sse(self):
        """Handle Server-Sent Events for progress updates"""
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Keep connection alive and send progress updates
            while True:
                if progress_store:
                    # Send current progress
                    data = json.dumps(progress_store)
                    self.wfile.write(f"data: {data}\n\n".encode('utf-8'))
                    self.wfile.flush()

                time.sleep(1)  # Update every second

        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            # Client disconnected from SSE stream, this is normal
            pass
        except Exception as e:
            print(f"SSE connection error: {e}")
            # Don't re-raise, just log and exit gracefully

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        # Suppress default logging
        pass

def run_server(port=8000):
    """Run the web server"""
    # Create catalogs directory if it doesn't exist
    os.makedirs('catalogs', exist_ok=True)

    # Change to the project root directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    handler = CatalogWebHandler
    httpd = socketserver.TCPServer(("", port), handler)

    print(f"🚀 Catalog Generator Web Server running at http://localhost:{port}")
    print("📁 Web interface: http://localhost:8000")
    print("🔄 Press Ctrl+C to stop")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        httpd.shutdown()

if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()

    port = int(os.getenv('PORT', 8000))
    run_server(port)
