from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pdca_service import pdca_service
from services.learning_service import learning_service

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/pdca/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            logs = pdca_service.get_pending_actions()
            self.wfile.write(json.dumps(logs).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/pdca/approve':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            term = data.get('term')
            unit = data.get('unit')
            target = data.get('target') # Correct exam name
            
            if not term or not target:
                self.send_response(400)
                self.end_headers()
                return

            # 1. Execute the action (Learn)
            learning_service.learn(term, target)
            
            # 2. Update PDCA Status
            pdca_service.approve_action(term, unit)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": f"Aprendido: {term} -> {target}"}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
