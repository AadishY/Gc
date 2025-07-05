import os
import json
import time
from http.server import BaseHTTPRequestHandler
from vercel_kv.redis import VercelKV

# Connect to Vercel KV (reads connection details from environment variables)
try:
    kv = VercelKV.from_env()
except Exception as e:
    # This allows local testing without a live KV connection if needed,
    # though functionality will be degraded.
    print(f"Warning: Could not connect to Vercel KV. {e}")
    kv = None

# Constants
USER_TIMEOUT_SECONDS = 30  # Time in seconds before a user is considered stale
MAX_MESSAGES = 50 # Max messages to keep in history

def create_boxed_message(lines, title=""):
    """Creates an ASCII-framed message box."""
    if isinstance(lines, str): lines = [lines]
    if not lines: return ""
    max_len = max(len(line) for line in lines)
    if title: max_len = max(max_len, len(title) + 4)
    box = [f"┌{'─' * (max_len + 2)}┐"]
    if title:
        box.append(f"│ {title.center(max_len)} │")
        box.append(f"├{'─' * (max_len + 2)}┤")
    for line in lines:
        box.append(f"│ {line.ljust(max_len)} │")
    box.append(f"└{'─' * (max_len + 2)}┘")
    return "\n".join(box)

def add_message(pipe, text):
    """Adds a message to the global chat history."""
    msg_data = json.dumps({"text": text, "timestamp": time.time()})
    pipe.lpush("messages", msg_data)
    pipe.ltrim("messages", 0, MAX_MESSAGES - 1)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handles commands like LOGIN, MSG, LOGOUT, ACTIVE."""
        if not kv:
            self.send_response(503); self.end_headers(); self.wfile.write(b"KV store not available"); return

        try:
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length))
            command = body.get("command")
            username = body.get("username")
            
            if not all([command, username]):
                self.send_response(400); self.end_headers(); self.wfile.write(b"Missing command or username"); return
            
            pipe = kv.pipeline()
            
            if command == "LOGIN":
                if kv.hexists("clients", username):
                    self.send_response(409); self.end_headers(); self.wfile.write(b"Username already taken"); return
                
                pipe.hset("clients", username, time.time())
                add_message(pipe, f"*** {username} has joined the chat ***")
                response_data = create_boxed_message(f"Welcome, {username}!")
            
            elif command == "HEARTBEAT":
                if kv.hexists("clients", username):
                    pipe.hset("clients", username, time.time())
                response_data = '{"status": "ok"}'

            elif command == "MSG":
                text = body.get("text", "")
                add_message(pipe, f"[{username}]: {text}")
                response_data = '{"status": "sent"}'

            elif command == "QUERY_ACTIVE":
                clients_raw = kv.hgetall("clients")
                active_users = []
                now = time.time()
                for u, last_seen in clients_raw.items():
                    if now - float(last_seen) < USER_TIMEOUT_SECONDS:
                        active_users.append(u.decode('utf-8'))
                response_data = create_boxed_message(sorted(active_users), title="Active Users")

            elif command == "LOGOUT":
                pipe.hdel("clients", username)
                add_message(pipe, f"*** {username} has left the chat ***")
                response_data = '{"status": "logged out"}'
            
            else:
                self.send_response(400); self.end_headers(); self.wfile.write(b"Unknown command"); return

            pipe.execute()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(response_data.encode('utf-8'))

        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(f"Server Error: {e}".encode())

    def do_GET(self):
        """Handles polling for new messages."""
        if not kv:
            self.send_response(503); self.end_headers(); self.wfile.write(b"KV store not available"); return
        
        # Get the timestamp of the last message the client has seen
        last_seen_ts = float(self.headers.get('X-Last-Seen-Timestamp', 0))
        
        try:
            messages_raw = kv.lrange("messages", 0, MAX_MESSAGES - 1)
            new_messages = []
            for msg_raw in reversed(messages_raw): # Iterate from oldest to newest
                msg = json.loads(msg_raw)
                if msg["timestamp"] > last_seen_ts:
                    new_messages.append(msg)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(new_messages).encode('utf-8'))

        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(f"Server Error: {e}".encode())
