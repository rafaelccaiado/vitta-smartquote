from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "V21_DEPENDENCY_PROBE_SUCCESS",
            "message": "Dependencies installed successfully. Logic disconnected."
        }).encode())
        return

    def do_POST(self):
        self.do_GET()
