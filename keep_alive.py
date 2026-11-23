import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - TelegramFileAccessBot is running 24/7 on Render")

    def log_message(self, format, *args):
        # Silence routine HTTP access logs
        pass

def start_health_server():
    """Start a lightweight HTTP server on the PORT assigned by Render/Cloud host."""
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"Health check web server running on port {port} (Render ready)")
    except Exception as e:
        print(f"Health check server notice: {e}")

if __name__ == "__main__":
    start_health_server()
