from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "NUCLEAR_DEPLOY_SUCCESS",
            "message": "The Vercel build pipeline is unclogged."
        }).encode())
        return

    def do_POST(self):
        self.do_GET()
