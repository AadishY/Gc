import threading
import time
import requests
import argparse
import sys
import json

class ChatClient:
    def __init__(self, username, vercel_url):
        self.username = username
        self.base_url = vercel_url.rstrip('/')
        self.chat_url = f"{self.base_url}/api/chat"
        self.ai_url = f"{self.base_url}/api/ai"
        self.running = True
        self.last_seen_timestamp = 0
        self.session = requests.Session() # Use a session for connection pooling

    def _post_command(self, payload):
        """Sends a command to the chat API."""
        try:
            payload['username'] = self.username
            response = self.session.post(self.chat_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            # On login, this is a fatal error
            if payload.get("command") == "LOGIN":
                print(f"Error: Could not connect to chat server at {self.chat_url}.")
                print(f"Details: {e}")
                self.running = False
            else:
                print(f"\n[CLIENT ERROR] Failed to send command: {e}\n> ", end="")
            return None

    def poll_messages(self):
        """Periodically polls the server for new messages."""
        while self.running:
            try:
                headers = {'X-Last-Seen-Timestamp': str(self.last_seen_timestamp)}
                response = self.session.get(self.chat_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    messages = response.json()
                    if messages:
                        for msg in messages:
                            print(f"\n{msg['text']}\n> ", end="")
                            self.last_seen_timestamp = max(self.last_seen_timestamp, msg['timestamp'])
                        sys.stdout.flush()
                elif response.status_code != 304: # 304 Not Modified is ok
                     print(f"\n[SERVER WARN] Polling failed with status: {response.status_code}\n> ", end="")

            except requests.exceptions.RequestException:
                # Ignore connection errors during polling, they might be temporary
                pass
            except json.JSONDecodeError:
                print(f"\n[CLIENT ERROR] Could not decode server response.\n> ", end="")
            
            time.sleep(2) # Poll every 2 seconds

    def heartbeat(self):
        """Sends a heartbeat to the server to stay online."""
        while self.running:
            self._post_command({"command": "HEARTBEAT"})
            time.sleep(15) # Heartbeat every 15 seconds

    def handle_ai_query(self, query):
        print("Sending query to AI, please wait...")
        try:
            response = self.session.post(self.ai_url, json={"query": query}, timeout=45)
            response.raise_for_status()
            print(f"\n{response.text}\n> ", end="")
        except requests.exceptions.RequestException as e:
            print(f"\n[AI ERROR] Could not connect to the AI service: {e}\n> ", end="")
        sys.stdout.flush()

    def start(self):
        # 1. Login
        welcome_message = self._post_command({"command": "LOGIN"})
        if not self.running: # Login failed
            return
        
        print(welcome_message)
        self.last_seen_timestamp = time.time() # Start polling for messages from now

        # 2. Start background threads
        threading.Thread(target=self.poll_messages, daemon=True).start()
        threading.Thread(target=self.heartbeat, daemon=True).start()

        # 3. Start main input loop
        self.input_loop()

    def input_loop(self):
        try:
            while self.running:
                msg = input("> ")
                if not self.running: break
                
                if msg.lower() in ["--active", "--a"]:
                    active_users_box = self._post_command({"command": "QUERY_ACTIVE"})
                    if active_users_box:
                        print(f"\n{active_users_box}\n> ", end="")
                        sys.stdout.flush()
                elif msg.lower().startswith("--ai "):
                    self.handle_ai_query(msg[len("--ai "):].strip())
                elif msg.lower() in ["--exit", "quit"]:
                    break
                else:
                    self._post_command({"command": "MSG", "text": msg})
        except (KeyboardInterrupt, EOFError):
            pass # Exit gracefully
        finally:
            self.stop()

    def stop(self):
        if self.running:
            self.running = False
            print("\nDisconnecting...")
            self._post_command({"command": "LOGOUT"})
            # Threads are daemons, so they will exit automatically

def main():
    parser = argparse.ArgumentParser(description="Vercel-Powered CLI Chat Client")
    parser.add_argument("username", help="Your single-word username.")
    parser.add_argument("vercel_url", help="The base URL of your Vercel deployment.")
    args = parser.parse_args()
    
    if " " in args.username or not args.username:
        print("Error: Username must be a single, non-empty word.")
        sys.exit(1)

    client = ChatClient(args.username, args.vercel_url)
    client.start()
    print("Goodbye!")

if __name__ == "__main__":
    main()
