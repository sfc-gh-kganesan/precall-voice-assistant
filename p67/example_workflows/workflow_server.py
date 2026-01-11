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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests."""
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        """Handle POST requests for file saving."""
        import json
        import shutil

        # Decode the URL path
        path = unquote(self.path)

        # Special endpoint to save files
        if path == '/api/save':
            try:
                # Read the request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                file_path = data.get('filePath', '')
                content = data.get('content', '')

                # Security: prevent directory traversal
                if '..' in file_path or file_path.startswith('/'):
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid file path'}).encode())
                    return

                # Write the file
                full_path = os.path.join(os.getcwd(), file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"[Server] Saved file: {file_path}")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'message': 'File saved successfully'}).encode())

            except Exception as e:
                print(f"[Server] Error saving file: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
                return

        # Special endpoint to create a new project
        elif path == '/api/create-project':
            try:
                # Read the request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                project_name = data.get('projectName', '')

                # Security: validate project name
                if not project_name or '..' in project_name or '/' in project_name or '\\' in project_name:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid project name'}).encode())
                    return

                # Get current working directory (should be the example_workflows directory)
                workdir = os.getcwd()
                template_dir = os.path.join(workdir, 'template')
                new_project_dir = os.path.join(workdir, project_name)

                # Check if project already exists
                if os.path.exists(new_project_dir):
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Project already exists'}).encode())
                    return

                # Check if template directory exists
                if not os.path.exists(template_dir):
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Template directory not found'}).encode())
                    return

                # Create the new project directory
                os.makedirs(new_project_dir, exist_ok=True)

                # Copy .cortex/commands directory
                template_commands_dir = os.path.join(template_dir, '.cortex', 'commands')
                new_commands_dir = os.path.join(new_project_dir, '.cortex', 'commands')
                if os.path.exists(template_commands_dir):
                    shutil.copytree(template_commands_dir, new_commands_dir)
                    print(f"[Server] Copied .cortex/commands to {new_commands_dir}")

                # Copy conf directory
                template_conf_dir = os.path.join(template_dir, 'conf')
                new_conf_dir = os.path.join(new_project_dir, 'conf')
                if os.path.exists(template_conf_dir):
                    shutil.copytree(template_conf_dir, new_conf_dir)
                    print(f"[Server] Copied conf to {new_conf_dir}")

                print(f"[Server] Created new project: {project_name}")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': f'Project "{project_name}" created successfully',
                    'projectPath': project_name
                }).encode())

            except Exception as e:
                print(f"[Server] Error creating project: {e}")
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
                return

        else:
            self.send_response(404)
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

        # Special endpoint to list subdirectories
        if path == '/api/folders':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            import json
            try:
                workdir = os.getcwd()
                folders = []
                for entry in os.listdir(workdir):
                    full_path = os.path.join(workdir, entry)
                    if os.path.isdir(full_path) and not entry.startswith('.'):
                        folders.append({
                            'name': entry,
                            'path': entry
                        })
                folders.sort(key=lambda x: x['name'].lower())
                self.wfile.write(json.dumps({'folders': folders, 'currentDir': workdir}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e), 'folders': []}).encode())
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
