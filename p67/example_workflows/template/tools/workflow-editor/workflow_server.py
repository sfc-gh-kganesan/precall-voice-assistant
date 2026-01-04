#!/usr/bin/env python3
"""
Simple HTTP server for the workflow browser.
This server allows the browser to access local files while respecting CORS policies.
"""

import http.server
import socketserver
import os
import sys
from urllib.parse import unquote

PORT = 8000

class WorkflowServerHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that adds CORS headers and serves files from the workflow directory."""

    def end_headers(self):
        """Add CORS headers to allow cross-origin requests."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests."""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        # Decode the URL path
        path = unquote(self.path)

        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]

        # Special endpoint to return the server's working directory
        if path == '/api/workdir':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            import json
            workdir = os.getcwd()
            self.wfile.write(json.dumps({'workdir': workdir}).encode())
            return

        # Log the request
        print(f"Serving: {path}")

        # Call the parent handler
        super().do_GET()

    def log_message(self, format, *args):
        """Custom log message format."""
        print(f"[Server] {format % args}")


def main():
    """Start the HTTP server."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print(f"Starting workflow browser server...")
    print(f"Serving files from: {script_dir}")
    print(f"Server running at: http://localhost:{PORT}")
    print(f"\nOpen the workflow browser at:")
    print(f"  http://localhost:{PORT}/workflow_browser.html")
    print(f"\nPress Ctrl+C to stop the server\n")

    try:
        with socketserver.TCPServer(("", PORT), WorkflowServerHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"\nError: Port {PORT} is already in use.")
            print(f"Please stop the other server or use a different port.")
            sys.exit(1)
        else:
            raise


if __name__ == "__main__":
    main()
