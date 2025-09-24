import re
import subprocess
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class RestartHandler(FileSystemEventHandler):
    def __init__(self, command, match_pattern=r".*\.py$"):
        self.command = command
        self.match_pattern = match_pattern
        self.process = None
        self.restart_server()

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only restart on Python file changes
        if re.match(self.match_pattern, str(event.src_path)):
            print(f"⚠️ File {event.src_path} changed.")
            self.restart_server()

    def restart_server(self):
        if self.process:
            print("🛑 Stopping server...")
            self.process.terminate()
            self.process.wait()

        print("✅ Starting server...")
        self.process = subprocess.Popen(self.command, shell=True)


def run_dev_server(server_command="uv run python -m app.main", watch_path=".", match_pattern=r".*\.py$"):
    # Command to start your gRPC server
    event_handler = RestartHandler(server_command, match_pattern)
    observer = Observer()
    observer.schedule(event_handler, path=watch_path, recursive=True)

    observer.start()
    print("Watching for file changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()

    observer.join()
